#!/usr/bin/env python3
"""Deploy AskProfNui to Streamlit Community Cloud via the official API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

API_BASE = "https://api.streamlit.io/v1"
REPO = "mhmansoo/askprofnui"
BRANCH = "main"
MAIN_FILE = "app.py"
APP_NAME = "askprofnui"
SECRETS_PATH = Path(".streamlit/secrets.toml")


def _token() -> str:
    token = os.getenv("STREAMLIT_API_TOKEN", "").strip()
    if not token:
        print(
            "Missing STREAMLIT_API_TOKEN.\n"
            "Create one at https://share.streamlit.io → Settings → API tokens,\n"
            "then run:\n"
            "  export STREAMLIT_API_TOKEN='your-token'\n"
            "  python deploy_streamlit.py"
        )
        sys.exit(1)
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _load_secrets() -> str:
    if not SECRETS_PATH.is_file():
        print(f"Missing {SECRETS_PATH}. Copy values from .env into that file first.")
        sys.exit(1)
    return SECRETS_PATH.read_text(encoding="utf-8")


def _find_app(token: str) -> dict | None:
    response = requests.get(f"{API_BASE}/apps", headers=_headers(token), timeout=30)
    response.raise_for_status()
    for app in response.json().get("apps", []):
        if app.get("repo") == REPO and app.get("mainFile") == MAIN_FILE:
            return app
    return None


def main() -> None:
    token = _token()
    secrets = _load_secrets()
    headers = _headers(token)

    app = _find_app(token)
    if app is None:
        print(f"Deploying {REPO} ({BRANCH}/{MAIN_FILE}) …")
        response = requests.post(
            f"{API_BASE}/apps",
            headers=headers,
            json={
                "repo": REPO,
                "branch": BRANCH,
                "mainFile": MAIN_FILE,
                "appName": APP_NAME,
            },
            timeout=60,
        )
        response.raise_for_status()
        app = response.json()
        print(f"Created app: {app.get('url', app.get('id'))}")
    else:
        print(f"Found existing app: {app.get('url', app.get('id'))}")

    app_id = app["id"]
    print("Updating secrets …")
    response = requests.put(
        f"{API_BASE}/apps/{app_id}/secrets",
        headers=headers,
        json={"secrets": secrets},
        timeout=60,
    )
    response.raise_for_status()
    print("Secrets updated (app will restart).")

    response = requests.get(f"{API_BASE}/apps/{app_id}", headers=headers, timeout=30)
    response.raise_for_status()
    details = response.json()
    print(f"\nPublic URL: {details.get('url')}")
    print(f"Status: {details.get('status')}")


if __name__ == "__main__":
    main()
