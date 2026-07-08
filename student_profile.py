"""Student profile helpers for personalized greetings (live + text chat)."""

from __future__ import annotations


def first_name(full_name: str) -> str:
    name = full_name.strip()
    return name.split()[0] if name else ""


def session_opening(name: str, major: str, year: str) -> str:
    """Short natural live-session opener for Prof Nui (voice)."""
    first = first_name(name)
    major = major.strip()
    year = year.strip()

    if first and year and major:
        return (
            f"Hey {first}! I'm Prof Nui. You're a {year} in {major}, right? "
            f"Good to see you. What's on your mind for digital transformation today?"
        )
    if first and major:
        return (
            f"Hey {first}! I'm Prof Nui — {major}, nice. "
            f"What do you want to dig into — assignment, framework, something else?"
        )
    if first:
        return (
            f"Hey {first}! I'm Prof Nui. Good to see you. "
            f"What's up — assignment, frameworks, or anything on digital transformation?"
        )
    return (
        "Hey! I'm Prof Nui. Good to see you. "
        "What's on your mind for digital transformation?"
    )


def text_welcome(name: str = "", major: str = "", year: str = "") -> str:
    """Welcome message for the text chat tab."""
    return session_opening(name, major, year) + (
        "\n\nUse **Live Avatar** to talk, or type here."
    )


def elevenlabs_dynamic_variables(name: str, major: str, year: str) -> dict[str, str]:
    return {
        "student_name": first_name(name) or "there",
        "student_major": major.strip() or "your major",
        "student_year": year.strip() or "your year",
        "session_opening": session_opening(name, major, year),
    }
