import env_config  # noqa: F401 — load secrets before other imports
import os
import uuid

import streamlit as st
import streamlit.components.v1 as components

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
5. Speak your question clearly
        """
    )
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
    voices = _cached_elevenlabs_voices(elevenlabs_key)
    if not voices:
        st.error("No ElevenLabs voices found.")
        return

    voice_labels = {v["name"]: v["id"] for v in voices}
    default_voice = str(config.get("voice_id") or "").strip()
    default_index = 0
    if default_voice:
        for i, voice in enumerate(voices):
            if voice["id"] == default_voice:
                default_index = i
                break

    with st.form("live_session_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Your name", value=st.session_state.student_name)
        with col2:
            major = st.text_input("Major", value=st.session_state.student_major)
        with col3:
            year = st.text_input("Year", value=st.session_state.student_year)

        voice_name = st.selectbox(
            "Voice",
            options=list(voice_labels.keys()),
            index=default_index,
        )
        submitted = st.form_submit_button("Start live session", type="primary")

    selected_voice_id = voice_labels[voice_name]

    if submitted:
        st.session_state.student_name = name
        st.session_state.student_major = major
        st.session_state.student_year = year
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
            st.success("Session ready — click **Start session** in the player below.")
        except LiveAvatarError as exc:
            st.error(str(exc))

    if st.session_state.liveavatar_token:
        components.html(
            render_liveavatar_widget(
                st.session_state.liveavatar_token,
                st.session_state.liveavatar_widget_id,
            ),
            height=460,
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
