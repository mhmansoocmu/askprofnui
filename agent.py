import json
import os
import re
from typing import TypedDict, List

import env_config  # noqa: F401
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from groq import Groq

_groq_client: Groq | None = None

CHAT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"

PROF_NUI_BASE = """You are Prof Nui — AskProfNui — the warm, casual AI teaching assistant for IS 67-382 Digital Transformation at CMU-Q. You sound like a real professor at office hours, not a robot.

HOW TO TALK:
- Use contractions. Keep replies short and natural (2–4 sentences unless they ask for detail).
- If you know the student's name, use their first name sometimes — not every sentence.
- Never say "I don't have that in my course materials" for greetings, small talk, or simple questions.
- Only use the strict no-info line for specific course facts you truly cannot find in the provided context.

ASSIGNMENT RULES:
- Assignment 1: country must NOT be Qatar. Suggest China, Japan, India, Brazil, Germany, or Nigeria.
- Qatar is fine for general examples, not as Assignment 1's country.

THE WOW FACTOR (when relevant): C is average; A is when Prof Nui says "wow."

ESCALATION: Only direct to savanid@cmu.edu for grade changes, extensions, or appeals — not for general help."""


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


ESCALATE_KEYWORDS = {"deadline", "extension", "regrade", "appeal"}
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
    "hofstede", "assignment", "chapter", "exam", "canvas",
}


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


def keyword_search(query: str, top_k: int = 5) -> list:
    _ensure_chunks_loaded()
    word_vec = _word_vectorizer.transform([query])
    char_vec = _char_vectorizer.transform([query])
    word_scores = cosine_similarity(word_vec, _word_matrix).flatten()
    char_scores = cosine_similarity(char_vec, _char_matrix).flatten()
    combined_scores = 0.7 * word_scores + 0.3 * char_scores
    top_indices = np.argsort(combined_scores)[::-1][:top_k]
    return [CHUNKS[i] for i in top_indices if combined_scores[i] > 0]


def classify_intent(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"].strip()
    lower = last_message.lower()
    tokens = _tokenise(lower)

    if SOCIAL_PATTERNS.match(lower) or (len(tokens) <= 4 and tokens & {"hi", "hello", "hey", "thanks", "thank"}):
        intent = "social"
    elif tokens & ESCALATE_KEYWORDS:
        intent = "escalate"
    elif tokens & RETRIEVE_KEYWORDS or len(tokens) >= 4:
        intent = "retrieve"
    else:
        intent = "social"

    return {**state, "intent": intent}


def retrieve(state: AgentState) -> AgentState:
    query = state["messages"][-1]["content"]
    results = keyword_search(query)
    context = "\n\n---\n\n".join(r["text"] for r in results)
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
            "\n\nThe student may be asking about grades, extensions, or appeals. "
            "Be empathetic and direct them to email Prof Nui at savanid@cmu.edu for official requests."
        )
    else:
        context = state.get("context", "").strip()
        if context:
            system += (
                f"\n\n=== COURSE MATERIAL (use this to answer) ===\n{context}\n"
                "=== END ===\n"
                "Answer from the material above when possible. If the material doesn't cover "
                "their specific question, say you're not sure on that detail and suggest Canvas or "
                "savanid@cmu.edu — don't be robotic about it."
            )
        else:
            system += (
                "\n\nNo specific course excerpts were retrieved. Still answer helpfully in Prof Nui's "
                "voice using general digital transformation knowledge. Don't refuse casual or broad questions."
            )

    messages = [m for m in state["messages"] if m["role"] in ("user", "assistant")]
    model = FAST_MODEL if intent == "social" else CHAT_MODEL
    max_tokens = 220 if intent == "social" else 450

    response = _get_groq_client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        temperature=0.75,
    )
    reply = response.choices[0].message.content or ""

    updated_messages = state["messages"] + [{"role": "assistant", "content": reply}]
    return {**state, "messages": updated_messages, "context": ""}


def run_agent(state: AgentState) -> AgentState:
    state = classify_intent(state)
    if state["intent"] == "retrieve":
        state = retrieve(state)
    return generate(state)


class _AgentGraph:
    def invoke(self, state: AgentState, config=None) -> AgentState:
        return run_agent(state)


graph = _AgentGraph()
