"""Load secrets from .env, Render env vars, or a single SECRETS_TOML blob."""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv

REQUIRED_KEYS = (
    "LIVEAVATAR_API_KEY",
    "LIVEAVATAR_AVATAR_ID",
    "LIVEAVATAR_SANDBOX",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ELEVENLABS_AGENT_ID",
    "ELEVENLABS_SECRET_ID",
    "GROQ_API_KEY",
)


def _clean(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _set_env(key: str, value: str) -> None:
    cleaned = _clean(value)
    if cleaned:
        os.environ[key] = cleaned


def _load_dotenv_format(text: str) -> None:
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        _set_env(key.strip(), value.strip())


def _load_secrets_toml_path() -> None:
    for path in (".streamlit/secrets.toml", "secrets.toml"):
        if os.path.isfile(path):
            _load_dotenv_format(open(path, encoding="utf-8").read())


def bootstrap_env() -> None:
    load_dotenv()
    _load_secrets_toml_path()

    secrets_blob = os.getenv("SECRETS_TOML", "")
    if secrets_blob.strip():
        _load_dotenv_format(secrets_blob)

    for key in REQUIRED_KEYS:
        raw = os.getenv(key)
        if raw:
            _set_env(key, raw)

    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return

        for key in st.secrets:
            value = st.secrets[key]
            if isinstance(value, str):
                _set_env(key, value)
    except Exception:
        pass


def missing_keys() -> list[str]:
    return [key for key in REQUIRED_KEYS if not os.getenv(key, "").strip()]


bootstrap_env()
