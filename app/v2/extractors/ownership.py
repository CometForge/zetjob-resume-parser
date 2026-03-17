from ..llm import call_gemini
from ..prompts import OWNERSHIP_DETECTOR_PROMPT
from ..types import CanonicalResume, OwnershipSignal


def _heuristic_ownership(canonical: CanonicalResume) -> list[OwnershipSignal]:
    led = {"led", "owned", "architected", "spearheaded", "built"}
    contributed = {"collaborated", "helped", "supported", "partnered"}
    participated = {"worked on", "assisted", "participated"}

    result: list[OwnershipSignal] = []
    for i, role in enumerate(canonical.experience):
        bullets = " | ".join(role.bullets).lower()
        evidence = role.bullets[:3]
        passive_flags = []

        if any(k in bullets for k in led):
            level = "led"
        elif any(k in bullets for k in contributed):
            level = "contributed"
        elif any(k in bullets for k in participated):
            level = "participated"
        else:
            level = "unclear"

        if "across" in bullets or "cross-functional" in bullets:
            scope = "cross-functional"
        elif "team" in bullets or "squad" in bullets:
            scope = "team"
        elif "org" in bullets or "company-wide" in bullets:
            scope = "org-wide"
        else:
            scope = "individual"

        for token in ["responsible for", "helped", "worked on", "assisted"]:
            if token in bullets:
                passive_flags.append(token)

        result.append(
            OwnershipSignal(
                role_index=i,
                company=role.company,
                title=role.title,
                ownership_level=level,
                scope=scope,
                evidence=evidence,
                passive_flags=passive_flags,
            )
        )

    return result


async def extract_ownership(canonical: CanonicalResume, model: str | None = None, intake_data: dict | None = None) -> list[OwnershipSignal]:
    payload = {
        "experience": [
            {"role_index": i, "company": r.company, "title": r.title, "bullets": r.bullets}
            for i, r in enumerate(canonical.experience)
        ]
    }
    llm = await call_gemini(OWNERSHIP_DETECTOR_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, list):
        try:
            return [OwnershipSignal.model_validate(x) for x in llm]
        except Exception:
            pass
    return _heuristic_ownership(canonical)
