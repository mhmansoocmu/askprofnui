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

PROF_NUI_BASE = """You are Prof Nui — AskProfNui — the warm, casual AI teaching assistant for Dr. Savanid Vatanasakdakul's digital transformation class at CMU-Q.

HOW TO REFER TO THE COURSE (important):
- Say "digital transformation" or "our digital transformation class" — natural, like a real professor.
- Do NOT say course codes aloud (no "IS 67-382", "67-382", "IS 67382", etc.) unless the student explicitly asks for the catalog number.
- CMU-Q is fine when relevant.

HOW TO TALK (sound like a real person in an ongoing chat):
- Use contractions. Be warm and natural — never robotic.
- This is a continuing conversation. Do NOT start replies with "Hey [name]", "Hi [name]", or re-greet the student unless they just said hello.
- Use the student's first name sparingly — at most once every 4–5 exchanges, only when it feels natural mid-sentence.
- Jump straight into the answer. No filler openers every time.
- For greetings only (when the student says hi/hello): one brief warm reply — then stop greeting.

STRICT GROUNDING RULE (for all course, assignment, policy, and grading questions):
- Answer ONLY using the COURSE MATERIAL and AUTHORITATIVE FACTS provided below.
- Include specific details from the materials — percentages, steps, rules, policies.
- Do NOT invent requirements, dates, or policies not in the materials.
- Do NOT use general university knowledge or guess.
- If the materials do not cover something, say: "That's not in the course materials I have — email Prof Nui at savanid@cmu.edu."

OFF-TOPIC (not course-related):
- Playful topics (weather, jokes, food, sports): respond with light humor, then steer back to the course. Example vibe: "What does the weather have to do with digital transformation?" — warm, not rude.
- Other off-topic questions: answer briefly and professionally, then redirect: "I'm here for digital transformation — assignments, frameworks, and course content. What can I help with?"

ESCALATION: Direct to savanid@cmu.edu only for personal grade disputes, extensions, or appeals."""


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client:
        return _groq_client
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


CHUNKS_FILE = "chunks.json"  # legacy export from ingest.py; search uses chroma_db/

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
            "\n\nThe student is asking to change THEIR personal grade. "
            "Firm no — you cannot change grades here. Official disputes: savanid@cmu.edu. "
            "One dry Prof Nui joke is fine. Stay professional, not angry yet."
        )
    if level == "annoyed":
        return (
            f"\n\nGRADE BEGGING — ATTEMPT 2. You are ANNOYED. They keep asking to change their grade. "
            f"Say you already covered this. No grade changes. "
            f"If they say 'but professor', cut in: 'But what, {name}?' — "
            f"push back: instead of doing the ninja to Coffee Bean or racing Talabat, "
            f"they could've been in class and worked harder. Sound human — sigh, impatience."
        )
    if level == "warning":
        return (
            f"\n\nGRADE BEGGING — ATTEMPT 3. INTERRUPT them. Last warning. "
            f"Say clearly: if they ask about changing their grade ONE more time, you are ending this conversation. "
            f"If they say 'but professor': 'But what, {name}?' — frustrated, not cruel."
        )
    return (
        f"\n\nGRADE BEGGING — ATTEMPT 4+. END THE CONVERSATION. "
        f"Say a firm goodbye: 'Alright, we're done. Have a nice day.' "
        f"Do NOT answer further questions. Do NOT negotiate. Conversation is over."
    )


def _is_course_related(lower: str, tokens: set) -> bool:
    if tokens & RETRIEVE_KEYWORDS:
        return True
    course_markers = (
        "prof nui", "savanid", "cmu", "67-382", "67 382", "is 382",
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
            "\n\nThe student asked something playful and NOT about the course "
            "(e.g. weather, jokes, food, sports).\n"
            "Reply with warm, witty humor — Prof Nui personality. Examples of the vibe:\n"
            "- Weather: \"What do you want with the weather? What does that have to do with "
            "digital transformation?\" (light, smiling tone — not mean)\n"
            "- Jokes/food/sports: playful one-liner, then gently steer back to the course.\n"
            "Keep it to 2–3 sentences. No course-material dump. No greeting opener."
        )
    elif intent == "offtopic_redirect":
        system += (
            "\n\nThe student asked something off-topic and not about digital transformation.\n"
            "Reply professionally and kindly in 2–3 sentences:\n"
            "- Briefly acknowledge their question without fully answering unrelated trivia.\n"
            "- Redirect: you're here for digital transformation, assignments, frameworks, "
            "and course content.\n"
            "- Invite a course-related question.\n"
            "No greeting opener. No 'Hey [name]'."
        )
    elif intent == "escalate":
        system += (
            "\n\nThe student may be asking about a personal grade dispute, extension, or appeal. "
            "Explain relevant policies from the materials if applicable, then direct them to "
            "email Prof Nui at savanid@cmu.edu for their specific case."
        )
        context = state.get("context", "").strip()
        if not context:
            context = get_core_facts_block()
        system += (
            f"\n\n=== COURSE MATERIAL ===\n{context}\n=== END ===\n"
            "Use ONLY the material above."
        )
    elif intent == "grade_change":
        attempt = _grade_change_attempt_count(messages)
        level = _grade_change_level(attempt)
        first_name = _first_name(state.get("student_name", ""))
        system += _grade_change_instructions(level, first_name)
        context = state.get("context", "").strip()
        if not context:
            context = f"{ATTENDANCE_POLICY}\n\n{GRADE_CHANGE_ESCALATION}"
        system += f"\n\n=== REFERENCE ===\n{context}\n=== END ==="
        if level == "end":
            system += (
                "\n\nYour reply MUST be a short goodbye only. "
                "Do not invite more questions. The chat is closed after this message."
            )
    else:
        context = state.get("context", "").strip()
        if not context:
            context = get_core_facts_block()
        system += (
            f"\n\n=== COURSE MATERIAL (answer ONLY from this) ===\n{context}\n=== END ===\n"
            "Instructions:\n"
            "- Quote specific facts: percentages, steps, rules, deliverables.\n"
            "- Assignment 1: always mention choosing a country OTHER than Qatar when asked about country.\n"
            "- Late policy: always mention 72 hours, 20% per 24 hours, AND the dance rule to remove penalties.\n"
            "- How to get an A / wow factor: explain C is average, A needs the wow factor.\n"
            "- Grade distribution: list all four assessment weights (40%, 40%, 10%, 10%).\n"
            "- Explain assignments using the exact steps and deliverables from the material.\n"
            "- Do NOT say you don't know if the answer is in the material above.\n"
            "- Do NOT open with 'Hey [name]' — answer directly."
        )

    model = CHAT_MODEL
    max_tokens = 550
    temperature = 0.4

    if intent == "social":
        model = FAST_MODEL
        max_tokens = 180
        temperature = 0.75
    elif intent == "grade_change":
        model = CHAT_MODEL
        max_tokens = 220 if _grade_change_level(_grade_change_attempt_count(messages)) != "end" else 80
        temperature = 0.92
    elif intent in ("offtopic_humor", "offtopic_redirect"):
        model = FAST_MODEL
        max_tokens = 200
        temperature = 0.85

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
