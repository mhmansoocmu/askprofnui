import env_config  # noqa: F401 — load secrets before other imports
import os
import uuid

import streamlit as st
import streamlit.components.v1 as components

from env_config import missing_keys
from agent import graph
from liveavatar_client import (
    LiveAvatarError,
    config_is_complete,
    create_elevenlabs_session_token,
    get_liveavatar_config,
    list_elevenlabs_voices,
    render_liveavatar_widget,
)
from student_profile import (
    elevenlabs_dynamic_variables,
    first_name,
    text_welcome,
)

st.set_page_config(
    page_title="AskProfNui",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

    html, body, [class*="css"] {
      font-family: "DM Sans", system-ui, sans-serif;
    }
    .block-container {
      padding-top: 1.4rem;
      padding-bottom: 2.5rem;
      max-width: 980px;
    }
    .apn-hero {
      background:
        radial-gradient(900px 320px at 0% 0%, rgba(13,148,136,.22), transparent 55%),
        radial-gradient(700px 280px at 100% 0%, rgba(245,158,11,.12), transparent 50%),
        linear-gradient(180deg, #141c2e 0%, #0c1222 100%);
      border: 1px solid #243049;
      border-radius: 20px;
      padding: 1.4rem 1.6rem 1.25rem;
      margin-bottom: 1rem;
    }
    .apn-hero h1 {
      font-family: "Fraunces", Georgia, serif;
      font-size: 2.1rem;
      line-height: 1.15;
      margin: 0 0 .35rem 0;
      color: #eef2ff;
      letter-spacing: -0.02em;
    }
    .apn-hero p {
      margin: 0;
      color: #94a3b8;
      font-size: 1.02rem;
    }
    .stTabs [data-baseweb="tab-list"] {
      gap: 8px;
      background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
      border-radius: 10px;
      padding: 10px 16px;
    }
    div[data-testid="stSidebar"] {
      background: #101827;
    }
    .stButton > button[kind="primary"] {
      background: #0d9488;
      border: none;
    }
    .stButton > button[kind="primary"]:hover {
      background: #0f766e;
      border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_elevenlabs_voices(api_key: str) -> list[dict[str, str]]:
    return list_elevenlabs_voices(api_key)


DEFAULT_VOICE_NAME = "Thai Professor Nui"


def _default_voice_index(voices: list[dict[str, str]], preferred_id: str) -> int:
    if preferred_id:
        for i, voice in enumerate(voices):
            if voice["id"] == preferred_id:
                return i
    for i, voice in enumerate(voices):
        if voice["name"] == DEFAULT_VOICE_NAME:
            return i
    for i, voice in enumerate(voices):
        if "professor nui" in voice["name"].lower() or "askprofnui" in voice["name"].lower():
            return i
    return 0


def _init_session_state() -> None:
    defaults = {
        "thread_id": str(uuid.uuid4()),
        "messages": [{"role": "assistant", "content": text_welcome()}],
        "profile_saved": False,
        "liveavatar_token": "",
        "liveavatar_widget_id": "",
        "liveavatar_voice_id": "",
        "student_name": "",
        "student_major": "",
        "student_year": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state()
config = get_liveavatar_config()

with st.sidebar:
    st.markdown("## AskProfNui")
    st.markdown("**Digital Transformation**  \nStrategy & Management  \n**CMU-Q**")
    st.divider()
    st.markdown("### Your profile")
    profile_name = st.text_input(
        "Your name",
        value=st.session_state.student_name,
        key="sidebar_name",
        placeholder="e.g. Yaman",
    )
    profile_major = st.text_input(
        "Major",
        value=st.session_state.student_major,
        key="sidebar_major",
        placeholder="e.g. Information Systems",
    )
    profile_year = st.text_input(
        "Year",
        value=st.session_state.student_year,
        key="sidebar_year",
        placeholder="e.g. Junior",
    )
    if st.button("Save profile", type="primary", use_container_width=True):
        prev = (
            st.session_state.student_name,
            st.session_state.student_major,
            st.session_state.student_year,
        )
        st.session_state.student_name = profile_name.strip()
        st.session_state.student_major = profile_major.strip()
        st.session_state.student_year = profile_year.strip()
        st.session_state.profile_saved = bool(st.session_state.student_name)
        st.session_state.messages = [{
            "role": "assistant",
            "content": text_welcome(
                st.session_state.student_name,
                st.session_state.student_major,
                st.session_state.student_year,
            ),
        }]
        if prev != (
            st.session_state.student_name,
            st.session_state.student_major,
            st.session_state.student_year,
        ):
            st.session_state.liveavatar_token = ""
            st.session_state.liveavatar_widget_id = ""
        first = first_name(st.session_state.student_name)
        st.success(f"Saved! I'll call you {first}." if first else "Profile saved.")
        st.rerun()
    elif st.session_state.profile_saved and st.session_state.student_name:
        st.caption(f"Talking to **{first_name(st.session_state.student_name)}**")

    st.divider()
    st.markdown("### How to use")
    st.markdown(
        """
1. Save your name (so the greeting is personal)
2. **Live Avatar** → **Start live session**
3. Wait for the loading overlay — AskProfNui greets you
4. Speak anytime
        """
    )
    st.divider()
    missing = missing_keys()
    if missing:
        st.error("Missing server keys")
        for key in missing:
            st.code(key, language=None)
    else:
        st.success("Ready")
    st.caption("Official grading questions → savanid@cmu.edu")

st.markdown(
    """
    <div class="apn-hero">
      <h1>AskProfNui</h1>
      <p>Your digital transformation teaching assistant — CMU-Q</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_live, tab_text = st.tabs(["Live Avatar", "Text Chat"])


@st.fragment
def live_avatar_panel() -> None:
    st.subheader("Talk live")
    st.caption("Voice office hours grounded in digital transformation course materials.")

    if not config_is_complete(config):
        st.warning("Live avatar is not configured on this server.")
        return

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not elevenlabs_key:
        st.error("ELEVENLABS_API_KEY is missing on this server.")
        return

    try:
        voices = _cached_elevenlabs_voices(elevenlabs_key)
    except LiveAvatarError as exc:
        st.error(f"Could not load voices: {exc}")
        return

    if not voices:
        st.error("No ElevenLabs voices found.")
        return

    voice_labels = {v["name"]: v["id"] for v in voices}
    voice_names = list(voice_labels.keys())
    default_index = _default_voice_index(voices, str(config.get("voice_id") or "").strip())

    if st.session_state.student_name:
        st.success(
            f"Ready for **{first_name(st.session_state.student_name)}** · "
            f"{st.session_state.student_major or 'major TBD'} · "
            f"{st.session_state.student_year or 'year TBD'}"
        )
    else:
        st.info("Add your name in the sidebar so AskProfNui can greet you personally.")

    voice_name = st.selectbox(
        "Voice",
        options=voice_names,
        index=default_index,
        key="live_voice",
    )
    selected_voice_id = voice_labels[voice_name]

    if st.button("Start live session", type="primary", key="start_live_session_btn"):
        with st.spinner("Preparing AskProfNui — waiting for a clean connection…"):
            try:
                token_data = create_elevenlabs_session_token(
                    str(config["api_key"]),
                    str(config["avatar_id"]),
                    str(config["agent_id"]),
                    str(config["secret_id"]),
                    voice_id=selected_voice_id,
                    dynamic_variables=elevenlabs_dynamic_variables(
                        st.session_state.student_name,
                        st.session_state.student_major,
                        st.session_state.student_year,
                    ),
                    is_sandbox=bool(config["is_sandbox"]),
                )
                st.session_state.liveavatar_token = token_data["session_token"]
                st.session_state.liveavatar_widget_id = token_data["session_id"]
                st.session_state.liveavatar_voice_id = selected_voice_id
            except LiveAvatarError as exc:
                st.error(str(exc))
                return
        st.rerun()

    if st.session_state.liveavatar_token:
        st.caption(f"Voice: **{voice_name}** · session auto-starts when ready")
        components.html(
            render_liveavatar_widget(
                st.session_state.liveavatar_token,
                st.session_state.liveavatar_widget_id,
            ),
            height=560,
            scrolling=False,
        )
    else:
        st.info("Click **Start live session** — AskProfNui will load, then greet you.")


@st.fragment
def text_chat_panel() -> None:
    st.subheader("Text chat")
    if st.session_state.student_name:
        st.caption(f"Chatting as {first_name(st.session_state.student_name)}")
    else:
        st.caption("Save your profile in the sidebar for a personal greeting")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about digital transformation…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        state_input = {
            "messages": st.session_state.messages,
            "student_name": st.session_state.student_name,
            "student_major": st.session_state.student_major,
            "student_year": st.session_state.student_year,
            "context": "",
            "intent": "",
        }
        chat_config = {"configurable": {"thread_id": st.session_state.thread_id}}

        with st.chat_message("assistant"):
            with st.spinner("…"):
                try:
                    result = graph.invoke(state_input, config=chat_config)
                    reply = result["messages"][-1]["content"]
                    st.session_state.messages = result["messages"]
                    st.markdown(reply)
                except Exception as exc:
                    st.error(f"Text chat error: {exc}")


with tab_live:
    live_avatar_panel()

with tab_text:
    text_chat_panel()
