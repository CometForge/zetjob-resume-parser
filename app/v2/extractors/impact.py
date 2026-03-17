import re

from ..llm import call_gemini
from ..prompts import IMPACT_EXTRACTOR_PROMPT
from ..types import CanonicalResume, ImpactSignal

VERB_RE = re.compile(r"\b(increased|reduced|improved|built|launched|delivered|designed|optimized|led|implemented|owned|managed|created)\b", re.IGNORECASE)
NUM_RE = re.compile(r"\b\d+(?:\.\d+)?%?|\$\d+[\d,]*(?:\.\d+)?\b")


def _heuristic_impact(canonical: CanonicalResume) -> list[ImpactSignal]:
    signals: list[ImpactSignal] = []
    for ri, role in enumerate(canonical.experience):
        for bi, bullet in enumerate(role.bullets):
            b = bullet.lower()
            metrics = NUM_RE.findall(bullet)
            verbs = VERB_RE.findall(bullet)
            if metrics:
                impact_type, quant, star = "metric", "strong", 0.85
            elif any(k in b for k in ["improved", "increased", "reduced", "optimized", "launched"]):
                impact_type, quant, star = "outcome", "weak", 0.62
            elif any(k in b for k in ["responsible for", "tasked with", "worked on"]):
                impact_type, quant, star = "duty", "none", 0.28
            else:
                impact_type, quant, star = "scope", "none", 0.45
            signals.append(
                ImpactSignal(
                    role_index=ri,
                    bullet_index=bi,
                    text=bullet,
                    impact_type=impact_type,
                    quantification=quant,
                    star_score=star,
                    verbs=[v.lower() for v in verbs],
                    metrics=metrics,
                )
            )
    return signals


async def extract_impact(canonical: CanonicalResume, model: str | None = None, intake_data: dict | None = None) -> list[ImpactSignal]:
    payload = {
        "experience": [
            {"role_index": i, "company": r.company, "title": r.title, "bullets": r.bullets}
            for i, r in enumerate(canonical.experience)
        ]
    }
    llm = await call_gemini(IMPACT_EXTRACTOR_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, list):
        try:
            return [ImpactSignal.model_validate(x) for x in llm]
        except Exception:
            pass
    return _heuristic_impact(canonical)
