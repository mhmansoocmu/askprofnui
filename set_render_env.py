#!/usr/bin/env python3
"""Resume, configure, and deploy the AskProfNui Render service."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.render.com/v1"
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "askprofnui")
SERVICE_URL = os.getenv("RENDER_SERVICE_URL", "https://askprofnui.onrender.com")
BUILD_COMMAND = "pip install -r requirements.txt && python ingest.py"
START_COMMAND = (
    "streamlit run app.py --server.port $PORT --server.address 0.0.0.0 "
    "--server.headless true --browser.gatherUsageStats false"
)
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


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _find_service(token: str) -> dict:
    response = requests.get(f"{API}/services?limit=50", headers=_headers(token), timeout=30)
    response.raise_for_status()
    for item in response.json():
        service = item.get("service") or item
        if service.get("name") == SERVICE_NAME or service.get("slug") == SERVICE_NAME:
            return service
    raise RuntimeError(f"Could not find Render service named {SERVICE_NAME!r}")


def _resume_if_needed(token: str, service_id: str, service: dict) -> None:
    if service.get("suspended") in ("suspended", True):
        print(f"Resuming suspended service {service_id} …")
        response = requests.post(
            f"{API}/services/{service_id}/resume",
            headers=_headers(token),
            timeout=30,
        )
        response.raise_for_status()
        print("Service resumed.")


def _ensure_build_commands(token: str, service_id: str) -> None:
    payload = {
        "serviceDetails": {
            "envSpecificDetails": {
                "buildCommand": BUILD_COMMAND,
                "startCommand": START_COMMAND,
            }
        }
    }
    response = requests.patch(
        f"{API}/services/{service_id}",
        headers=_headers(token),
        json=payload,
        timeout=30,
    )
    if response.ok:
        print("Build/start commands updated.")
    else:
        print(f"Warning: could not update build commands ({response.status_code})")


def main() -> int:
    token = os.getenv("RENDER_API_KEY", "").strip()
    if not token:
        print("Add RENDER_API_KEY to .env (Render → Account Settings → API Keys)")
        return 1

    service = _find_service(token)
    service_id = service["id"]
    print(f"Found {SERVICE_NAME} ({service_id})")

    _resume_if_needed(token, service_id, service)
    _ensure_build_commands(token, service_id)

    print("Updating environment variables …")
    for key in KEYS:
        value = os.getenv(key, "").strip()
        if not value:
            print(f"  skip {key} (empty in .env)")
            continue
        response = requests.put(
            f"{API}/services/{service_id}/env-vars/{key}",
            headers=_headers(token),
            json={"value": value},
            timeout=30,
        )
        response.raise_for_status()
        print(f"  set {key}")

    print("Triggering deploy …")
    response = requests.post(
        f"{API}/services/{service_id}/deploys",
        headers=_headers(token),
        json={"clearCache": "do_not_clear"},
        timeout=30,
    )
    response.raise_for_status()
    print(f"Deploy started. Wait ~5–8 minutes, then open {SERVICE_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
