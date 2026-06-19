"""Load local .env and Streamlit Cloud secrets into os.environ."""

from __future__ import annotations

import os

from dotenv import load_dotenv


def bootstrap_env() -> None:
    load_dotenv()
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return

        for key in st.secrets:
            value = st.secrets[key]
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:
        pass


bootstrap_env()
