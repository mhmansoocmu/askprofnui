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


def render_liveavatar_widget(
    session_token: str,
    widget_id: str,
    opening_message: str = "",
    student_first_name: str = "",
) -> str:
    token_json = json.dumps(session_token)
    widget_id_json = json.dumps(widget_id)
    opening_json = json.dumps(
        opening_message
        or "Hi, how are you? I'm AskProfNui. What can I help you with today for digital transformation?"
    )
    student_name_json = json.dumps(student_first_name.strip() or "there")
    html = r"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0c1222;
      --panel: #141c2e;
      --line: #243049;
      --text: #eef2ff;
      --muted: #94a3b8;
      --accent: #0d9488;
      --accent-2: #f59e0b;
      --danger: #e11d48;
    }
    * { box-sizing: border-box; }
    body {
      font-family: "DM Sans", system-ui, sans-serif;
      margin: 0;
      padding: 0;
      background: radial-gradient(1200px 500px at 20% -10%, #1e3a5f 0%, transparent 55%),
                  radial-gradient(900px 400px at 100% 0%, #134e4a 0%, transparent 50%),
                  var(--bg);
      color: var(--text);
    }
    #wrap { max-width: 980px; margin: 0 auto; padding: 8px; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(240px, 0.9fr);
      gap: 12px;
      align-items: stretch;
    }
    @media (max-width: 720px) {
      .layout { grid-template-columns: 1fr; }
    }
    .stage {
      position: relative;
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: #000;
      box-shadow: 0 20px 50px rgba(0,0,0,.35);
      min-height: 340px;
    }
    video {
      width: 100%;
      display: block;
      min-height: 340px;
      background: #000;
      object-fit: cover;
    }
    #overlay {
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
    }
    #overlay.hidden { opacity: 0; pointer-events: none; }
    .spinner {
      width: 42px; height: 42px;
      border: 3px solid rgba(255,255,255,.15);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    #overlay-text {
      font-size: 15px;
      color: var(--muted);
      text-align: center;
      padding: 0 20px;
      line-height: 1.45;
    }
    .sources {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(180deg, #172033 0%, #121a2b 100%);
      padding: 14px 14px 12px;
      display: flex;
      flex-direction: column;
      min-height: 340px;
      max-height: 420px;
    }
    .sources h2 {
      font-family: "Fraunces", Georgia, serif;
      font-size: 1.05rem;
      margin: 0 0 4px;
      color: #eef2ff;
      letter-spacing: -0.01em;
    }
    .sources .sub {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 12px;
      line-height: 1.4;
    }
    #citations {
      overflow-y: auto;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-right: 4px;
    }
    .cite {
      border-left: 3px solid var(--accent);
      background: rgba(13, 148, 136, .08);
      border-radius: 0 10px 10px 0;
      padding: 10px 12px;
      animation: fadeIn .35s ease;
    }
    .cite .src {
      font-size: 12px;
      font-weight: 700;
      color: #5eead4;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 6px;
    }
    .cite .quote {
      font-size: 13.5px;
      line-height: 1.45;
      color: #e2e8f0;
      font-style: italic;
    }
    .cite-empty {
      color: #64748b;
      font-size: 13px;
      line-height: 1.5;
      padding: 8px 2px;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: none; }
    }
    .controls {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    button {
      border: 0;
      border-radius: 10px;
      padding: 11px 16px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      font-family: inherit;
      transition: transform .12s ease, opacity .12s ease;
    }
    button:active { transform: scale(.98); }
    button:disabled { opacity: .45; cursor: not-allowed; }
    #start-btn { background: var(--accent); color: white; }
    #stop-btn { background: #334155; color: white; }
    #interrupt-btn { background: var(--danger); color: white; }
    #mute-btn { background: var(--panel); color: white; border: 1px solid var(--line); }
    #status {
      margin-top: 12px;
      font-size: 14px;
      color: var(--muted);
      min-height: 22px;
      line-height: 1.45;
    }
    .hint {
      margin-top: 6px;
      font-size: 13px;
      color: #64748b;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      margin-left: 6px;
      background: #1e293b;
      color: #cbd5e1;
    }
    .badge.live { background: #064e3b; color: #a7f3d0; }
  </style>
</head>
<body>
  <div id="wrap">
    <div class="layout">
      <div class="stage">
        <video id="avatar-video" autoplay playsinline></video>
        <div id="overlay">
          <div class="spinner"></div>
          <div id="overlay-text">Preparing AskProfNui… please wait a moment.</div>
        </div>
      </div>
      <aside class="sources" aria-live="polite">
        <h2>Sources &amp; quotes</h2>
        <div class="sub">When AskProfNui cites research or course lines, they appear here.</div>
        <div id="citations">
          <div class="cite-empty" id="cite-empty">No citations yet — ask about a concept, framework, or assignment.</div>
        </div>
      </aside>
    </div>
    <div class="controls">
      <button id="start-btn" disabled>Connecting…</button>
      <button id="interrupt-btn" disabled>Stop speaking</button>
      <button id="mute-btn" disabled>Mute mic</button>
      <button id="stop-btn" disabled>End session</button>
    </div>
    <div id="status">Loading session securely…</div>
    <div class="hint">Wait for LIVE — she greets you after audio/video are ready. Sources show on the right.</div>
  </div>
  <script type="module">
    import {
      ElevenLabsAgentSession,
      LiveAvatarSession,
      SessionEvent,
      SessionState,
      VoiceChatEvent,
      AgentEventsEnum,
    } from "https://esm.sh/@heygen/liveavatar-web-sdk@0.0.18";

    const widgetId = __WIDGET_ID__;
    const sessionToken = __TOKEN__;
    const openingMessage = __OPENING__;
    const studentName = __STUDENT_NAME__;

    const statusEl = document.getElementById("status");
    const overlay = document.getElementById("overlay");
    const overlayText = document.getElementById("overlay-text");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const muteBtn = document.getElementById("mute-btn");
    const interruptBtn = document.getElementById("interrupt-btn");
    const videoEl = document.getElementById("avatar-video");
    const citationsEl = document.getElementById("citations");
    const citeEmpty = document.getElementById("cite-empty");

    const SessionClass = ElevenLabsAgentSession || LiveAvatarSession;
    const session = new SessionClass(sessionToken, {
      voiceChat: { defaultMuted: false },
    });

    let isMuted = false;
    let started = false;
    let avatarSpeaking = false;
    let streamAttached = false;
    let greetingSent = false;
    let gradeChangeAttempts = 0;
    let forceEndAfterSpeak = false;
    let endingSession = false;
    let endBackupTimer = null;
    let lastGradeCueAt = 0;
    const seenCitations = new Set();
    const gradeChangeRe =
      /\b(change|bump|raise|fix|update|increase)\b.{0,40}\bgrade\b|\b(regrade|re-grade)\b|\bgive me (a )?(better|higher) grade\b|\bcan you change\b|\bwill you change\b|\bbut professor\b|\bbut prof\b|\bplease change my\b|\bmy grade\b.{0,20}\b(please|change|bump|higher|better)\b/i;
    const goodbyeHeardRe =
      /\bwe'?re done\b|\bi'?m ending this session\b|\bbye\b.{0,80}\bdigital transformation\b|\bgo put that energy\b/i;

    function gradeScript(attempt) {
      const name = studentName || "there";
      if (attempt <= 1) {
        return 'Say ONLY this exact sentence, nothing else: "I can\'t change your grade."';
      }
      if (attempt === 2) {
        return (
          'Say ONLY this exact line, nothing else: "You should\'ve worked harder in class than wasting your time and my time — and now you\'re asking for a higher grade? Come on, ' +
          name +
          '."'
        );
      }
      if (attempt === 3) {
        return (
          'Say ONLY this exact angry line, nothing else: "Stop, ' +
          name +
          ' — or I will end this session."'
        );
      }
      return (
        'GRADE CHANGE ATTEMPT 4 — FINAL. Say this longer goodbye EXACTLY, then IMMEDIATELY call end_call: ' +
        '"We\'re done, ' + name +
        '. I\'m ending this session right now. Bye — go put that energy into digital transformation instead of asking me to change your grade." ' +
        'Do not say anything after that.'
      );
    }

    function enforceGradeChange(transcript) {
      if (!transcript || endingSession) return;
      if (!gradeChangeRe.test(transcript)) return;
      const now = Date.now();
      // Avoid double-counting the same utterance from repeated transcripts
      if (now - lastGradeCueAt < 4500) return;
      lastGradeCueAt = now;
      gradeChangeAttempts += 1;
      const attempt = Math.min(gradeChangeAttempts, 4);
      const cue =
        "OVERRIDE — GRADE CHANGE ATTEMPT " +
        attempt +
        " of 4. Ignore other personality. " +
        gradeScript(attempt);
      try {
        if (typeof session.sendContextualUpdate === "function") {
          session.sendContextualUpdate(cue);
        }
      } catch (err) {
        console.warn("grade cue failed", err);
      }
      if (attempt >= 4) {
        forceEndAfterSpeak = true;
        setStatus("Final goodbye — session will end when she finishes…");
        // Hard backup: end even if speak-ended events never fire
        if (endBackupTimer) clearTimeout(endBackupTimer);
        endBackupTimer = setTimeout(() => forceEndSession("backup timer"), 14000);
      } else {
        setStatus("Grade-change attempt " + attempt + " — script enforced.");
      }
    }

    async function forceEndSession(reason) {
      if (endingSession) return;
      endingSession = true;
      forceEndAfterSpeak = false;
      if (endBackupTimer) {
        clearTimeout(endBackupTimer);
        endBackupTimer = null;
      }
      setStatus("Ending session…");
      try {
        try { session.interrupt(); } catch (_) {}
        await session.stop();
      } catch (err) {
        console.warn("force stop failed (" + reason + ")", err);
      }
      setStatus("Session ended after her goodbye.");
      setOverlay("Session ended. AskProfNui closed the office hours.", true);
      stopBtn.disabled = true;
      muteBtn.disabled = true;
      interruptBtn.disabled = true;
      startBtn.disabled = false;
      startBtn.textContent = "Start session";
      started = false;
      avatarSpeaking = false;
    }

    function maybeForceEndSession() {
      if (!forceEndAfterSpeak || endingSession) return;
      // Let the longer goodbye finish speaking before hanging up
      setTimeout(() => forceEndSession("speak ended"), 2800);
    }

    function maybeEndFromGoodbyeSpeech(text) {
      if (!text || endingSession) return;
      if (gradeChangeAttempts < 4 && !forceEndAfterSpeak) return;
      if (!goodbyeHeardRe.test(text)) return;
      forceEndAfterSpeak = true;
      setStatus("Goodbye heard — ending session when she finishes…");
      if (endBackupTimer) clearTimeout(endBackupTimer);
      endBackupTimer = setTimeout(() => forceEndSession("goodbye heard"), 6000);
    }

    function setStatus(message) {
      statusEl.innerHTML = message;
    }

    function setOverlay(message, show = true) {
      overlayText.textContent = message;
      overlay.classList.toggle("hidden", !show);
    }

    function updateInterruptButton() {
      interruptBtn.disabled = !started || !avatarSpeaking;
    }

    function escapeHtml(text) {
      return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function addCitation(source, quote) {
      const src = (source || "").trim();
      const q = (quote || "").trim();
      if (!src || !q) return;
      const key = (src + "|" + q).toLowerCase();
      if (seenCitations.has(key)) return;
      seenCitations.add(key);
      if (citeEmpty) citeEmpty.remove();
      const card = document.createElement("div");
      card.className = "cite";
      card.innerHTML =
        '<div class="src">' + escapeHtml(src) + "</div>" +
        '<div class="quote">“' + escapeHtml(q) + '”</div>';
      citationsEl.prepend(card);
    }

    function extractCitationFromSpeech(text) {
      if (!text) return;
      const according = text.match(
        /According to\s+([^:.!?]+?)(?:[:\-—,]|\s+—\s+)\s*[“"']?([^”"']+?)[”"']?(?:[.!?]|$)/i
      );
      if (according) {
        addCitation(according[1].trim(), according[2].trim());
        return;
      }
      const course = text.match(
        /(?:From|In)\s+(our\s+)?course materials[^\-:]*[:\-—]\s*[“"']?([^”"']+?)[”"']?(?:[.!?]|$)/i
      );
      if (course) {
        addCitation("Course materials", course[2].trim());
      }
    }

    function handleClientToolCall(raw) {
      const data = raw?.data || raw || {};
      const eventType =
        raw?.elevenlabs_event_type ||
        data?.type ||
        data?.elevenlabs_event_type ||
        "";
      const isTool =
        String(eventType).includes("client_tool_call") ||
        data.tool_name ||
        data.toolName;
      if (!isTool && !data.tool_call_id && !data.toolCallId) return;

      const name = data.tool_name || data.toolName || data.name || "";
      const params = data.parameters || data.tool_params || data.arguments || {};
      const toolCallId = data.tool_call_id || data.toolCallId || "";

      let parsed = params;
      if (typeof params === "string") {
        try { parsed = JSON.parse(params); } catch (_) { parsed = {}; }
      }

      if (String(name).toLowerCase() === "show_citation") {
        addCitation(parsed.source || parsed.Source, parsed.quote || parsed.Quote);
        if (toolCallId && typeof session.sendClientToolResult === "function") {
          try {
            session.sendClientToolResult({
              toolCallId,
              result: "Citation shown on screen",
              sourceEventId: raw?.event_id,
            });
          } catch (err) {
            console.warn("sendClientToolResult failed", err);
          }
        }
      } else if (toolCallId && typeof session.sendClientToolResult === "function") {
        try {
          session.sendClientToolResult({
            toolCallId,
            result: "ok",
            sourceEventId: raw?.event_id,
          });
        } catch (_) {}
      }
    }

    function interruptAvatar() {
      if (!started || !avatarSpeaking) return;
      try {
        session.interrupt();
        avatarSpeaking = false;
        updateInterruptButton();
        setStatus("Interrupted — go ahead, I'm listening.");
      } catch (error) {
        setStatus("Interrupt failed: " + (error?.message || error));
      }
    }

    function triggerGreeting() {
      if (greetingSent) return;
      greetingSent = true;
      try {
        const cue =
          "The student can see and hear you now. Respond with ONLY this opening greeting, warmly, then wait: " +
          openingMessage +
          " Never say 'are you still there'.";
        if (typeof session.sendContextualUpdate === "function") {
          session.sendContextualUpdate(cue);
        }
        setTimeout(() => {
          try {
            if (typeof session.sendUserMessage === "function") {
              session.sendUserMessage("Hi — I'm ready, please greet me.");
            } else if (typeof session.sendUserActivity === "function") {
              session.sendUserActivity();
            }
          } catch (err) {
            console.warn("Greeting nudge failed:", err);
          }
        }, 500);
        setStatus("AskProfNui is introducing herself…");
      } catch (error) {
        console.warn("Greeting trigger failed:", error);
        setStatus("Connected — say hi if AskProfNui is quiet.");
      }
    }

    async function startSession() {
      if (started) return;
      try {
        started = true;
        greetingSent = false;
        startBtn.disabled = true;
        startBtn.textContent = "Starting…";
        setOverlay("Connecting audio & video — please wait…", true);
        setStatus("Starting live session…");
        await session.start();
        try { await session.voiceChat.unmute(); } catch (_) {}
      } catch (error) {
        started = false;
        startBtn.disabled = false;
        startBtn.textContent = "Start session";
        setOverlay("Could not start. Click Start session to try again.", true);
        setStatus("Failed to start: " + (error?.message || error));
      }
    }

    session.on(SessionEvent.SESSION_STATE_CHANGED, (state) => {
      if (state === SessionState.CONNECTED) {
        setStatus("Connected <span class='badge live'>LIVE</span> — finishing setup…");
        stopBtn.disabled = false;
        muteBtn.disabled = false;
        startBtn.disabled = true;
        startBtn.textContent = "Live";
      } else if (state === SessionState.INACTIVE || state === SessionState.DISCONNECTED) {
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
        greetingSent = false;
        gradeChangeAttempts = 0;
        forceEndAfterSpeak = false;
        endingSession = false;
        if (endBackupTimer) {
          clearTimeout(endBackupTimer);
          endBackupTimer = null;
        }
      }
    });

    session.on(SessionEvent.SESSION_STREAM_READY, () => {
      if (!streamAttached) {
        session.attach(videoEl);
        streamAttached = true;
      }
      setOverlay("Almost ready — starting your greeting…", true);
      setTimeout(() => {
        setOverlay("", false);
        setStatus("Ready <span class='badge live'>LIVE</span>");
        triggerGreeting();
      }, 2000);
    });

    session.voiceChat.on(VoiceChatEvent.MUTED, () => {
      isMuted = true;
      muteBtn.textContent = "Unmute mic";
    });

    session.voiceChat.on(VoiceChatEvent.UNMUTED, () => {
      isMuted = false;
      muteBtn.textContent = "Mute mic";
    });

    session.on(AgentEventsEnum.USER_SPEAK_STARTED, () => {
      if (avatarSpeaking) interruptAvatar();
      setStatus("Listening… <span class='badge live'>MIC ON</span>");
    });

    session.on(AgentEventsEnum.USER_SPEAK_ENDED, () => {
      setStatus("Thinking…");
    });

    session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {
      avatarSpeaking = true;
      updateInterruptButton();
      setStatus("AskProfNui is speaking…");
    });

    session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {
      avatarSpeaking = false;
      updateInterruptButton();
      setStatus("Your turn — ask a question.");
      maybeForceEndSession();
    });

    session.on(AgentEventsEnum.AVATAR_TRANSCRIPTION, (evt) => {
      const text = evt?.text || "";
      extractCitationFromSpeech(text);
      maybeEndFromGoodbyeSpeech(text);
    });

    session.on(AgentEventsEnum.USER_TRANSCRIPTION, (evt) => {
      enforceGradeChange(evt?.text || "");
    });

    if (AgentEventsEnum.USER_TRANSCRIPTION_CHUNK) {
      session.on(AgentEventsEnum.USER_TRANSCRIPTION_CHUNK, (evt) => {
        enforceGradeChange(evt?.text || "");
      });
    }
    if (AgentEventsEnum.ELEVENLABS_AGENT_EVENT) {
      session.on(AgentEventsEnum.ELEVENLABS_AGENT_EVENT, (evt) => {
        handleClientToolCall(evt);
      });
    }

    startBtn.addEventListener("click", () => startSession());

    stopBtn.addEventListener("click", async () => {
      try { await session.stop(); }
      catch (error) { setStatus("Failed to stop: " + (error?.message || error)); }
    });

    interruptBtn.addEventListener("click", () => interruptAvatar());

    muteBtn.addEventListener("click", async () => {
      try {
        if (isMuted) await session.voiceChat.unmute();
        else await session.voiceChat.mute();
      } catch (error) {
        setStatus("Mic error: " + (error?.message || error));
      }
    });

    setTimeout(() => {
      setOverlay("Loading AskProfNui…", true);
      startSession();
    }, 700);
  </script>
</body>
</html>"""
    return (
        html.replace("__WIDGET_ID__", widget_id_json)
        .replace("__TOKEN__", token_json)
        .replace("__OPENING__", opening_json)
        .replace("__STUDENT_NAME__", student_name_json)
    )
