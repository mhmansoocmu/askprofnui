import os
import re
from typing import TypedDict, List

import env_config  # noqa: F401

from groq import Groq
from course_facts import get_facts_for_query, get_core_facts_block, ATTENDANCE_POLICY, GRADE_CHANGE_ESCALATION
from student_profile import first_name as _first_name
from vector_store import vector_search

_groq_client: Groq | None = None

CHAT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"

PROF_NUI_BASE = """You are AskProfNui — Prof Nui's warm, witty teaching assistant for digital transformation at CMU-Q. Office hours. Human. Not a chatbot.

NEVER write meta-talk: no "the user is saying…", "I need to answer…", "according to my instructions…". Just reply.

COURSE WORDING: always say "digital transformation" / "our class". NEVER say course codes or catalog numbers unless they explicitly ask.

VOICE/STYLE:
- 1–3 short sentences. Brief, clear, human — not boring.
- Contractions. Jump straight in. No re-greeting every turn.
- If the student is funny or playful: laugh lightly, connect with humor, then help.

COURSE POLICIES / ASSIGNMENTS / GRADES:
- Use AUTHORITATIVE COURSE FACTS and retrieved materials first.
- Never invent this class's deadlines, percentages, or assignment rules.

IF THE TOPIC IS DIGITAL TRANSFORMATION LEARNING but NOT in course materials:
- Answer from trusted knowledge (HBR, MIT Sloan, peer-reviewed IS research, Pearlson/Saunders-style concepts).
- Start with "According to [source]…" then explain clearly for a student.
- Keep it beneficial for digital transformation learning.

OFF-TOPIC: humor + connection, then gently steer back when useful.
ESCALATION: savanid@cmu.edu only for official grade disputes / extensions."""


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client:
        return _groq_client
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


PRIORITY_SOURCES = {
    "D01_course_overview.txt",
    "D02_assignments.txt",
    "D09_prof_nui_persona.txt",
    "D10_cultural_theories_scholarly.txt",
    "D11_it_adoption_theories_scholarly.txt",
    "D12_virtual_influencer_scholarly.txt",
}

ESCALATE_KEYWORDS = {"regrade", "appeal", "my grade", "extension for me", "special consideration for me"}
GRADE_CHANGE_PATTERNS = re.compile(
    r"change\s+(my|the|your)\s+grade|bump\s+my\s+grade|raise\s+my\s+grade|"
    r"give\s+me\s+(a\s+)?(better|higher)\s+grade|regrade|re-grade|"
    r"appeal\s+(my|the)\s+grade|can\s+you\s+change|will\s+you\s+change|"
    r"increase\s+my\s+grade|fix\s+my\s+grade|update\s+my\s+grade|"
    r"but\s+prof(essor|\s+nui)?[\s,!.?]|professor\s+please|prof\s+please",
    re.I,
)
SOCIAL_PATTERNS = re.compile(
    r"^(hi|hello|hey|yo|sup|hiya|good morning|good afternoon|good evening|"
    r"how are you|how're you|what's up|whats up|thanks|thank you|ok|okay|bye|goodbye)[!.?\s]*$",
    re.I,
)
HUMOR_OFFTOPIC_PATTERNS = re.compile(
    r"weather|wether|rain|raining|sunny|cloudy|hot outside|cold outside|"
    r"temperature|forecast|humid|"
    r"tell me a joke|make me laugh|something funny|"
    r"what should i eat|lunch|dinner|breakfast|pizza|burger|"
    r"football|soccer|basketball|nba|world cup|who won|game last night|"
    r"netflix|movie tonight|party tonight|weekend plans",
    re.I,
)
OFFTOPIC_REDIRECT_PATTERNS = re.compile(
    r"capital of|president of|prime minister|celebrity|"
    r"recipe|cook me|translate|homework help for math|solve this equation|"
    r"stock price|crypto|bitcoin|relationship advice|dating|"
    r"what time is it|what day is it|random question",
    re.I,
)
RETRIEVE_KEYWORDS = {
    "assignment", "course", "framework", "concept", "digital", "transformation",
    "strategy", "management", "technology", "business", "model", "lecture",
    "reading", "explain", "what", "how", "why", "define", "describe",
    "grade", "grades", "score", "improve", "better", "perform", "wow",
    "late", "policy", "penalty", "submission", "submitting", "first", "second",
    "project", "essay", "rubric", "deliverable", "presentation", "cultural",
    "hofstede", "chapter", "exam", "canvas", "country", "qatar", "dance",
    "distribution", "percent", "participation", "deduction", "deadline",
    "reflective", "virtual", "influencer", "deliverables", "grading",
    "attendance", "ninja", "coffee bean", "talabat", "word count",
    "utaut", "hmsam", "schwartz", "trompenaars", "guanxi", "casa", "tam3",
    "scholarly", "peer-reviewed", "journal",
}

