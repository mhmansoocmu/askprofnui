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

st.set_page_config(
    page_title="AskProfNui",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; max-width: 960px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_elevenlabs_voices(api_key: str) -> list[dict[str, str]]:
    return list_elevenlabs_voices(api_key)


DEFAULT_VOICE_NAME = "Thai Professor Nui"


def _default_voice_index(voices: list[dict[str, str]], preferred_id: str) -> int:
    for i, voice in enumerate(voices):
        if voice["name"] == DEFAULT_VOICE_NAME:
            return i
    if preferred_id:
        for i, voice in enumerate(voices):
            if voice["id"] == preferred_id:
                return i
    for i, voice in enumerate(voices):
        if "professor nui" in voice["name"].lower():
            return i
    return 0


def _student_dynamic_variables(name: str, major: str, year: str) -> dict[str, str]:
    variables = {}
    if name.strip():
        variables["student_name"] = name.strip()
    if major.strip():
        variables["student_major"] = major.strip()
    if year.strip():
        variables["student_year"] = year.strip()
    return variables


def _init_session_state() -> None:
    defaults = {
        "thread_id": str(uuid.uuid4()),
        "messages": [{
            "role": "assistant",
            "content": (
                "Hey! Welcome to AskProfNui — your space for everything IS 67-382. "
                "Ask me about digital transformation, strategy, assignments, or the wow factor.\n\n"
                "Use the **Live Avatar** tab to talk to Prof Nui with your voice, "
                "or **Text Chat** to type your question."
            ),
        }],
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

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Prof Nui")
    st.markdown(
        "**IS 67-382**  \nDigital Transformation, Strategy & Management  \n**CMU-Q**"
    )
    st.divider()
    st.markdown("### How to use")
    st.markdown(
        """
1. Open **Live Avatar**
2. Fill in your details (optional)
3. Click **Start live session**
4. Allow microphone access
5. Speak anytime — interrupt by talking or click **Stop speaking**
        """
    )
    st.divider()
    missing = missing_keys()
    if missing:
        st.error("Missing server keys")
        for key in missing:
            st.code(key, language=None)
        st.caption(
            "Render → askprofnui → Environment → add `SECRETS_TOML` "
            "with your full secrets.toml contents, then Save & redeploy."
        )
    else:
        st.success("Server keys loaded")
    st.divider()
    st.caption(
        "Grading or deadline questions → [savanid@cmu.edu](mailto:savanid@cmu.edu)"
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.title("AskProfNui")
st.caption("AI teaching assistant for Digital Transformation — CMU-Q")

tab_live, tab_text = st.tabs(["Live Avatar", "Text Chat"])


@st.fragment
def live_avatar_panel() -> None:
    st.subheader("Talk to Prof Nui")
    st.markdown(
        "Voice conversation powered by your course materials on **digital transformation**, "
        "strategy, culture, and assignments."
    )

    if not config_is_complete(config):
        st.warning("Live avatar is not configured on this server.")
        st.info(
            "Add these in **Render → askprofnui → Environment**: "
            "`LIVEAVATAR_API_KEY`, `LIVEAVATAR_AVATAR_ID`, "
            "`ELEVENLABS_AGENT_ID`, `ELEVENLABS_SECRET_ID`, `ELEVENLABS_API_KEY`. "
            "Then click **Save Changes** and redeploy."
        )
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
        st.error("No ElevenLabs voices found. Check your API key permissions.")
        return

    voice_labels = {v["name"]: v["id"] for v in voices}
    voice_names = list(voice_labels.keys())
    default_index = _default_voice_index(voices, str(config.get("voice_id") or "").strip())

    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("Your name", value=st.session_state.student_name, key="live_name")
    with col2:
        major = st.text_input("Major", value=st.session_state.student_major, key="live_major")
    with col3:
        year = st.text_input("Year", value=st.session_state.student_year, key="live_year")

    voice_name = st.selectbox(
        "Voice",
        options=voice_names,
        index=default_index,
        key="live_voice",
    )
    selected_voice_id = voice_labels[voice_name]

    if st.button("Start live session", type="primary", key="start_live_session_btn"):
        st.session_state.student_name = name
        st.session_state.student_major = major
        st.session_state.student_year = year
        with st.spinner("Connecting to Prof Nui…"):
            try:
                token_data = create_elevenlabs_session_token(
                    str(config["api_key"]),
                    str(config["avatar_id"]),
                    str(config["agent_id"]),
                    str(config["secret_id"]),
                    voice_id=selected_voice_id,
                    dynamic_variables=_student_dynamic_variables(name, major, year),
                    is_sandbox=bool(config["is_sandbox"]),
                )
                st.session_state.liveavatar_token = token_data["session_token"]
                st.session_state.liveavatar_widget_id = token_data["session_id"]
                st.session_state.liveavatar_voice_id = selected_voice_id
            except LiveAvatarError as exc:
                st.error(str(exc))
                return
        st.success("Session ready — click **Start session** in the player below.")
        st.rerun()

    if st.session_state.liveavatar_token:
        st.caption(f"Voice: **{voice_name}**")
        components.html(
            render_liveavatar_widget(
                st.session_state.liveavatar_token,
                st.session_state.liveavatar_widget_id,
            ),
            height=520,
            scrolling=False,
        )
    else:
        st.info("Fill in your details and click **Start live session** above.")


@st.fragment
def text_chat_panel() -> None:
    st.subheader("Text chat with Prof Nui")
    st.caption("Grounded in IS 67-382 course materials via Groq.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about digital transformation, assignments, frameworks…"):
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
            with st.spinner("Prof Nui is thinking…"):
                try:
                    result = graph.invoke(state_input, config=chat_config)
                    reply = result["messages"][-1]["content"]
                    st.session_state.messages = result["messages"]
                    st.markdown(reply)
                except Exception as exc:
                    st.error(f"Text chat error: {exc}")
                    if not os.getenv("GROQ_API_KEY", "").strip():
                        st.info(
                            "Add `GROQ_API_KEY` in **Render → askprofnui → Environment**, "
                            "save, then redeploy."
                        )
                    else:
                        st.info("Check that GROQ_API_KEY is set in your environment.")


with tab_live:
    live_avatar_panel()

with tab_text:
    text_chat_panel()
