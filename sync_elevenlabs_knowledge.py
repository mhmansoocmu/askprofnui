"""Sync IS 67-382 course documents to the ElevenLabs agent knowledge base."""

import hashlib
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

DOCUMENTS_DIR = Path("documents")
MANIFEST_FILE = Path("elevenlabs_knowledge_manifest.json")
PROMPT_FILE = Path("elevenlabs_agent_prompt.txt")
ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"

COURSE_KB_FOLDER_NAME = "IS 67-382 Digital Transformation"


def _load_first_message() -> str:
    return "{{session_opening}}"


def _dynamic_variable_placeholders() -> dict[str, str]:
    from student_profile import session_opening

    return {
        "student_name": "there",
        "student_major": "",
        "student_year": "",
        "student_intro_line": "Good to see you.",
        "session_opening": session_opening("", "", ""),
    }


def _load_system_prompt() -> str:
    text = PROMPT_FILE.read_text(encoding="utf-8")
    parts = text.split("---")
    if len(parts) >= 2:
        return parts[1].strip()
    return text.strip()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {"documents": {}}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _headers(api_key: str) -> dict[str, str]:
    return {"xi-api-key": api_key}


def upload_document(api_key: str, path: Path, display_name: str) -> str:
    with path.open("rb") as handle:
        response = requests.post(
            f"{ELEVENLABS_API_BASE}/convai/knowledge-base/file",
            headers=_headers(api_key),
            files={"file": (path.name, handle, "text/plain")},
            data={"name": display_name},
            timeout=120,
        )
    if not response.ok:
        raise RuntimeError(
            f"Failed to upload {path.name} ({response.status_code}): {response.text}"
        )
    doc_id = response.json().get("id")
    if not doc_id:
        raise RuntimeError(f"Unexpected upload response for {path.name}: {response.text}")
    return doc_id


def update_agent(api_key: str, agent_id: str, knowledge_entries: list[dict]) -> None:
    payload = {
        "conversation_config": {
            "agent": {
                "first_message": _load_first_message(),
                "language": "en",
                "disable_first_message_interruptions": False,
                "dynamic_variables": {
                    "dynamic_variable_placeholders": _dynamic_variable_placeholders(),
                },
                "prompt": {
                    "prompt": _load_system_prompt(),
                    "llm": "gemini-2.0-flash",
                    "temperature": 0.85,
                    "max_tokens": 250,
                    "knowledge_base": knowledge_entries,
                    "built_in_tools": {
                        "end_call": {
                            "name": "end_call",
                            "description": (
                                "End the voice session. Use when: (1) the student asks to change, "
                                "regrade, or bump THEIR grade for the FOURTH time after your last "
                                "warning — say 'Alright, we're done. Have a nice day.' then call this; "
                                "(2) the student says goodbye and the conversation is naturally over."
                            ),
                            "type": "system",
                            "params": {"system_tool_type": "end_call"},
                        }
                    },
                    "rag": {
                        "enabled": True,
                        "embedding_model": "e5_mistral_7b_instruct",
                        "max_documents_length": 50000,
                        "max_retrieved_rag_chunks_count": 8,
                        "max_vector_distance": 0.78,
                    },
                },
            },
            "turn": {
                "turn_timeout": 10,
                "turn_eagerness": "eager",
                "silence_end_call_timeout": 600,
            },
            "conversation": {
                "client_events": [
                    "audio",
                    "interruption",
                    "user_transcript",
                    "agent_response",
                    "agent_response_correction",
                    "vad_score",
                    "agent_chat_response_part",
                ],
            },
        },
        "name": "AskProfNui — Digital Transformation",
    }

    response = requests.patch(
        f"{ELEVENLABS_API_BASE}/convai/agents/{agent_id}",
        headers={**_headers(api_key), "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"Failed to update agent ({response.status_code}): {response.text}")


def sync_course_knowledge(api_key: str, agent_id: str) -> list[str]:
    manifest = _load_manifest()
    doc_paths = sorted(DOCUMENTS_DIR.glob("*.txt"))
    if not doc_paths:
        raise RuntimeError(f"No .txt files found in {DOCUMENTS_DIR}/")

    knowledge_entries: list[dict] = []
    uploaded: list[str] = []

    for path in doc_paths:
        content_hash = _file_hash(path)
        cached = manifest["documents"].get(path.name)
        if cached and cached.get("sha256") == content_hash:
            doc_id = cached["id"]
            print(f"  reuse {path.name}")
        else:
            display_name = path.stem.replace("_", " ")
            print(f"  upload {path.name}")
            doc_id = upload_document(api_key, path, display_name)
            manifest["documents"][path.name] = {
                "id": doc_id,
                "sha256": content_hash,
                "name": display_name,
            }
            uploaded.append(path.name)

        knowledge_entries.append(
            {
                "type": "file",
                "id": doc_id,
                "name": manifest["documents"][path.name]["name"],
                "usage_mode": "auto",
            }
        )

    _save_manifest(manifest)
    print(f"\nUpdating agent with {len(knowledge_entries)} course documents…")
    update_agent(api_key, agent_id, knowledge_entries)
    return uploaded


def main() -> int:
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    agent_id = os.getenv("ELEVENLABS_AGENT_ID", "").strip()

    if not api_key or not agent_id:
        print("Set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID in .env first.")
        return 1

    print(f"Syncing course materials → ElevenLabs agent ({COURSE_KB_FOLDER_NAME})")
    try:
        uploaded = sync_course_knowledge(api_key, agent_id)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1

    if uploaded:
        print(f"Uploaded {len(uploaded)} new/changed file(s).")
    else:
        print("All documents already synced — agent knowledge base refreshed.")
    print("Done. Restart your live avatar session in the app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
