from .llm import call_gemini
from .prompts import RECOMMENDATION_PROMPT
from .types import Recommendation


def _fallback_recommendations(score, signals: dict) -> list[Recommendation]:
    recs: list[Recommendation] = []

    impact = signals.get("impact", [])
    if sum(1 for s in impact if getattr(s, "quantification", "") == "strong") < 3:
        recs.append(
            Recommendation(
                id="rec-impact-1",
                priority=1,
                title="Rewrite top bullets with measurable outcomes",
                dimension="impact_quality",
                effort="moderate",
                estimated_score_impact=10,
                description="Add metric + context + result to at least 5 bullets.",
                before="Responsible for API development",
                after="Built 6 partner APIs, reducing onboarding time by 32%.",
                location="experience",
            )
        )

    ownership = signals.get("ownership", [])
    if not any(getattr(o, "ownership_level", "") == "led" for o in ownership):
        recs.append(
            Recommendation(
                id="rec-ownership-1",
                priority=len(recs) + 1,
                title="Make ownership explicit in each role",
                dimension="ownership",
                effort="low",
                estimated_score_impact=7,
                description="Replace passive verbs with decision-level ownership statements.",
                location="experience",
            )
        )

    ats = signals.get("ats")
    if ats and getattr(ats, "pass_rate", 1.0) < 0.8:
        recs.append(
            Recommendation(
                id="rec-ats-1",
                priority=len(recs) + 1,
                title="Improve ATS structure",
                dimension="ats_compliance",
                effort="low",
                estimated_score_impact=6,
                description="Ensure standard headers, consistent dates, and contact metadata.",
                location="resume_header",
            )
        )

    if getattr(score, "overall", 100) < 60:
        recs.append(
            Recommendation(
                id="rec-narrative-1",
                priority=len(recs) + 1,
                title="Strengthen resume narrative",
                dimension="narrative_coherence",
                effort="moderate",
                estimated_score_impact=5,
                description="Align summary and experience bullets with target role outcomes.",
                location="summary",
            )
        )

    for i, rec in enumerate(recs, start=1):
        rec.priority = i
    return recs[:5]


async def generate_recommendations(target_role: str, canonical, signals: dict, alignment, score, model: str | None = None) -> list[Recommendation]:
    payload = {
        "target_role": target_role,
        "score": score.model_dump(),
        "alignment": alignment.model_dump() if alignment else None,
        "signals": {
            "impact": [x.model_dump() for x in signals.get("impact", [])],
            "ownership": [x.model_dump() for x in signals.get("ownership", [])],
            "ats": signals.get("ats").model_dump() if signals.get("ats") else {},
            "red_flags": signals.get("red_flags").model_dump() if signals.get("red_flags") else {},
        },
    }
    llm = await call_gemini(RECOMMENDATION_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, list):
        try:
            recs = [Recommendation.model_validate(x) for x in llm][:5]
            for i, rec in enumerate(recs, start=1):
                rec.priority = i
            return recs
        except Exception:
            pass
    return _fallback_recommendations(score, signals)
