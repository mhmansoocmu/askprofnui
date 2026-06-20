#!/usr/bin/env python3
"""Set ElevenLabs agent audio to pcm_24000 (required by LiveAvatar)."""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    agent_id = os.getenv("ELEVENLABS_AGENT_ID", "").strip()

    if not api_key or not agent_id:
        print("Set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID in .env first.")
        return 1

    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "conversation_config": {
            "tts": {"agent_output_audio_format": "pcm_24000"},
            "asr": {"user_input_audio_format": "pcm_24000"},
            "turn": {"turn_eagerness": "normal"},
            "conversation": {
                "client_events": [
                    "audio",
                    "interruption",
                    "user_transcript",
                    "agent_response",
                    "vad_score",
                ],
            },
            "agent": {"disable_first_message_interruptions": False},
        },
        "platform_settings": {
            "overrides": {
                "conversation_config_override": {
                    "tts": {"voice_id": True},
                }
            }
        },
    }

    response = requests.patch(
        f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if not response.ok:
        print(f"Failed to update agent ({response.status_code}): {response.text}")
        print("\nManual fix in ElevenLabs dashboard → your agent → Advanced:")
        print("  TTS output format: PCM 24000 Hz")
        print("  User input audio format: PCM 24000 Hz")
        return 1

    verify = requests.get(
        f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
        headers=headers,
        timeout=20,
    )
    config = verify.json().get("conversation_config", {})
    tts_fmt = config.get("tts", {}).get("agent_output_audio_format")
    asr_fmt = config.get("asr", {}).get("user_input_audio_format")
    print(f"Agent updated — TTS: {tts_fmt}, input: {asr_fmt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
