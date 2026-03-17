import re

from ..llm import call_gemini
from ..prompts import ATS_VALIDATOR_PROMPT
from ..types import ATSCheck, ATSSignal, CanonicalResume

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{8,}\d)")


def _heuristic_ats(canonical: CanonicalResume, intake_data: dict | None = None) -> ATSSignal:
    checks: list[ATSCheck] = []

    checks.append(ATSCheck(rule="core_sections", passed=bool(canonical.experience and canonical.education and canonical.skills), detail="Need experience, education, and skills"))
    checks.append(ATSCheck(rule="date_presence", passed=all(bool(r.start_date) for r in canonical.experience) if canonical.experience else False, detail="Every role should include start date"))
    checks.append(ATSCheck(rule="reasonable_length", passed=300 <= canonical.metadata.estimated_word_count <= 1200, detail=f"Word count {canonical.metadata.estimated_word_count}"))
    checks.append(ATSCheck(rule="bulleted_content", passed=canonical.metadata.bullet_ratio >= 0.15, detail=f"Bullet ratio {canonical.metadata.bullet_ratio:.2f}"))

    contact_text = ""
    if intake_data:
        contact_text = str(intake_data)
    has_email = bool(EMAIL_RE.search(contact_text))
    has_phone = bool(PHONE_RE.search(contact_text))
    checks.append(ATSCheck(rule="contact_completeness", passed=has_email or has_phone, detail="Email/phone only detectable from intake_data in v2"))

    passed = sum(1 for c in checks if c.passed)
    total = len(checks)
    rate = round(passed / total, 2) if total else 0.0
    return ATSSignal(overall_pass=rate >= 0.7, pass_rate=rate, checks=checks)


async def extract_ats(canonical: CanonicalResume, model: str | None = None, intake_data: dict | None = None) -> ATSSignal:
    payload = {
        "metadata": canonical.metadata.model_dump(),
        "section_order": canonical.metadata.section_order,
        "experience_count": len(canonical.experience),
        "education_count": len(canonical.education),
        "skills_count": len(canonical.skills),
        "intake_data": intake_data or {},
    }
    llm = await call_gemini(ATS_VALIDATOR_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, dict):
        try:
            return ATSSignal.model_validate(llm)
        except Exception:
            pass
    return _heuristic_ats(canonical, intake_data)
