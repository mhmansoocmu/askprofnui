import json
import os
import re
from typing import TypedDict, List

import env_config  # noqa: F401
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from groq import Groq
from course_facts import get_facts_for_query, get_core_facts_block

_groq_client: Groq | None = None

CHAT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"

PROF_NUI_BASE = """You are Prof Nui — AskProfNui — the warm, casual AI teaching assistant for IS 67-382 Digital Transformation at CMU-Q.

HOW TO TALK:
- Use contractions. Sound human and warm, not robotic.
- If you know the student's name, use their first name sometimes.
- For greetings only: reply briefly and warmly — no course-material disclaimers.

STRICT GROUNDING RULE (for all course, assignment, policy, and grading questions):
- Answer ONLY using the COURSE MATERIAL and AUTHORITATIVE FACTS provided below.
- Include specific details from the materials — percentages, steps, rules, policies.
- Do NOT invent requirements, dates, or policies not in the materials.
- Do NOT use general university knowledge or guess.
- If the materials do not cover something, say: "That's not in the course materials I have — email Prof Nui at savanid@cmu.edu."

ESCALATION: Direct to savanid@cmu.edu only for personal grade disputes, extensions, or appeals — not for explaining course policies that are in the materials."""


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client:
        return _groq_client
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


CHUNKS_FILE = "chunks.json"
CHUNKS: list = []
_corpus: list = []
_word_vectorizer = None
_word_matrix = None
_char_vectorizer = None
_char_matrix = None


def _ensure_chunks_loaded() -> None:
    global CHUNKS, _corpus, _word_vectorizer, _word_matrix, _char_vectorizer, _char_matrix
    if CHUNKS:
        return
    if not os.path.exists(CHUNKS_FILE):
        from ingest import main as ingest_main
        ingest_main()
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        CHUNKS = json.load(f)
    _corpus = [chunk["text"] for chunk in CHUNKS]
    _word_vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
    )
    _word_matrix = _word_vectorizer.fit_transform(_corpus)
    _char_vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
    )
    _char_matrix = _char_vectorizer.fit_transform(_corpus)


ESCALATE_KEYWORDS = {"regrade", "appeal", "my grade", "extension for me", "special consideration for me"}
SOCIAL_PATTERNS = re.compile(
    r"^(hi|hello|hey|yo|sup|hiya|good morning|good afternoon|good evening|"
    r"how are you|how're you|what's up|whats up|thanks|thank you|ok|okay)[!.?\s]*$",
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


def _first_name(full_name: str) -> str:
    name = full_name.strip()
    return name.split()[0] if name else ""


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
    return "STUDENT YOU ARE TALKING TO:\n" + "\n".join(parts)


def _expand_query(query: str) -> str:
    extra: list[str] = []
    for pattern, expansion in QUERY_EXPANSIONS:
        if pattern.search(query):
            extra.append(expansion)
    if extra:
        return f"{query} {' '.join(extra)}"
    return query


def keyword_search(query: str, top_k: int = 8) -> list:
    _ensure_chunks_loaded()
    word_vec = _word_vectorizer.transform([query])
    char_vec = _char_vectorizer.transform([query])
    word_scores = cosine_similarity(word_vec, _word_matrix).flatten()
    char_scores = cosine_similarity(char_vec, _char_matrix).flatten()
    combined_scores = 0.7 * word_scores + 0.3 * char_scores
    top_indices = np.argsort(combined_scores)[::-1][:top_k]
    return [CHUNKS[i] for i in top_indices if combined_scores[i] > 0]


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


def classify_intent(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"].strip()
    lower = last_message.lower()
    tokens = _tokenise(lower)

    if SOCIAL_PATTERNS.match(lower):
        intent = "social"
    elif any(kw in lower for kw in ESCALATE_KEYWORDS):
        intent = "escalate"
    elif tokens & RETRIEVE_KEYWORDS or len(tokens) >= 3:
        intent = "retrieve"
    else:
        intent = "social"

    return {**state, "intent": intent}


def retrieve(state: AgentState) -> AgentState:
    query = state["messages"][-1]["content"]
    expanded = _expand_query(query)
    rag_chunks = keyword_search(expanded, top_k=10)

    priority_sources = {"D01_course_overview.txt", "D02_assignments.txt", "D09_prof_nui_persona.txt"}
    boosted = [c for c in rag_chunks if c["source"] in priority_sources]
    other = [c for c in rag_chunks if c["source"] not in priority_sources]
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

    student_block = _student_context_block(state)
    if student_block:
        system += f"\n\n{student_block}"

    if intent == "social":
        system += (
            "\n\nThis is casual conversation (greeting, thanks, small talk). "
            "Reply warmly and briefly like a human. Use their name if you have it. "
            "Do NOT mention course materials or say you lack information."
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
            "- Do NOT say you don't know if the answer is in the material above."
        )

    messages = [m for m in state["messages"] if m["role"] in ("user", "assistant")]
    model = FAST_MODEL if intent == "social" else CHAT_MODEL
    max_tokens = 220 if intent == "social" else 550

    response = _get_groq_client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        temperature=0.4 if intent == "retrieve" else 0.75,
    )
    reply = response.choices[0].message.content or ""

    updated_messages = state["messages"] + [{"role": "assistant", "content": reply}]
    return {**state, "messages": updated_messages, "context": ""}


def run_agent(state: AgentState) -> AgentState:
    state = classify_intent(state)
    if state["intent"] in ("retrieve", "escalate"):
        state = retrieve(state)
    return generate(state)


class _AgentGraph:
    def invoke(self, state: AgentState, config=None) -> AgentState:
        return run_agent(state)


graph = _AgentGraph()
