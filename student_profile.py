"""Student profile helpers for personalized greetings (live + text chat)."""

from __future__ import annotations


def first_name(full_name: str) -> str:
    name = full_name.strip()
    return name.split()[0] if name else ""


def session_opening(name: str, major: str, year: str) -> str:
    """Warm live-session opener — AskProfNui voice intro."""
    first = first_name(name)
    major = major.strip()
    year = year.strip()

    if first and year and major:
        return (
            f"Hi {first}, how are you? I'm AskProfNui. "
            f"I see you're a {year} studying {major} — nice to meet you. "
            f"What can I help you with today for digital transformation?"
        )
    if first and major:
        return (
            f"Hi {first}, how are you? I'm AskProfNui. "
            f"You're in {major}, right? What can I help you with today?"
        )
    if first:
        return (
            f"Hi {first}, how are you? I'm AskProfNui. "
            f"What can I help you with today — anything on digital transformation?"
        )
    return (
        "Hi, how are you? I'm AskProfNui. "
        "What can I help you with today for digital transformation?"
    )


def text_welcome(name: str = "", major: str = "", year: str = "") -> str:
    """Welcome message for the text chat tab."""
    return session_opening(name, major, year) + (
        "\n\nUse **Live Avatar** to talk with voice, or type here."
    )


def elevenlabs_dynamic_variables(name: str, major: str, year: str) -> dict[str, str]:
    return {
        "student_name": first_name(name) or "there",
        "student_major": major.strip() or "your major",
        "student_year": year.strip() or "your year",
        "session_opening": session_opening(name, major, year),
    }
