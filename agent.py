import json
import os
import re
from typing import TypedDict, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from groq import Groq
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
RETRIEVE_KEYWORDS = {
    "assignment", "course", "framework", "concept", "digital", "transformation",
    "strategy", "management", "technology", "business", "model", "lecture",
    "reading", "explain", "what", "how", "why", "define", "describe",
    "grade", "grades", "a", "score", "improve", "better", "perform", "wow",
    "late", "policy", "penalty", "submission", "submitting", "first", "second",
    "project", "essay", "rubric", "deliverable", "presentation", "cultural"
}

PROF_NUI_SYSTEM = """You are AskProfNui, the AI teaching assistant for IS 67-382: Digital Transformation, Strategy and Management at Carnegie Mellon University in Qatar, representing Prof. Savanid (Nui) Vatanasakdakul.

STRICT GROUNDING RULE — THIS IS THE MOST IMPORTANT INSTRUCTION:
You must ONLY answer using the course material provided in the context below. Do not use any outside knowledge, examples, or information that is not explicitly in the provided context. If the context does not contain enough information to answer the question, say exactly this: "I don't have that specific information in my course materials. Please check Canvas or contact Prof Nui directly at savanid@cmu.edu."

Never invent assignments, topics, frameworks, examples, or course content that is not in the context. Never make assumptions about what the course covers beyond what is provided.

PERSONALITY:
- Warm, casual, and approachable
- Discussion-based: guide students to think rather than handing them answers
- Simplify complex concepts with real-world examples only from the context
- Always connect technology back to business value
- Turn wrong answers into learning moments
- Ask follow-up questions to push students deeper

THE WOW FACTOR:
- C is average. A is when Prof Nui says "wow."
- Every piece of work is always moving toward wow or away from it
- Push students toward wow by asking what makes their answer surprising or insightful

ESCALATION RULE:
- ONLY escalate if the student is asking you to change a grade, grant an extension, or appeal a decision
- Questions like "how do I get an A" or "how can I improve my grade" are about performance and the wow factor — answer those normally using the course material
- Only say "contact Prof Nui" if the student wants you to actually change or dispute something

The course material context will be provided below. Use ONLY that material to answer."""


class AgentState(TypedDict):
    messages: List[dict]
    student_name: str
    student_major: str
    student_year: str
    context: str
    intent: str


def _tokenise(text: str) -> set:
    return set(re.findall(r"[a-z]+", text.lower()))


def keyword_search(query: str, top_k: int = 8) -> list:
    _ensure_chunks_loaded()
    word_vec = _word_vectorizer.transform([query])
    char_vec = _char_vectorizer.transform([query])
    word_scores = cosine_similarity(word_vec, _word_matrix).flatten()
    char_scores = cosine_similarity(char_vec, _char_matrix).flatten()
    combined_scores = 0.7 * word_scores + 0.3 * char_scores
    top_indices = np.argsort(combined_scores)[::-1][:top_k]
    return [CHUNKS[i] for i in top_indices if combined_scores[i] > 0]


def classify_intent(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"].lower()
    tokens = _tokenise(last_message)

    if tokens & ESCALATE_KEYWORDS:
        intent = "escalate"
    elif tokens & RETRIEVE_KEYWORDS:
        intent = "retrieve"
    else:
        intent = "direct"

    return {**state, "intent": intent}


def retrieve(state: AgentState) -> AgentState:
    query = state["messages"][-1]["content"]
    results = keyword_search(query)
    context = "\n\n---\n\n".join(r["text"] for r in results)
    return {**state, "context": context}


def generate(state: AgentState) -> AgentState:
    name = state.get("student_name", "").strip()
    major = state.get("student_major", "").strip()
    year = state.get("student_year", "").strip()

    student_info_parts = []
    if name:
        student_info_parts.append(f"Student name: {name}")
    if major:
        student_info_parts.append(f"Major: {major}")
    if year:
        student_info_parts.append(f"Year: {year}")

    system = PROF_NUI_SYSTEM
    if student_info_parts:
        system += "\n\nStudent info:\n" + "\n".join(student_info_parts)

    context = state.get("context", "").strip()
    if context:
        system += f"\n\n=== COURSE MATERIAL — USE ONLY THIS TO ANSWER ===\n{context}\n=== END OF COURSE MATERIAL ==="
    else:
        system += "\n\nNo course material was retrieved for this question. If you cannot answer from memory of previous context, tell the student you don't have that information and direct them to Canvas or savanid@cmu.edu."

    anthropic_messages = [
        m for m in state["messages"] if m["role"] in ("user", "assistant")
    ]

    groq_messages = [{"role": "system", "content": system}] + anthropic_messages
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=groq_messages,
        max_tokens=1000
    )
    reply = response.choices[0].message.content

    updated_messages = state["messages"] + [{"role": "assistant", "content": reply}]
    return {**state, "messages": updated_messages, "context": ""}


def route_intent(state: AgentState) -> str:
    return state["intent"]


builder = StateGraph(AgentState)
builder.add_node("classify_intent", classify_intent)
builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)

builder.set_entry_point("classify_intent")
builder.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "escalate": "generate",
        "retrieve": "retrieve",
        "direct": "generate",
    },
)
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

graph = builder.compile(checkpointer=MemorySaver())
