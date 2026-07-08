"""Student profile helpers for personalized greetings (live + text chat)."""

from __future__ import annotations


def first_name(full_name: str) -> str:
    name = full_name.strip()
    return name.split()[0] if name else ""


def intro_line(name: str, major: str, year: str) -> str:
    """One natural sentence weaving in major/year when provided."""
    major = major.strip()
    year = year.strip()
    if year and major:
        return f"I see you're a {year} studying {major} — nice."
    if major:
        return f"You're studying {major}, right? Good to know."
    if year:
        return f"You're a {year} — got it."
    if first_name(name):
        return "Good to see you."
    return ""


def session_opening(name: str, major: str, year: str) -> str:
    """Natural live-session opener for Prof Nui (voice)."""
    first = first_name(name) or "there"
    lines = [f"Hey {first}! I'm Prof Nui."]
    intro = intro_line(name, major, year)
    if intro:
        lines.append(intro)
    lines.append(
        "I'm here for our digital transformation class — what's on your mind? "
        "Could be an assignment, a framework, culture and tech — whatever you want to dig into."
    )
    lines.append("Oh, and remember — C is average. A is when I say wow.")
    return " ".join(lines)


def text_welcome(name: str = "", major: str = "", year: str = "") -> str:
    """Welcome message for the text chat tab."""
    first = first_name(name)
    if first:
        greeting = f"Hey {first}! I'm Prof Nui — good to see you."
    else:
        greeting = "Hey! I'm Prof Nui — welcome."

    intro = intro_line(name, major, year)
    body = (
        f"{greeting} {intro + ' ' if intro else ''}"
        "Ask me anything about **digital transformation** — strategy, culture, technology adoption, "
        "assignments, or the wow factor.\n\n"
        "Use **Live Avatar** to talk with your voice, or **Text Chat** to type."
    )
    return body.strip()


def elevenlabs_dynamic_variables(name: str, major: str, year: str) -> dict[str, str]:
    return {
        "student_name": first_name(name) or "there",
        "student_major": major.strip() or "",
        "student_year": year.strip() or "",
        "student_intro_line": intro_line(name, major, year),
        "session_opening": session_opening(name, major, year),
    }
