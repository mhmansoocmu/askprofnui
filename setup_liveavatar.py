#!/usr/bin/env python3
"""One-time setup: register ElevenLabs API key with LiveAvatar."""

import os
import sys

from dotenv import load_dotenv

from liveavatar_client import (
    LiveAvatarError,
    check_elevenlabs_permissions,
    register_elevenlabs_secret,
)

load_dotenv()


def main() -> int:
    liveavatar_api_key = os.getenv("LIVEAVATAR_API_KEY", "").strip()
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()

    missing = []
    if not liveavatar_api_key:
        missing.append("LIVEAVATAR_API_KEY")
    if not elevenlabs_api_key:
        missing.append("ELEVENLABS_API_KEY")

    if missing:
        print("Missing required variables in .env:")
        for name in missing:
            print(f"  - {name}")
        print("\nFill in .env, then run: python setup_liveavatar.py")
        return 1

    missing = check_elevenlabs_permissions(elevenlabs_api_key)
    if missing:
        print("Your ElevenLabs API key is missing required permissions:")
        for permission in missing:
            print(f"  - {permission}")
        print("\nFix in ElevenLabs → Profile → API Keys → edit your key:")
        print("  Enable: Text to Speech, Voices, User, and Conversational AI")
        print("  Or turn off 'Restrict key' for full access.")
        print("\nAlso confirm you are on a paid ElevenLabs plan (free keys block third-party use).")
        print("After updating permissions, run this script again.")
        return 1

    try:
        secret_id = register_elevenlabs_secret(liveavatar_api_key, elevenlabs_api_key)
    except LiveAvatarError as exc:
        print(f"Error: {exc}")
        if "ElevenLabs rejected" in str(exc):
            print("\nIf permissions look correct, confirm your ElevenLabs plan is paid.")
        return 1

    print("Success! ElevenLabs key registered with LiveAvatar.\n")
    print(f"ELEVENLABS_SECRET_ID={secret_id}")
    print("\nAdd that line to your .env file, then run:")
    print("  streamlit run app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
