#!/usr/bin/env python3
"""Deploy AskProfNui to Streamlit Community Cloud."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

import requests

API_BASE = "https://api.streamlit.io/v1"
REPO = "mhmansoocmu/askprofnui"
BRANCH = "main"
MAIN_FILE = "app.py"
APP_NAME = "askprofnui"
PUBLIC_URL = "https://askprofnui.streamlit.app"
DEPLOY_URL = (
    "https://share.streamlit.io/deploy"
    f"?repository={REPO}&branch={BRANCH}&mainModule={MAIN_FILE}&subdomain={APP_NAME}"
)
SECRETS_PATH = Path(".streamlit/secrets.toml")
ENV_PATH = Path(".env")


def _token() -> str | None:
    token = os.getenv("STREAMLIT_API_TOKEN", "").strip()
    return token or None


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _sync_secrets_from_env() -> None:
    if not ENV_PATH.is_file():
        return
    lines: list[str] = []
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        lines.append(f'{key.strip()} = "{value.strip()}"')
    if lines:
        SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SECRETS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_secrets() -> str:
    _sync_secrets_from_env()
    if not SECRETS_PATH.is_file():
        print(f"Missing {SECRETS_PATH}. Fill in .env first.")
        sys.exit(1)
    return SECRETS_PATH.read_text(encoding="utf-8")


def _find_app(token: str) -> dict | None:
    response = requests.get(f"{API_BASE}/apps", headers=_headers(token), timeout=30)
    response.raise_for_status()
    for app in response.json().get("apps", []):
        if app.get("repo") == REPO and app.get("mainFile") == MAIN_FILE:
            return app
    return None


def _open_browser_deploy() -> None:
    print(f"Opening deploy page: {DEPLOY_URL}")
    webbrowser.open(DEPLOY_URL)
    print(f"\nAfter deploy, your public URL should be: {PUBLIC_URL}")
    print("\nIn Advanced settings → Secrets, paste the contents of:")
    print(f"  {SECRETS_PATH.resolve()}")
    print("\nThen click Deploy and wait ~2 minutes.")


def _deploy_via_api(token: str) -> None:
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
    print("Secrets updated.")

    print("Restarting app …")
    response = requests.post(
        f"{API_BASE}/apps/{app_id}/restart",
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()

    response = requests.get(f"{API_BASE}/apps/{app_id}", headers=headers, timeout=30)
    response.raise_for_status()
    details = response.json()
    print(f"\nPublic URL: {details.get('url')}")
    print(f"Status: {details.get('status')}")


def main() -> None:
    _load_secrets()
    token = _token()
    if token is None:
        _open_browser_deploy()
        if sys.platform == "darwin":
            subprocess.run(["open", DEPLOY_URL], check=False)
        return

    try:
        _deploy_via_api(token)
    except requests.RequestException as exc:
        print(f"Streamlit API deploy failed: {exc}")
        print("Falling back to browser deploy …")
        _open_browser_deploy()
        if sys.platform == "darwin":
            subprocess.run(["open", DEPLOY_URL], check=False)


if __name__ == "__main__":
    main()
