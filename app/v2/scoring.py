from .types import DimensionScore, ResumeScore

WEIGHTS = {
    "impact_quality": 0.25,
    "ownership": 0.15,
    "skills_relevance": 0.20,
    "ats_compliance": 0.15,
    "red_flag_penalty": 0.15,
    "narrative_coherence": 0.10,
}


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def score_impact(impact: list) -> DimensionScore:
    if not impact:
        return DimensionScore(score=20, weight=WEIGHTS["impact_quality"], rationale="No impact bullets detected")
    strong = sum(1 for i in impact if getattr(i, "quantification", "") == "strong")
    weak = sum(1 for i in impact if getattr(i, "quantification", "") == "weak")
    avg_star = sum(float(getattr(i, "star_score", 0)) for i in impact) / len(impact)
    score = _clamp((strong / len(impact)) * 70 + (weak / len(impact)) * 20 + avg_star * 10)
    return DimensionScore(score=score, weight=WEIGHTS["impact_quality"], rationale="Based on quantified outcomes and STAR quality")


def score_ownership(ownership: list) -> DimensionScore:
    if not ownership:
        return DimensionScore(score=30, weight=WEIGHTS["ownership"], rationale="No role ownership signals")
    led = sum(1 for o in ownership if getattr(o, "ownership_level", "") == "led")
    contrib = sum(1 for o in ownership if getattr(o, "ownership_level", "") == "contributed")
    unclear = sum(1 for o in ownership if getattr(o, "ownership_level", "") == "unclear")
    score = _clamp((led / len(ownership)) * 90 + (contrib / len(ownership)) * 60 - (unclear / len(ownership)) * 25)
    return DimensionScore(score=score, weight=WEIGHTS["ownership"], rationale="Leadership and ownership explicitness")


def score_skills(skills_signal, target_role: str) -> DimensionScore:
    hard = getattr(skills_signal, "hard_skills", []) if skills_signal else []
    if not hard:
        return DimensionScore(score=25, weight=WEIGHTS["skills_relevance"], rationale="No hard skills extracted")
    depth_map = {"expert": 1.0, "proficient": 0.75, "familiar": 0.5}
    avg_depth = sum(depth_map.get(getattr(s, "depth", "familiar"), 0.5) for s in hard) / len(hard)

    role_tokens = [t for t in (target_role or "").lower().split() if len(t) > 2]
    names = " ".join(getattr(s, "name", "").lower() for s in hard)
    overlap = sum(1 for t in role_tokens if t in names)
    overlap_score = (overlap / max(len(role_tokens), 1)) * 30
    score = _clamp(avg_depth * 70 + overlap_score)
    return DimensionScore(score=score, weight=WEIGHTS["skills_relevance"], rationale="Skill depth and target-role keyword relevance")


def score_ats(ats_signal) -> DimensionScore:
    rate = float(getattr(ats_signal, "pass_rate", 0.0) or 0.0)
    score = _clamp(rate * 100)
    return DimensionScore(score=score, weight=WEIGHTS["ats_compliance"], rationale="ATS checks pass rate")


def score_red_flags(red_flags_signal) -> DimensionScore:
    flags = getattr(red_flags_signal, "flags", []) if red_flags_signal else []
    penalty = 0
    for f in flags:
        sev = getattr(f, "severity", "low")
        penalty += 20 if sev == "high" else 10 if sev == "medium" else 4
    score = _clamp(100 - penalty)
    return DimensionScore(score=score, weight=WEIGHTS["red_flag_penalty"], rationale="Penalty for risk signals")


def score_narrative(canonical, alignment) -> DimensionScore:
    summary_present = 1 if getattr(canonical, "summary", None) else 0
    role_count = len(getattr(canonical, "experience", []))
    fit = float(getattr(alignment, "fit_score", 50.0) or 50.0)
    score = _clamp(summary_present * 25 + min(role_count * 8, 25) + fit * 0.5)
    return DimensionScore(score=score, weight=WEIGHTS["narrative_coherence"], rationale="Summary, progression, and role alignment coherence")


def score_confidence(canonical, signals: dict) -> float:
    completeness = 0.0
    completeness += 0.2 if getattr(canonical, "experience", []) else 0.0
    completeness += 0.15 if getattr(canonical, "education", []) else 0.0
    completeness += 0.15 if getattr(canonical, "skills", []) else 0.0
    completeness += 0.2 if signals.get("impact") else 0.0
    completeness += 0.1 if signals.get("ownership") else 0.0
    completeness += 0.1 if signals.get("ats") else 0.0
    completeness += 0.1 if signals.get("red_flags") is not None else 0.0
    return round(_clamp(completeness * 100), 2)


def _tier(overall: float) -> str:
    if overall >= 80:
        return "strong"
    if overall >= 60:
        return "competitive"
    if overall >= 40:
        return "needs-work"
    return "major-gaps"


def compute_score(canonical, signals: dict, alignment, target_role: str) -> ResumeScore:
    dimensions = {
        "impact_quality": score_impact(signals.get("impact", [])),
        "ownership": score_ownership(signals.get("ownership", [])),
        "skills_relevance": score_skills(signals.get("skills"), target_role),
        "ats_compliance": score_ats(signals.get("ats")),
        "red_flag_penalty": score_red_flags(signals.get("red_flags")),
        "narrative_coherence": score_narrative(canonical, alignment),
    }

    overall = 0.0
    for dim in dimensions.values():
        dim.weighted_contribution = round(dim.score * dim.weight, 2)
        overall += dim.weighted_contribution

    confidence = score_confidence(canonical, signals)
    return ResumeScore(overall=round(_clamp(overall), 2), confidence=confidence, dimensions=dimensions, tier=_tier(overall))
