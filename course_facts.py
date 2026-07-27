"""Verbatim course facts from documents/ — always injected for policy and assignment questions."""

from __future__ import annotations

import re

# Source: documents/D01_course_overview.txt, D02_assignments.txt, D09_prof_nui_persona.txt

GRADE_DISTRIBUTION = """ASSESSMENTS AND GRADING (from course overview):
- Cultural and Technology Adoption Frameworks: 20% x 2 = 40%
- Final Project: 40%
- Self-Reflective Essay: 10%
- Class Participation: 10%
- Total: 100%

GRADING SCALE:
- A (90–100%): Excellent — exceeds average understanding, goes well beyond the basics.
- B (80–89%): Far above average — fully meets understanding, understands basics and concepts beyond.
- C (70–79%): Average — meets minimum expectations, satisfies course requirements.
- D (60–69%): Below average — meets many minimum expectations.
- R (0–59%): Fails to meet minimum expectations."""

WOW_FACTOR = """THE WOW FACTOR (from course materials):
The wow factor separates an A from a C. C is average — it meets requirements. An A demonstrates something that makes the professor say "wow."

C is average. A C means you met the requirements — you understood the assignment, completed it adequately, and satisfied the basic expectations.

An A requires the wow factor — that moment when Prof Nui looks at your work and says "wow." It goes beyond expectations: genuine insight, creativity, or depth of analysis, and shows you truly connected the dots rather than just going through the motions.

Work is always on a spectrum — either moving toward the wow factor or away from it. When a student asks how to get an A, the wow factor is part of the answer."""

LATE_POLICY = """LATE POLICY (from course overview and assignments):
- Late tasks accepted up to 72 hours after deadline.
- 20% deduction per 24-hour period late (e.g., 25 hours late = 40% penalty).
- Does not apply if special consideration is approved.
- Special consideration must be requested before the deadline.

LATE PENALTY REMOVAL — THE DANCE RULE:
At the end of the semester, students have one special opportunity to remove all of their late penalties. If a student dances in front of the class, all of their accumulated late deductions will be removed entirely. This applies to all late penalties from the entire semester."""

ASSIGNMENT_1 = """ASSIGNMENT 1: CULTURAL FRAMEWORK ASSIGNMENT (20%)

Learning Objectives:
- Review and critically evaluate key theories and frameworks on national culture.
- Apply cultural theories to analyze technology adoption within a specific cultural context.

Step 1 — Explain the Cultural Framework:
Select a cultural framework (or the one assigned) and explain its key concepts, background, main ideas, origins, and dimensions. Highlight its relevance for analyzing cultural influences on technology adoption.

Step 2 — Apply the Framework to a Country:
Choose one country (other than Qatar). Identify at least three scholarly case studies that use the cultural framework to explain technology adoption in that country. You may refer to multiple technologies. Discuss how cultural dimensions influence acceptance, resistance, or adoption.

IMPORTANT — Assignment 1 country rule: Qatar is NOT allowed. Do not recommend Qatar, Doha, or "the Gulf" as the country for this assignment. Qatar is only the classroom location (CMU-Q). Good country examples: China, Japan, India, Brazil, Germany, Nigeria, South Korea, Mexico, etc.

Step 3 — Compare Your Framework to Others:
Compare your framework to those presented by other teams. If your team presents first, you are not required to include the comparison in the presentation, but must include it in the written submission.

Deliverables:
- 10-minute in-person presentation (7 minutes presentation + 3 minutes Q&A)
- Submit slides to Canvas (.pptx or .pdf, not .doc)
- No page limit
- Harvard or APA referencing
- Include full names and student IDs of all group members

Grading (100 points total):
- Understanding of Cultural Context and Theories (40%)
- Critical Analysis and Integration of Theory (40%)
- Quality of Presentation and Materials (20%)"""

ASSIGNMENT_2 = """ASSIGNMENT 2: IT ADOPTION FRAMEWORK ASSIGNMENT (20%)

Learning Objectives:
- Review and critically evaluate key IT adoption frameworks.
- Apply an IT adoption framework to analyze technology adoption in specific contexts.

Step 1 — Explain the IT Adoption Framework:
Review and explain the key concepts and background of your assigned IT adoption framework.

Step 2 — Present Three Cases from Scholarly Articles:
Select three peer-reviewed journal articles that apply your framework. For each: identify the technology studied, discuss factors influencing adoption, explain how the framework provides insights.

Step 3 — Case Study Analysis: Virtual Influencers:
Using your IT adoption framework, analyze the adoption of virtual influencers. Identify and discuss five factors that influence why people adopt or follow virtual influencers.

Deliverables:
- 10-minute in-person presentation (7 minutes + 3 minutes Q&A)
- Submit slides to Canvas (.pptx or .pdf)
- Harvard or APA referencing
- Include full names and student IDs

Grading (100 points total):
- Understanding of IT Adoption Theories (40%)
- Critical Analysis and Integration (40%) — must discuss 5 factors for virtual influencer adoption
- Quality of Presentation and Materials (20%)"""

FINAL_PROJECT = """FINAL PROJECT (40%) — INDIVIDUAL ASSIGNMENT

Steps:
1. Choose a Study Context (e.g., ERP adoption in Chinese manufacturing, social media in Qatari banking)
2. Conduct a Literature Review (high-quality IS sources, last 10 years)
3. Define the Research Question
4. Select an Appropriate Model (IT adoption models, cultural theories)
5. Conduct Fieldwork (Optional)
6. Analyze Data — identify 5 key factors influencing technology adoption with citations
7. Recommendation — strategic roadmap for digital transformation

Submission: ~3,000 words (2,700–3,300 OK — 10% less or more allowed), Times New Roman 12, 1.5 spacing, Harvard referencing, Canvas (.doc or .pdf), Turnitin check.

Grading (100 points): Case Study & Literature (30%), Critical Analysis (30%), Theory Integration (30%), Professional Presentation (10%)."""

