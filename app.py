import uuid
import streamlit as st
from agent import graph

st.set_page_config(page_title="AskProfNui", page_icon="🎓", layout="centered")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Prof Nui")
    st.markdown("**IS 67-382**  \nDigital Transformation, Strategy and Management  \n**CMU-Q**")
    st.divider()
    st.markdown("#### About you (optional)")
    student_name = st.text_input("Your name", placeholder="e.g. Fatima")
    student_major = st.text_input("Your major", placeholder="e.g. Information Systems")
    student_year = st.text_input("Your year", placeholder="e.g. Junior")
    st.divider()
    st.caption("For grading or deadline questions, contact [savanid@cmu.edu](mailto:savanid@cmu.edu) directly.")

# ── Session state ─────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    welcome = (
        "Hey! Welcome to AskProfNui — your go-to space for everything IS 67-382. "
        "I'm here to help you think through digital transformation, strategy, and "
        "the real business impact of technology.\n\n"
        "One thing to keep in mind as we work together: **C is average. "
        "A is when I say wow.** Every idea you bring here is either moving "
        "toward wow or away from it — and I'm here to help you get there.\n\n"
        "What's on your mind?"
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome}]

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("AskProfNui — Digital Transformation Assistant")

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask Prof Nui anything about the course…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    state_input = {
        "messages": st.session_state.messages,
        "student_name": student_name,
        "student_major": student_major,
        "student_year": student_year,
        "context": "",
        "intent": "",
    }
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    with st.chat_message("assistant"):
        with st.spinner("Prof Nui is thinking…"):
            result = graph.invoke(state_input, config=config)

    reply = result["messages"][-1]["content"]
    st.session_state.messages = result["messages"]

    # Re-render the last assistant message (spinner replaces it)
    with st.chat_message("assistant"):
        st.markdown(reply)
