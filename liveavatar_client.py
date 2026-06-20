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
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 0;
      background: #0f1117;
      color: #f5f5f5;
    }}
    #wrap {{ max-width: 720px; margin: 0 auto; }}
    video {{
      width: 100%;
      border-radius: 12px;
      background: #000;
      min-height: 300px;
    }}
    .controls {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    button {{
      border: 0; border-radius: 8px; padding: 10px 16px;
      cursor: pointer; font-weight: 600; font-size: 14px;
    }}
    #start-btn {{ background: #7c3aed; color: white; }}
    #stop-btn {{ background: #374151; color: white; }}
    #interrupt-btn {{ background: #dc2626; color: white; }}
    #interrupt-btn:disabled {{ background: #4b5563; opacity: 0.6; cursor: not-allowed; }}
    #mute-btn {{ background: #1f2937; color: white; }}
    #status {{
      margin-top: 12px; font-size: 14px; color: #d1d5db;
      min-height: 22px; line-height: 1.4;
    }}
    .hint {{
      margin-top: 8px; font-size: 13px; color: #9ca3af;
    }}
    .badge {{
      display: inline-block; padding: 2px 8px; border-radius: 999px;
      font-size: 12px; font-weight: 600; margin-left: 6px;
      background: #374151; color: #e5e7eb;
    }}
    .badge.live {{ background: #065f46; color: #d1fae5; }}
  </style>
</head>
<body>
  <div id="wrap">
    <video id="avatar-video" autoplay playsinline></video>
    <div class="controls">
      <button id="start-btn">Start session</button>
      <button id="interrupt-btn" disabled>Stop speaking</button>
      <button id="mute-btn" disabled>Mute mic</button>
      <button id="stop-btn" disabled>End session</button>
    </div>
    <div id="status">Click <strong>Start session</strong>, allow microphone access, then talk.</div>
    <div class="hint">You can interrupt anytime — just start talking, or click <strong>Stop speaking</strong>.</div>
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

    function setStatus(message) {{
      statusEl.innerHTML = message;
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

    session.on(SessionEvent.SESSION_STATE_CHANGED, (state) => {{
      if (state === SessionState.CONNECTED) {{
        setStatus("Connected <span class='badge live'>LIVE</span> — talk anytime, even if I'm mid-sentence.");
        stopBtn.disabled = false;
        muteBtn.disabled = false;
        startBtn.disabled = true;
      }} else if (state === SessionState.INACTIVE) {{
        setStatus("Session ended. Click <strong>Start session</strong> to talk again.");
        stopBtn.disabled = true;
        muteBtn.disabled = true;
        interruptBtn.disabled = true;
        startBtn.disabled = false;
        started = false;
        avatarSpeaking = false;
        streamAttached = false;
      }}
    }});

    session.on(SessionEvent.SESSION_STREAM_READY, () => {{
      if (!streamAttached) {{
        session.attach(videoEl);
        streamAttached = true;
      }}
      setStatus("Video ready — your mic is on. Talk anytime.");
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
      if (avatarSpeaking) {{
        interruptAvatar();
      }}
      setStatus("Listening to you… <span class='badge live'>MIC ON</span>");
    }});

    session.on(AgentEventsEnum.USER_SPEAK_ENDED, () => {{
      setStatus("Thinking…");
    }});

    session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {{
      avatarSpeaking = true;
      updateInterruptButton();
      setStatus("Prof Nui is answering… <em>(talk or click Stop speaking to interrupt)</em>");
    }});

    session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {{
      avatarSpeaking = false;
      updateInterruptButton();
      setStatus("Your turn — ask another question.");
    }});

    startBtn.addEventListener("click", async () => {{
      if (started) return;
      try {{
        started = true;
        setStatus("Starting session…");
        await session.start();
        try {{ await session.voiceChat.unmute(); }} catch (_) {{}}
      }} catch (error) {{
        started = false;
        setStatus("Failed to start: " + (error?.message || error));
      }}
    }});

    stopBtn.addEventListener("click", async () => {{
      try {{
        await session.stop();
      }} catch (error) {{
        setStatus("Failed to stop: " + (error?.message || error));
      }}
    }});

    interruptBtn.addEventListener("click", () => {{
      interruptAvatar();
    }});

    muteBtn.addEventListener("click", async () => {{
      try {{
        if (isMuted) await session.voiceChat.unmute();
        else await session.voiceChat.mute();
      }} catch (error) {{
        setStatus("Mic error: " + (error?.message || error));
      }}
    }});
  </script>
</body>
</html>"""
