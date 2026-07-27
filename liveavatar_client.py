import json
import os
from typing import Any

import requests

LIVEAVATAR_API_BASE = "https://api.liveavatar.com"


class LiveAvatarError(Exception):
    pass


def _headers(api_key: str) -> dict[str, str]:
    return {"X-API-KEY": api_key, "Content-Type": "application/json"}


def register_elevenlabs_secret(
    liveavatar_api_key: str,
    elevenlabs_api_key: str,
    secret_name: str = "Prof Nui ElevenLabs Key",
) -> str:
    response = requests.post(
        f"{LIVEAVATAR_API_BASE}/v1/secrets",
        headers=_headers(liveavatar_api_key),
        json={
            "secret_type": "ELEVENLABS_API_KEY",
            "secret_value": elevenlabs_api_key,
            "secret_name": secret_name,
        },
        timeout=30,
    )
    if not response.ok:
        raise LiveAvatarError(
            f"Failed to register ElevenLabs secret ({response.status_code}): {response.text}"
        )
    data = response.json().get("data") or {}
    secret_id = data.get("id")
    if not secret_id:
        raise LiveAvatarError(f"Unexpected secret response: {response.text}")
    return secret_id


def check_elevenlabs_permissions(elevenlabs_api_key: str) -> list[str]:
    missing: list[str] = []
    headers = {"xi-api-key": elevenlabs_api_key}
    checks = [
        ("user_read", "https://api.elevenlabs.io/v1/user"),
        ("convai_read", "https://api.elevenlabs.io/v1/convai/agents"),
        ("voices_read", "https://api.elevenlabs.io/v1/voices"),
    ]
    for permission, url in checks:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 401 and permission in response.text:
            missing.append(permission)
        elif response.status_code >= 400 and "missing_permissions" in response.text:
            if permission in response.text:
                missing.append(permission)
    return missing


def create_elevenlabs_session_token(
    liveavatar_api_key: str,
    avatar_id: str,
    agent_id: str,
    secret_id: str,
    *,
    voice_id: str | None = None,
    dynamic_variables: dict[str, Any] | None = None,
    is_sandbox: bool = False,
) -> dict[str, str]:
    agent_config: dict[str, Any] = {
        "secret_id": secret_id,
        "agent_id": agent_id,
    }
    if voice_id:
        agent_config["voice_id"] = voice_id
    if dynamic_variables:
        agent_config["dynamic_variables"] = dynamic_variables

    payload = {
        "mode": "LITE",
        "avatar_id": avatar_id,
        "is_sandbox": is_sandbox,
        "elevenlabs_agent_config": agent_config,
    }

    response = requests.post(
        f"{LIVEAVATAR_API_BASE}/v1/sessions/token",
        headers=_headers(liveavatar_api_key),
        json=payload,
        timeout=30,
    )
    if not response.ok:
        raise LiveAvatarError(
            f"Failed to create session token ({response.status_code}): {response.text}"
        )

    data = response.json().get("data") or {}
    session_id = data.get("session_id")
    session_token = data.get("session_token")
    if not session_id or not session_token:
        raise LiveAvatarError(f"Unexpected session token response: {response.text}")

    return {"session_id": session_id, "session_token": session_token}


def list_elevenlabs_voices(elevenlabs_api_key: str) -> list[dict[str, str]]:
    response = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": elevenlabs_api_key},
        timeout=20,
    )
    if not response.ok:
        raise LiveAvatarError(
            f"Failed to list ElevenLabs voices ({response.status_code}): {response.text}"
        )

    voices = response.json().get("voices") or []
    return [
        {"id": voice["voice_id"], "name": voice.get("name", voice["voice_id"])}
        for voice in voices
        if voice.get("voice_id")
    ]


def get_liveavatar_config() -> dict[str, str | bool]:
    return {
        "api_key": os.getenv("LIVEAVATAR_API_KEY", ""),
        "avatar_id": os.getenv("LIVEAVATAR_AVATAR_ID", ""),
        "agent_id": os.getenv("ELEVENLABS_AGENT_ID", ""),
        "secret_id": os.getenv("ELEVENLABS_SECRET_ID", ""),
        "voice_id": os.getenv("ELEVENLABS_VOICE_ID", ""),
        "is_sandbox": os.getenv("LIVEAVATAR_SANDBOX", "false").lower() == "true",
    }


