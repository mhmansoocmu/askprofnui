# AskProfNui

AI teaching assistant for **IS 67-382: Digital Transformation, Strategy and Management** at CMU-Q.

Students can talk to a live Prof Nui avatar (voice) or use text chat. Answers are grounded in course materials in `documents/`.

## Features

- **Live Avatar** — real-time voice conversation via LiveAvatar + ElevenLabs Agent
- **Text Chat** — Groq/LangGraph backup with course-material retrieval
- **Course knowledge** — 9 document files synced to the ElevenLabs agent (RAG)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
python setup_liveavatar.py
python sync_elevenlabs_knowledge.py
python fix_elevenlabs_audio.py
streamlit run app.py
```

Open http://localhost:8501

## One-time admin setup

| Step | Command |
|------|---------|
| Link ElevenLabs → LiveAvatar | `python setup_liveavatar.py` |
| Upload course docs to agent | `python sync_elevenlabs_knowledge.py` |
| Fix audio format (PCM 24k) | `python fix_elevenlabs_audio.py` |

## Deploy for other users (Streamlit Community Cloud)

1. Push this repo to **GitHub** (do not commit `.env`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, branch, and main file: `app.py`
4. Under **Advanced settings → Secrets**, paste:

```toml
LIVEAVATAR_API_KEY = "your-key"
LIVEAVATAR_AVATAR_ID = "your-avatar-uuid"
LIVEAVATAR_SANDBOX = "false"
ELEVENLABS_API_KEY = "your-key"
ELEVENLABS_VOICE_ID = "your-voice-id"
ELEVENLABS_AGENT_ID = "agent_..."
ELEVENLABS_SECRET_ID = "your-secret-uuid"
GROQ_API_KEY = "your-key"
```

5. Deploy — you'll get a public URL like `https://askprofnui.streamlit.app`

Run the three admin scripts **once** from your machine (with the same keys) before students use the live link.

## Environment variables

See `.env.example` for all required keys.

## Student usage

1. Open the shared link
2. **Live Avatar** tab → fill optional details → **Start live session**
3. Click **Start session** in the player → allow microphone
4. Speak your question; wait for Prof Nui to finish before asking again

## Project structure

```
app.py                    # Streamlit app (public-facing)
agent.py                  # Groq text chat + RAG
liveavatar_client.py      # LiveAvatar session + player widget
sync_elevenlabs_knowledge.py  # Admin: upload documents/ to agent
documents/                # Course material source files
```

## Notes

- Live avatar uses **ElevenLabs Agent** (not Groq) for voice conversations
- Text chat uses **Groq** with local TF-IDF retrieval over `documents/`
- HeyGen/LiveAvatar and ElevenLabs are billed separately per usage
