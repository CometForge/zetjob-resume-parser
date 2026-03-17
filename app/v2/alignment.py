from .llm import call_gemini
from .prompts import ROLE_ALIGNMENT_PROMPT
from .types import AlignmentGap, RoleAlignment


def _heuristic_alignment(target_role: str, canonical, signals: dict) -> RoleAlignment:
    role_lower = (target_role or "").lower()
    strengths = []
    gaps = []

    impact = signals.get("impact", [])
    strong_impacts = [s for s in impact if getattr(s, "quantification", "") == "strong"]
    if strong_impacts:
        strengths.append("Quantified business impact present in experience bullets")
    else:
        gaps.append(AlignmentGap(area="impact evidence", severity="high", detail="Few measurable outcomes for target role"))

    skill_signal = signals.get("skills")
    hard = [h.name.lower() for h in getattr(skill_signal, "hard_skills", [])]
    for token in role_lower.split():
        if len(token) > 3 and token not in hard:
            gaps.append(AlignmentGap(area=f"keyword:{token}", severity="low", detail="Target-role keyword weakly represented"))

    ownership = signals.get("ownership", [])
    led_count = sum(1 for o in ownership if getattr(o, "ownership_level", "") == "led")
    if led_count:
        strengths.append("Clear ownership signals in at least one role")
    else:
        gaps.append(AlignmentGap(area="ownership", severity="medium", detail="Leadership/ownership not explicit"))

    fit = 55.0 + min(20.0, len(strong_impacts) * 3.0) + min(10.0, led_count * 3.0) - min(25.0, len(gaps) * 2.5)
    fit = max(0.0, min(100.0, fit))
    return RoleAlignment(
        fit_score=fit,
        strength_alignment=strengths[:6],
        gaps=gaps[:6],
        narrative_assessment="Overall fit based on impact evidence, ownership clarity, and role-keyword overlap.",
        market_notes="Refine role-specific keywords and quantified outcomes for stronger recruiter pass-through.",
    )


async def run_role_alignment(target_role: str, canonical, signals: dict, model: str | None = None) -> RoleAlignment:
    payload = {
        "target_role": target_role,
        "canonical": canonical.model_dump(),
        "signals": {
            "impact": [x.model_dump() for x in signals.get("impact", [])],
            "ownership": [x.model_dump() for x in signals.get("ownership", [])],
            "skills": signals.get("skills").model_dump() if signals.get("skills") else {},
            "ats": signals.get("ats").model_dump() if signals.get("ats") else {},
            "red_flags": signals.get("red_flags").model_dump() if signals.get("red_flags") else {},
        },
    }
    llm = await call_gemini(ROLE_ALIGNMENT_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, dict):
        try:
            return RoleAlignment.model_validate(llm)
        except Exception:
            pass
    return _heuristic_alignment(target_role, canonical, signals)