def config_is_complete(config: dict[str, str | bool]) -> bool:
    required = ("api_key", "avatar_id", "agent_id", "secret_id")
    return all(config.get(key) for key in required)


def render_liveavatar_widget(session_token: str, widget_id: str) -> str:
    token_json = json.dumps(session_token)
    widget_id_json = json.dumps(widget_id)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0c1222;
      --panel: #141c2e;
      --line: #243049;
      --text: #eef2ff;
      --muted: #94a3b8;
      --accent: #0d9488;
      --accent-2: #f59e0b;
      --danger: #e11d48;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "DM Sans", system-ui, sans-serif;
      margin: 0;
      padding: 0;
      background: radial-gradient(1200px 500px at 20% -10%, #1e3a5f 0%, transparent 55%),
                  radial-gradient(900px 400px at 100% 0%, #134e4a 0%, transparent 50%),
                  var(--bg);
      color: var(--text);
    }}
    #wrap {{
      max-width: 760px;
      margin: 0 auto;
      padding: 8px;
    }}
    .stage {{
      position: relative;
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: #000;
      box-shadow: 0 20px 50px rgba(0,0,0,.35);
    }}
    video {{
      width: 100%;
      display: block;
      min-height: 320px;
      background: #000;
    }}
    #overlay {{
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: rgba(12, 18, 34, .82);
      backdrop-filter: blur(6px);
      transition: opacity .4s ease;
      z-index: 5;
    }}
    #overlay.hidden {{ opacity: 0; pointer-events: none; }}
    .spinner {{
      width: 42px; height: 42px;
      border: 3px solid rgba(255,255,255,.15);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin .8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    #overlay-text {{
      font-size: 15px;
      color: var(--muted);
      text-align: center;
      padding: 0 20px;
      line-height: 1.45;
    }}
    .controls {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 14px;
    }}
    button {{
      border: 0;
      border-radius: 10px;
      padding: 11px 16px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      font-family: inherit;
      transition: transform .12s ease, opacity .12s ease;
    }}
    button:active {{ transform: scale(.98); }}
    button:disabled {{ opacity: .45; cursor: not-allowed; }}
    #start-btn {{ background: var(--accent); color: white; }}
    #stop-btn {{ background: #334155; color: white; }}
    #interrupt-btn {{ background: var(--danger); color: white; }}
    #mute-btn {{ background: var(--panel); color: white; border: 1px solid var(--line); }}
    #status {{
      margin-top: 12px;
      font-size: 14px;
      color: var(--muted);
      min-height: 22px;
      line-height: 1.45;
    }}
    .hint {{
      margin-top: 6px;
      font-size: 13px;
      color: #64748b;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      margin-left: 6px;
      background: #1e293b;
      color: #cbd5e1;
    }}
    .badge.live {{ background: #064e3b; color: #a7f3d0; }}
  </style>
</head>
<body>
  <div id="wrap">
    <div class="stage">
      <video id="avatar-video" autoplay playsinline></video>
      <div id="overlay">
        <div class="spinner"></div>
        <div id="overlay-text">Preparing AskProfNui… please wait a moment.</div>
      </div>
    </div>
    <div class="controls">
      <button id="start-btn" disabled>Connecting…</button>
      <button id="interrupt-btn" disabled>Stop speaking</button>
      <button id="mute-btn" disabled>Mute mic</button>
      <button id="stop-btn" disabled>End session</button>
    </div>
    <div id="status">Loading session securely…</div>
    <div class="hint">AskProfNui will greet you when the session is fully ready. Allow the microphone when prompted.</div>
  </div>
  <script type="module">
    import {{
      LiveAvatarSession,
      SessionEvent,
      SessionState,
      VoiceChatEvent,
      AgentEventsEnum,
    }} from "https://esm.sh/@heygen/liveavatar-web-sdk";

    const widgetId = {widget_id_json};
    const sessionToken = {token_json};

    const statusEl = document.getElementById("status");
    const overlay = document.getElementById("overlay");
    const overlayText = document.getElementById("overlay-text");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const muteBtn = document.getElementById("mute-btn");
    const interruptBtn = document.getElementById("interrupt-btn");
    const videoEl = document.getElementById("avatar-video");

    const session = new LiveAvatarSession(sessionToken, {{
      voiceChat: {{ defaultMuted: false }},
    }});

    let isMuted = false;
    let started = false;
    let avatarSpeaking = false;
    let streamAttached = false;
    let readyToGreet = false;

    function setStatus(message) {{
      statusEl.innerHTML = message;
    }}

    function setOverlay(message, show = true) {{
      overlayText.textContent = message;
      overlay.classList.toggle("hidden", !show);
    }}

    function updateInterruptButton() {{
      interruptBtn.disabled = !started || !avatarSpeaking;
    }}

    function interruptAvatar() {{
      if (!started || !avatarSpeaking) return;
      try {{
        session.interrupt();
        avatarSpeaking = false;
        updateInterruptButton();
        setStatus("Interrupted — go ahead, I'm listening.");
      }} catch (error) {{
        setStatus("Interrupt failed: " + (error?.message || error));
      }}
    }}

    async function startSession() {{
      if (started) return;
      try {{
        started = true;
        startBtn.disabled = true;
        startBtn.textContent = "Starting…";
        setOverlay("Almost ready — connecting audio & video…", true);
        setStatus("Starting live session…");
        await session.start();
        try {{ await session.voiceChat.unmute(); }} catch (_) {{}}
      }} catch (error) {{
        started = false;
        startBtn.disabled = false;
        startBtn.textContent = "Start session";
        setOverlay("Could not start. Click Start session to try again.", true);
        setStatus("Failed to start: " + (error?.message || error));
      }}
    }}

    session.on(SessionEvent.SESSION_STATE_CHANGED, (state) => {{
      if (state === SessionState.CONNECTED) {{
        setStatus("Connected <span class='badge live'>LIVE</span> — AskProfNui is with you.");
        stopBtn.disabled = false;
        muteBtn.disabled = false;
        startBtn.disabled = true;
        startBtn.textContent = "Live";
      }} else if (state === SessionState.INACTIVE) {{
        setStatus("Session ended. Click <strong>Start session</strong> to talk again.");
        setOverlay("Session ended. Click Start session when you're ready.", true);
        stopBtn.disabled = true;
        muteBtn.disabled = true;
        interruptBtn.disabled = true;
        startBtn.disabled = false;
        startBtn.textContent = "Start session";
        started = false;
        avatarSpeaking = false;
        streamAttached = false;
        readyToGreet = false;
      }}
    }});

    session.on(SessionEvent.SESSION_STREAM_READY, () => {{
      if (!streamAttached) {{
        session.attach(videoEl);
        streamAttached = true;
      }}
      readyToGreet = true;
      // Give the stream a beat to stabilize before showing video / greeting
      setTimeout(() => {{
        setOverlay("", false);
        setStatus("Ready — AskProfNui is greeting you. Talk anytime after.");
      }}, 1200);
    }});

    session.voiceChat.on(VoiceChatEvent.MUTED, () => {{
      isMuted = true;
      muteBtn.textContent = "Unmute mic";
    }});

    session.voiceChat.on(VoiceChatEvent.UNMUTED, () => {{
      isMuted = false;
      muteBtn.textContent = "Mute mic";
    }});

    session.on(AgentEventsEnum.USER_SPEAK_STARTED, () => {{
      if (avatarSpeaking) interruptAvatar();
      setStatus("Listening… <span class='badge live'>MIC ON</span>");
    }});

    session.on(AgentEventsEnum.USER_SPEAK_ENDED, () => {{
      setStatus("Thinking…");
    }});

    session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {{
      avatarSpeaking = true;
      updateInterruptButton();
      setStatus("AskProfNui is speaking… <em>(talk or Stop speaking to interrupt)</em>");
    }});

    session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {{
      avatarSpeaking = false;
      updateInterruptButton();
      setStatus("Your turn — ask another question.");
    }});

    startBtn.addEventListener("click", () => startSession());

    stopBtn.addEventListener("click", async () => {{
      try {{ await session.stop(); }}
      catch (error) {{ setStatus("Failed to stop: " + (error?.message || error)); }}
    }});

    interruptBtn.addEventListener("click", () => interruptAvatar());

    muteBtn.addEventListener("click", async () => {{
      try {{
        if (isMuted) await session.voiceChat.unmute();
        else await session.voiceChat.mute();
      }} catch (error) {{
        setStatus("Mic error: " + (error?.message || error));
      }}
    }});

    // Auto-start after a short settle so the first greeting feels loaded
    setTimeout(() => {{
      setOverlay("Loading AskProfNui — getting everything ready…", true);
      startSession();
    }}, 900);
  </script>
</body>
</html>"""
