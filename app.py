import os
import time
import uuid
import requests
import streamlit as st
import streamlit.components.v1 as components
from agent import graph

st.set_page_config(page_title="AskProfNui", page_icon="🎓", layout="centered")


def speak_with_avatar(text: str) -> str:
    api_key = os.getenv("HEYGEN_API_KEY")
    avatar_id = os.getenv("HEYGEN_AVATAR_ID")

    url = "https://api.heygen.com/v2/video/generate"
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "input_text": text,
                "voice_id": "en-US-JennyNeural"
            }
        }],
        "dimension": {"width": 1280, "height": 720}
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data.get("data", {}).get("video_id", "")


def get_video_url(video_id: str) -> str:
    api_key = os.getenv("HEYGEN_API_KEY")
    url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    headers = {"X-Api-Key": api_key}

    for _ in range(30):
        response = requests.get(url, headers=headers)
        data = response.json()
        status = data.get("data", {}).get("status", "")
        if status == "completed":
            return data.get("data", {}).get("video_url", "")
        time.sleep(3)
    return ""


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Prof Nui")
    st.markdown("**IS 67-382**  \nDigital Transformation, Strategy and Management  \n**CMU-Q**")
    st.divider()
    st.markdown("#### About you (optional)")
    student_name = st.text_input("Your name", placeholder="e.g. Fatima")
    student_major = st.text_input("Your major", placeholder="e.g. Information Systems")
    student_year = st.text_input("Your year", placeholder="e.g. Junior")
    st.divider()
    use_avatar = st.toggle("Show Prof Nui Avatar", value=False)
    st.session_state["use_avatar"] = use_avatar
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

components.iframe(
    src="https://app.heygen.com/embeds/1bc5999500d4413fa4386ea0793a7749",
    width=560,
    height=315,
    scrolling=False
)

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

    with st.chat_message("assistant"):
        st.markdown(reply)
        if st.session_state.get("use_avatar", False):
            with st.spinner("Prof Nui is responding..."):
                video_id = speak_with_avatar(reply)
                if video_id:
                    video_url = get_video_url(video_id)
                    if video_url:
                        st.video(video_url)