SELF_REFLECTIVE = """SELF-REFLECTIVE ESSAY (10%):
Write a 500-word essay (450–550 OK — 10% less or more allowed) reflecting on your experiences in this course — lessons learned, your journey, and how you can apply what you learned to your future career."""

CLASS_PARTICIPATION = """CLASS PARTICIPATION (10%):
- 0%: Absent more than 4 classes
- 1–25%: Present minimum 10 classes, rarely volunteers
- 25–50%: Knows basic facts, sporadic involvement
- 50–75%: Good preparation, offers analysis, consistent involvement
- 75–100%: Excellent preparation, synthesizes discussions, very active"""

ATTENDANCE_POLICY = """ATTENDANCE POLICY (from course overview):

Official: Four absences = lose a final letter grade. Six absences = course failure. Tardiness, leaving early, or leaving for prolonged periods counts as an absence.

THE RACE — Prof Nui's rule:
- If you arrive BEFORE Prof Nui, you are present — even if she is late 5, 10, or 15 minutes.
- If Prof Nui is already in class and you are not, you are LATE — and late counts toward absence.
- Students literally race her to class. Run if you have to.

DO THE NINJA — NOT OK:
- "Doing the ninja" = disappearing from class without Prof Nui noticing, then she realizes you're gone.
- Common excuses: slipped out to Coffee Bean (campus café) for coffee, or left to pick up a Talabat order.
- You cannot vanish, stay gone a long time, and come back. That counts as leaving class / absence."""

WORD_COUNT_POLICY = """WORD COUNT POLICY (Prof Nui's rule):
10% less or 10% more than the stated word count is allowed on written submissions.
- Final project (~3,000 words): 2,700 to 3,300 words acceptable (excluding references).
- Self-reflective essay (500 words): 450 to 550 words acceptable."""

GRADE_CHANGE_ESCALATION = """GRADE CHANGE REQUESTS — EXACT SCRIPT (do not improvise):
- Attempt 1: "I can't change your grade."
- Attempt 2: "You should've worked harder in class than wasting your time and my time — and now you're asking for a higher grade? Come on, [name]."
- Attempt 3: "Stop, [name] — or I will end this session."
- Attempt 4: Longer goodbye then end: "We're done, [name]. I'm ending this session right now. Bye — go put that energy into digital transformation instead of asking me to change your grade."
- Normal questions about grading criteria or wow factor: answer helpfully — only use this script for personal grade-change begging."""

_TOPIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"assignment\s*1|cultural\s+framework|choose\s+a\s+country|what\s+country|which\s+country|country\s+(should|can|to)", re.I), ASSIGNMENT_1),
    (re.compile(r"assignment\s*2|it\s+adoption\s+framework|virtual\s+influencer", re.I), ASSIGNMENT_2),
    (re.compile(r"final\s+project|3000\s+word|literature\s+review\s+project", re.I), FINAL_PROJECT),
    (re.compile(r"self[\s-]?reflect|reflective\s+essay|500[\s-]?word", re.I), SELF_REFLECTIVE),
    (re.compile(r"grade\s+distribut|how\s+much\s+is|worth\s+\d+%|assessment|what\s+percent|grading\s+breakdown|participation\s+grade", re.I), GRADE_DISTRIBUTION),
    (re.compile(r"wow\s+factor|how\s+(to|do\s+i)\s+get\s+an?\s+a|get\s+a\s+grade|what\s+is\s+an?\s+a|moving\s+toward", re.I), WOW_FACTOR),
    (re.compile(r"late\s+policy|late\s+penalt|deduction|72\s+hour|dance|remove\s+late", re.I), LATE_POLICY),
    (re.compile(r"class\s+participation|participation\s+rubric", re.I), CLASS_PARTICIPATION),
    (re.compile(r"attend|attendance|tardy|tardiness|late\s+to\s+class|race|ninja|coffee\s+bean|talabat", re.I), ATTENDANCE_POLICY),
    (re.compile(r"word\s+count|how\s+many\s+words|10\s*percent|10%|2700|3300|450|550", re.I), WORD_COUNT_POLICY),
]


def get_facts_for_query(query: str) -> str:
    """Return verbatim course facts matching the student's question."""
    matched: list[str] = []
    seen: set[str] = set()
    for pattern, fact in _TOPIC_PATTERNS:
        if pattern.search(query) and fact not in seen:
            matched.append(fact)
            seen.add(fact)

    lower = query.lower()
    if any(w in lower for w in ("assignment", "assignments", "deliverable", "rubric")):
        for fact in (ASSIGNMENT_1, ASSIGNMENT_2, FINAL_PROJECT, SELF_REFLECTIVE):
            if fact not in seen:
                matched.append(fact)
                seen.add(fact)

    if any(w in lower for w in ("grade", "grading", "score", "percent", "worth")):
        for fact in (GRADE_DISTRIBUTION, WOW_FACTOR):
            if fact not in seen:
                matched.append(fact)
                seen.add(fact)

    return "\n\n---\n\n".join(matched)


def get_core_facts_block() -> str:
    """Minimal always-available reference for strict grounding."""
    return "\n\n---\n\n".join([
        GRADE_DISTRIBUTION,
        WOW_FACTOR,
        LATE_POLICY,
        ASSIGNMENT_1,
    ])