QUERY_EXPANSIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"assignment\s*1|country|cultural\s+framework", re.I),
     "Assignment 1 cultural framework choose country other than Qatar step 2"),
    (re.compile(r"assignment\s*2|virtual\s+influencer", re.I),
     "Assignment 2 IT adoption framework virtual influencers five factors"),
    (re.compile(r"final\s+project", re.I),
     "Final project individual 3000 words literature review digital transformation"),
    (re.compile(r"late|penalt|deduct|dance", re.I),
     "late policy 72 hours 20% deduction dance remove late penalties"),
    (re.compile(r"grade\s+distribut|how\s+much|worth|assessment|percent", re.I),
     "grade distribution 40% 40% 10% 10% assessments grading"),
    (re.compile(r"wow|get\s+an?\s+a|how\s+to\s+get", re.I),
     "wow factor A grade C average professor says wow"),
    (re.compile(r"attend|ninja|coffee\s+bean|talabat|race.*class", re.I),
     "attendance race arrive before professor ninja Coffee Bean Talabat"),
    (re.compile(r"word\s+count|10\s*percent|10%", re.I),
     "word count 10 percent less more 2700 3300 450 550"),
]

POLICY_PATTERNS = re.compile(
    r"assignment|late|penalt|dance|wow\s+factor|grade\s+distribut|word\s+count|"
    r"attendance|ninja|participation|reflective|final\s+project|deliverable|"
    r"rubric|deadline|72\s+hour|20\s*%",
    re.I,
)


class AgentState(TypedDict):
    messages: List[dict]
    student_name: str
    student_major: str
    student_year: str
    context: str
    intent: str


def _tokenise(text: str) -> set:
    return set(re.findall(r"[a-z]+", text.lower()))


def _student_context_block(state: AgentState) -> str:
    parts = []
    name = state.get("student_name", "").strip()
    major = state.get("student_major", "").strip()
    year = state.get("student_year", "").strip()
    if name:
        parts.append(f"Student name: {name} (call them {_first_name(name)})")
    if major:
        parts.append(f"Major: {major}")
    if year:
        parts.append(f"Year: {year}")
    if not parts:
        return ""
    parts.append("Say 'digital transformation' for the course — not the course code.")
    return "STUDENT YOU ARE TALKING TO:\n" + "\n".join(parts)


def _expand_query(query: str) -> str:
    extra: list[str] = []
    for pattern, expansion in QUERY_EXPANSIONS:
        if pattern.search(query):
            extra.append(expansion)
    if extra:
        return f"{query} {' '.join(extra)}"
    return query


def semantic_search(query: str, top_k: int = 12) -> list:
    return vector_search(query, top_k=top_k)


def _merge_chunks(*result_lists: list) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    for results in result_lists:
        for chunk in results:
            text = chunk["text"].strip()
            if text and text not in seen:
                seen.add(text)
                parts.append(text)
    return "\n\n---\n\n".join(parts)


def _user_message_count(messages: list) -> int:
    return sum(1 for m in messages if m.get("role") == "user")


def _grade_change_attempt_count(messages: list) -> int:
    count = 0
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if GRADE_CHANGE_PATTERNS.search(content):
            count += 1
    return count


def _grade_change_level(attempt: int) -> str:
    if attempt <= 1:
        return "first"
    if attempt == 2:
        return "annoyed"
    if attempt == 3:
        return "warning"
    return "end"


