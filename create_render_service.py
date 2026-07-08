#!/usr/bin/env python3
"""Create a new Render web service for AskProfNui (fresh onrender.com URL)."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.render.com/v1"
REPO = "https://github.com/mhmansoocmu/askprofnui"
BRANCH = "main"
NEW_SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "profnui-cmuq")
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


def _find_owner_id(token: str) -> str:
    response = requests.get(f"{API}/services?limit=20", headers=_headers(token), timeout=30)
    response.raise_for_status()
    for item in response.json():
        service = item.get("service") or item
        owner_id = service.get("ownerId")
        if owner_id:
            return owner_id
    raise RuntimeError("Could not determine Render ownerId from existing services.")


def _find_service(token: str, name: str) -> dict | None:
    response = requests.get(f"{API}/services?limit=50", headers=_headers(token), timeout=30)
    response.raise_for_status()
    for item in response.json():
        service = item.get("service") or item
        if service.get("name") == name or service.get("slug") == name:
            return service
    return None


def _service_url(service: dict) -> str:
    details = service.get("serviceDetails") or {}
    url = details.get("url") or service.get("url") or ""
    if url and not url.startswith("http"):
        return f"https://{url}"
    return url


def create_service(token: str, owner_id: str) -> dict:
    payload = {
        "type": "web_service",
        "name": NEW_SERVICE_NAME,
        "ownerId": owner_id,
        "repo": REPO,
        "branch": BRANCH,
        "autoDeploy": "yes",
        "serviceDetails": {
            "runtime": "python",
            "plan": "free",
            "region": "oregon",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt && python ingest.py",
                "startCommand": (
                    "streamlit run app.py --server.port $PORT --server.address 0.0.0.0 "
                    "--server.headless true --browser.gatherUsageStats false"
                ),
            },
        },
    }
    response = requests.post(f"{API}/services", headers=_headers(token), json=payload, timeout=60)
    if not response.ok:
        raise RuntimeError(f"Create service failed ({response.status_code}): {response.text}")
    service = response.json().get("service") or response.json()
    return service


def set_env_vars(token: str, service_id: str) -> None:
    for key in KEYS:
        value = os.getenv(key, "").strip()
        if not value:
            print(f"  skip {key} (empty)")
            continue
        response = requests.put(
            f"{API}/services/{service_id}/env-vars/{key}",
            headers=_headers(token),
            json={"value": value},
            timeout=30,
        )
        response.raise_for_status()
        print(f"  set {key}")


def trigger_deploy(token: str, service_id: str) -> None:
    response = requests.post(
        f"{API}/services/{service_id}/deploys",
        headers=_headers(token),
        json={"clearCache": "do_not_clear"},
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    token = os.getenv("RENDER_API_KEY", "").strip()
    if not token:
        print("Add RENDER_API_KEY to .env")
        return 1

    existing = _find_service(token, NEW_SERVICE_NAME)
    if existing:
        service_id = existing["id"]
        print(f"Service {NEW_SERVICE_NAME!r} already exists ({service_id})")
    else:
        owner_id = _find_owner_id(token)
        print(f"Creating Render service {NEW_SERVICE_NAME!r} …")
        created = create_service(token, owner_id)
        service_id = created["id"]
        existing = created
        print(f"Created service {service_id}")

    print("Setting environment variables …")
    set_env_vars(token, service_id)

    print("Triggering deploy …")
    trigger_deploy(token, service_id)

    url = _service_url(existing) or f"https://{NEW_SERVICE_NAME}.onrender.com"
    print(f"\nNew URL: {url}")
    print("Deploy takes ~3–8 minutes (first build includes vector index).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
