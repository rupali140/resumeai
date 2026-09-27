"""
The actual "AI" in ResumeAI. Sends the parsed resume text and a job
description to Claude and asks for a strict JSON verdict: an ATS score
broken into sub-scores, matched/missing skills and keywords, and
prioritized improvement suggestions.

Swap-out point: if you want to use a different model/provider later,
only this file needs to change — everything else consumes `analyze_resume()`.
"""
import json
import re
from fastapi import HTTPException
from anthropic import Anthropic, APIError

from ..config import settings

_client = None


def get_client() -> Anthropic:
    global _client
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured on the server. Set it in your .env file.",
        )
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) analyst and technical recruiter.
You compare a candidate's resume text against a target job description and produce a
rigorous, honest evaluation. You are not a cheerleader — score based on real evidence
in the resume text, not assumptions.

Respond with ONLY a single valid JSON object. No markdown fences, no commentary,
no text before or after the JSON. The JSON must match this exact shape:

{
  "ats_score": <integer 0-100, overall score>,
  "keyword_match": <integer 0-100>,
  "skills_match": <integer 0-100>,
  "experience_relevance": <integer 0-100>,
  "education_match": <integer 0-100>,
  "formatting_score": <integer 0-100, based on structure/clarity of the raw text>,
  "matched_skills": [<strings, skills/technologies present in BOTH resume and job description>],
  "missing_skills": [
    {"name": <string>, "category": <one of "Programming","Frontend","Backend","Database","Cloud","DevOps","Tools","Soft Skills">, "priority": <"High","Medium","Low">}
  ],
  "matched_keywords": [<strings, important JD keywords/phrases found in the resume>],
  "missing_keywords": [<strings, important JD keywords/phrases NOT found in the resume>],
  "suggestions": [
    {"category": <"Critical","Important","Recommended">, "text": <one concrete, specific, actionable suggestion>}
  ]
}

Guidance:
- "missing_skills" priority should reflect how often/prominently that skill appears in the job description.
- Include 4-10 items each for matched_skills, missing_skills, matched_keywords, missing_keywords where the content supports it.
- Include 3-6 suggestions, each specific to THIS resume and THIS job description (cite concrete gaps, not generic advice).
- Scores must be integers, consistent with each other (ats_score is a weighted overall reflecting the sub-scores).
"""


def _build_user_message(resume_text: str, job_description: str, job_title: str | None) -> str:
    title_line = f"Target role: {job_title}\n\n" if job_title else ""
    return (
        f"{title_line}"
        f"=== JOB DESCRIPTION ===\n{job_description.strip()}\n\n"
        f"=== RESUME TEXT (extracted from uploaded file) ===\n{resume_text.strip()}\n\n"
        "Analyze the resume against the job description and return the JSON object as instructed."
    )


def _extract_json(raw_text: str) -> dict:
    # Claude is instructed to return raw JSON, but strip code fences defensively.
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to salvage the first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def analyze_resume(resume_text: str, job_description: str, job_title: str | None = None) -> dict:
    client = get_client()
    user_message = _build_user_message(resume_text, job_description, job_title)

    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"AI analysis service error: {exc}")

    raw_text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")

    try:
        result = _extract_json(raw_text)
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=502, detail="AI analysis returned an unreadable response. Please retry.")

    _validate_result(result)
    return result


REQUIRED_KEYS = {
    "ats_score", "keyword_match", "skills_match", "experience_relevance",
    "education_match", "formatting_score", "matched_skills", "missing_skills",
    "matched_keywords", "missing_keywords", "suggestions",
}


def _validate_result(result: dict) -> None:
    missing = REQUIRED_KEYS - result.keys()
    if missing:
        raise HTTPException(
            status_code=502,
            detail=f"AI analysis response was missing fields: {', '.join(missing)}",
        )


# ---------------------------------------------------------------------------
# Structured resume field extraction (name, education, skills, experience...)
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM_PROMPT = """You extract structured data from raw resume text.
Respond with ONLY a single valid JSON object, no markdown fences, no commentary.
Use this exact shape (use null or empty arrays for anything not present in the text):

{
  "name": <string or null>,
  "email": <string or null>,
  "phone": <string or null>,
  "location": <string or null>,
  "linkedin": <string or null>,
  "github": <string or null>,
  "portfolio": <string or null>,
  "education": [{"degree": <string>, "institution": <string>, "year": <string or null>, "score": <string or null>}],
  "skills": [<strings>],
  "experience": [{"company": <string>, "role": <string>, "duration": <string or null>, "responsibilities": [<strings>]}],
  "projects": [{"name": <string>, "technologies": [<strings>], "description": <string>}],
  "certifications": [<strings>]
}

Only extract what is actually present in the text — do not invent information."""


def extract_resume_fields(resume_text: str) -> dict:
    client = get_client()
    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            system=EXTRACT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": resume_text.strip()}],
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"AI extraction service error: {exc}")

    raw_text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return _extract_json(raw_text)


# ---------------------------------------------------------------------------
# Bullet point optimizer
# ---------------------------------------------------------------------------

BULLET_SYSTEM_PROMPT = """You are an expert resume writer. Given one resume bullet point,
rewrite it to be stronger: add measurable impact where plausible, use a strong action verb,
and align it with language recruiters and ATS systems look for. Keep it truthful — do not
invent specific numbers that weren't implied; instead phrase for impact without fabricating stats.

Respond with ONLY a single valid JSON object, no markdown fences, no commentary:
{
  "original": <the original bullet, verbatim>,
  "improved": <the rewritten bullet>,
  "explanation": <one or two sentences on why the rewrite is stronger>
}"""


def optimize_bullet(bullet_text: str) -> dict:
    client = get_client()
    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=500,
            system=BULLET_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": bullet_text.strip()}],
        )
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"AI optimization service error: {exc}")

    raw_text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    result = _extract_json(raw_text)
    for key in ("original", "improved", "explanation"):
        if key not in result:
            raise HTTPException(status_code=502, detail="AI optimization response was incomplete.")
    return result