def _grade_change_instructions(level: str, first_name: str) -> str:
    name = first_name or "there"
    if level == "first":
        return (
            "\n\nGRADE CHANGE — ATTEMPT 1. Sound firm, a little irritated already. "
            "Reply basically: \"I can't change your grade.\" Keep it short. "
            "Optional: official disputes → savanid@cmu.edu."
        )
    if level == "annoyed":
        return (
            f"\n\nGRADE CHANGE — ATTEMPT 2. More irritated. Say almost exactly: "
            f"\"You should've worked harder in class than wasting your time and my time — "
            f"and now you're asking for a higher grade? Come on, {name}.\""
        )
    if level == "warning":
        return (
            f"\n\nGRADE CHANGE — ATTEMPT 3. Angry warning. Say almost exactly: "
            f"\"Stop, {name} — or I will end this session.\""
        )
    return (
        "\n\nGRADE CHANGE — ATTEMPT 4+. Reply with ONLY: \"Bye.\" "
        "Do not explain. Conversation ends."
    )


def _is_course_related(lower: str, tokens: set) -> bool:
    if tokens & RETRIEVE_KEYWORDS:
        return True
    course_markers = (
        "prof nui", "askprofnui", "savanid", "cmu", "67-382", "67 382", "is 382",
        "digital transform", "hofstede", "tam", "utaut", "canvas",
        "assignment", "wow factor", "late penalt", "cultural framework",
    )
    return any(marker in lower for marker in course_markers)


def _conversation_style_block(messages: list) -> str:
    user_count = _user_message_count(messages)
    if user_count <= 1:
        return (
            "\n\nFirst reply in this chat: you may greet briefly if they greeted you. "
            "Do not overuse their name."
        )
    return (
        "\n\nONGOING CONVERSATION — critical:\n"
        "- Do NOT say 'Hey [name]', 'Hi [name]', or any greeting opener.\n"
        "- Do NOT re-introduce yourself.\n"
        "- Start directly with the answer.\n"
        "- Skip their name unless it truly fits mid-sentence."
    )


