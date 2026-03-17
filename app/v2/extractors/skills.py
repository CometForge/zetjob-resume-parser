import re

from ..llm import call_gemini
from ..prompts import SKILLS_EXTRACTOR_PROMPT
from ..types import CanonicalResume, EvidencedSoftSkill, ExtractedSkill, SkillSignal

SOFT_SKILL_HINTS = ["leadership", "communication", "stakeholder", "mentorship", "ownership", "collaboration"]


def _heuristic_skills(canonical: CanonicalResume) -> SkillSignal:
    hard: dict[str, ExtractedSkill] = {}

    for s in canonical.skills:
        key = s.strip().lower()
        if key:
            hard[key] = ExtractedSkill(name=s.strip(), depth="familiar", context="skills section")

    bullets = "\n".join(b for r in canonical.experience for b in r.bullets)
    tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{1,24}\b", bullets)
    for token in tokens:
        tl = token.lower()
        if tl in hard:
            hard[tl].depth = "proficient"
        elif token[0].isupper() and len(token) > 2:
            hard[tl] = ExtractedSkill(name=token, depth="proficient", context="experience bullets")

    soft = []
    low = bullets.lower()
    for hint in SOFT_SKILL_HINTS:
        if hint in low:
            soft.append(EvidencedSoftSkill(name=hint.title(), evidence=f"Mentioned in role bullets ({hint})"))

    return SkillSignal(
        hard_skills=list(hard.values())[:40],
        soft_skills=soft[:10],
        certifications=[c.name for c in canonical.certifications if c.name],
    )


async def extract_skills(canonical: CanonicalResume, model: str | None = None, intake_data: dict | None = None) -> SkillSignal:
    payload = {
        "skills": canonical.skills,
        "experience": [{"title": r.title, "bullets": r.bullets} for r in canonical.experience],
        "certifications": [c.model_dump() for c in canonical.certifications],
    }
    llm = await call_gemini(SKILLS_EXTRACTOR_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, dict):
        try:
            return SkillSignal.model_validate(llm)
        except Exception:
            pass
    return _heuristic_skills(canonical)
