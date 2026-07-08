#!/usr/bin/env python3
"""Push .env values to an existing Render web service via the Render API."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.render.com/v1"
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "profnui-cmuq")
KEYS = (
    "LIVEAVATAR_API_KEY",
    "LIVEAVATAR_AVATAR_ID",
    "LIVEAVATAR_SANDBOX",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ELEVENLABS_AGENT_ID",
    "ELEVENLABS_SECRET_ID",
    "GROQ_API_KEY",
)


def main() -> None:
    token = os.getenv("RENDER_API_KEY", "").strip()
    if not token:
        print("Add RENDER_API_KEY to .env (Render → Account Settings → API Keys)")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    response = requests.get(f"{API}/services?limit=50", headers=headers, timeout=30)
    response.raise_for_status()
    service_id = None
    for item in response.json():
        service = item.get("service") or item
        if service.get("name") == SERVICE_NAME or service.get("slug") == SERVICE_NAME:
            service_id = service["id"]
            break

    if not service_id:
        print(f"Could not find Render service named {SERVICE_NAME!r}")
        sys.exit(1)

    print(f"Updating env vars on {service_id} …")
    for key in KEYS:
        value = os.getenv(key, "").strip()
        if not value:
            print(f"  skip {key} (empty in .env)")
            continue
        put = requests.put(
            f"{API}/services/{service_id}/env-vars/{key}",
            headers=headers,
            json={"value": value},
            timeout=30,
        )
        put.raise_for_status()
        print(f"  set {key}")

    deploy = requests.post(
        f"{API}/services/{service_id}/deploys",
        headers=headers,
        json={"clearCache": "do_not_clear"},
        timeout=30,
    )
    deploy.raise_for_status()
    print("Deploy triggered. Wait ~3 minutes, then refresh https://askprofnui.onrender.com")


if __name__ == "__main__":
    main()