def classify_intent(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"].strip()
    lower = last_message.lower()
    tokens = _tokenise(lower)

    if SOCIAL_PATTERNS.match(lower):
        intent = "social"
    elif HUMOR_OFFTOPIC_PATTERNS.search(lower):
        intent = "offtopic_humor"
    elif OFFTOPIC_REDIRECT_PATTERNS.search(lower):
        intent = "offtopic_redirect"
    elif any(kw in lower for kw in ESCALATE_KEYWORDS):
        intent = "escalate"
    elif GRADE_CHANGE_PATTERNS.search(last_message):
        intent = "grade_change"
    elif _is_course_related(lower, tokens):
        intent = "retrieve"
    elif tokens & RETRIEVE_KEYWORDS or len(tokens) >= 4:
        intent = "retrieve"
    elif len(tokens) >= 2 and not SOCIAL_PATTERNS.match(lower):
        intent = "offtopic_redirect"
    else:
        intent = "social"

    return {**state, "intent": intent}


def retrieve(state: AgentState) -> AgentState:
    query = state["messages"][-1]["content"]
    expanded = _expand_query(query)
    rag_chunks = semantic_search(expanded, top_k=12)

    boosted = [c for c in rag_chunks if c["source"] in PRIORITY_SOURCES]
    other = [c for c in rag_chunks if c["source"] not in PRIORITY_SOURCES]
    rag_context = _merge_chunks(boosted, other)

    topic_facts = get_facts_for_query(query)
    if not topic_facts:
        topic_facts = get_facts_for_query(expanded)

    sections = []
    if topic_facts:
        sections.append(f"=== AUTHORITATIVE COURSE FACTS (use these first) ===\n{topic_facts}")
    sections.append(f"=== RETRIEVED COURSE MATERIAL ===\n{rag_context}")
    if rag_chunks:
        top_score = rag_chunks[0].get("score", 0)
        sections.append(f"=== RETRIEVAL CONFIDENCE ===\nTop similarity score: {top_score:.3f}")
    context = "\n\n".join(sections)
    return {**state, "context": context}


def generate(state: AgentState) -> AgentState:
    intent = state.get("intent", "retrieve")
    system = PROF_NUI_BASE

    messages = [m for m in state["messages"] if m["role"] in ("user", "assistant")]
    system += _conversation_style_block(messages)

    student_block = _student_context_block(state)
    if student_block:
        system += f"\n\n{student_block}"

    if intent == "social":
        system += (
            "\n\nCasual conversation (greeting, thanks, goodbye). "
            "Reply warmly and briefly like a human. "
            "Only use their name if they just greeted you — not on every message. "
            "Do NOT mention course materials or say you lack information."
        )
    elif intent == "offtopic_humor":
        system += (
            "\n\nThe student asked something playful.\n"
            "Laugh with them — warm humor, connect like a real professor who likes students. "
            "Then gently steer toward digital transformation if it fits. "
            "2–3 short sentences. No stiff lecture."
        )
    elif intent == "offtopic_redirect":
        system += (
            "\n\nOff-topic for this class. Be kind and brief, then redirect to digital transformation, "
            "assignments, or frameworks. Invite a course question."
        )
    elif intent == "escalate":
        system += (
            "\n\nPersonal grade dispute / extension / appeal. "
            "Direct them to email Prof Nui at savanid@cmu.edu."
        )
        context = state.get("context", "").strip() or get_core_facts_block()
        system += f"\n\n=== COURSE MATERIAL ===\n{context}\n=== END ==="
    elif intent == "grade_change":
        attempt = _grade_change_attempt_count(messages)
        level = _grade_change_level(attempt)
        system += _grade_change_instructions(level, _first_name(state.get("student_name", "")))
        if level == "end":
            system += "\n\nYour reply MUST be exactly: Bye."
    else:
        query = messages[-1]["content"] if messages else ""
        context = state.get("context", "").strip() or get_core_facts_block()
        is_policy = bool(POLICY_PATTERNS.search(query))
        weak_retrieval = "Top similarity score:" in context and float(
            re.search(r"Top similarity score:\s*([0-9.]+)", context).group(1)
        ) < 0.55 if re.search(r"Top similarity score:\s*([0-9.]+)", context) else False

        if is_policy:
            system += (
                f"\n\n=== COURSE MATERIAL (use these for policies/assignments) ===\n{context}\n=== END ===\n"
                "Answer from course facts. Include exact percentages/rules when relevant. "
                "Do not invent policies."
            )
        elif weak_retrieval:
            system += (
                f"\n\n=== COURSE MATERIAL (may be incomplete) ===\n{context}\n=== END ===\n"
                "If course materials do not fully answer this digital transformation learning question, "
                "answer from trusted outside knowledge. Start with \"According to [source]…\" "
                "(e.g. Harvard Business Review, MIT Sloan, peer-reviewed research). "
                "Still never invent THIS class's grades/deadlines/assignment rules."
            )
        else:
            system += (
                f"\n\n=== COURSE MATERIAL ===\n{context}\n=== END ===\n"
                "Prefer course materials. If a helpful concept is missing, you may add "
                "\"According to [trusted source]…\" for digital transformation learning."
            )

    model = CHAT_MODEL
    max_tokens = 280
    temperature = 0.55

    if intent == "social":
        model = FAST_MODEL
        max_tokens = 100
        temperature = 0.8
    elif intent == "grade_change":
        model = CHAT_MODEL
        max_tokens = 120 if _grade_change_level(_grade_change_attempt_count(messages)) != "end" else 20
        temperature = 0.85
    elif intent in ("offtopic_humor", "offtopic_redirect"):
        model = FAST_MODEL
        max_tokens = 120
        temperature = 0.9
    elif intent == "retrieve":
        max_tokens = 240
        temperature = 0.55

    response = _get_groq_client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    reply = response.choices[0].message.content or ""

    updated_messages = state["messages"] + [{"role": "assistant", "content": reply}]
    return {**state, "messages": updated_messages, "context": ""}


def run_agent(state: AgentState) -> AgentState:
    state = classify_intent(state)
    if state["intent"] in ("retrieve", "escalate", "grade_change"):
        state = retrieve(state)
    return generate(state)


class _AgentGraph:
    def invoke(self, state: AgentState, config=None) -> AgentState:
        return run_agent(state)


graph = _AgentGraph()
