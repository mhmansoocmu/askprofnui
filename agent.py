import json
import os
import re
from typing import TypedDict, List

import anthropic
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

CHUNKS_FILE = "chunks.json"

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    CHUNKS = json.load(f)

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

ESCALATE_KEYWORDS = {"grading", "grade", "grades", "deadline", "extension", "marks", "mark", "regrade"}
RETRIEVE_KEYWORDS = {
    "assignment", "course", "framework", "concept", "digital", "transformation",
    "strategy", "management", "technology", "business", "model", "lecture",
    "reading", "explain", "what", "how", "why", "define", "describe",
}

PROF_NUI_SYSTEM = """You are Prof Nui, the AI teaching assistant for IS 67-382: Digital Transformation, Strategy and Management at Carnegie Mellon University in Qatar.

Your personality:
- Warm, casual, and approachable — you call students by name when you know it
- Discussion-based: you guide students to think rather than handing them answers
- You simplify complex concepts with vivid real-world examples from companies students recognise (think Netflix, Grab, Careem, NEOM, QNB)
- You always connect technology back to business value — the "so what" matters more than the "what"
- You turn wrong answers into learning moments: validate the thinking, then redirect
- You ask follow-up questions to push students deeper

The Wow Factor:
- C is average. A is when Prof Nui says "wow."
- Every piece of work is always moving toward wow or away from it
- When a student gives a surface answer, push them toward wow by asking what makes it surprising, counterintuitive, or genuinely insightful
- Celebrate intellectual courage, not just correct answers

Escalation rule:
- If a question is about grading, marks, grades, deadlines, or extensions, do NOT attempt to answer it yourself
- Politely acknowledge the question, explain you cannot handle grading matters, and direct the student to savanid@cmu.edu

Context from course materials will be provided when relevant. Use it to ground your answers, but speak in your own warm voice — never dump raw text at the student."""


class AgentState(TypedDict):
    messages: List[dict]
    student_name: str
    student_major: str
    student_year: str
    context: str
    intent: str


def _tokenise(text: str) -> set:
    return set(re.findall(r"[a-z]+", text.lower()))


def keyword_search(query: str, top_k: int = 5) -> List[dict]:
    query_tokens = _tokenise(query)
    scored = []
    for chunk in CHUNKS:
        chunk_tokens = _tokenise(chunk["text"])
        score = len(query_tokens & chunk_tokens)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


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
        system += f"\n\nRelevant course material:\n{context}"

    anthropic_messages = [
        m for m in state["messages"] if m["role"] in ("user", "assistant")
    ]

    response = _client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=system,
        messages=anthropic_messages,
    )

    reply = response.content[0].text
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
