from ..llm import call_gemini
from ..prompts import INTERVIEW_PREP_PROMPT
from ..types import InterviewQuestion, RedFlagSignal


def _fallback_questions(red_flags: RedFlagSignal, ownership: list, alignment) -> list[InterviewQuestion]:
    questions: list[InterviewQuestion] = []

    for flag in red_flags.flags[:4]:
        if flag.type == "employment_gap":
            q = "Can you walk us through the timeline and intent behind the employment gap?"
        elif flag.type == "job_hopping":
            q = "What drove your recent role transitions, and what stability are you seeking next?"
        else:
            q = f"Can you clarify this concern: {flag.detail}?"
        questions.append(
            InterviewQuestion(
                question=q,
                source=flag.type,
                severity=flag.severity,
                likelihood="high" if flag.severity in {"high", "medium"} else "medium",
                coaching_note="Be concise, honest, and outcomes-focused.",
                suggested_framework="STAR",
                do_not="Do not blame former employers.",
            )
        )

    unclear = [o for o in ownership if getattr(o, "ownership_level", "") == "unclear"]
    if unclear:
        questions.append(
            InterviewQuestion(
                question="What specific decisions did you personally own in your recent projects?",
                source="ownership",
                severity="high",
                likelihood="high",
                coaching_note="Differentiate what you led vs supported.",
                suggested_framework="CAR",
                do_not="Do not use vague wording like 'helped with everything'.",
            )
        )

    if alignment and getattr(alignment, "gaps", None):
        for gap in alignment.gaps[:2]:
            questions.append(
                InterviewQuestion(
                    question=f"How are you addressing this gap: {gap.area}?",
                    source="role_alignment",
                    severity=gap.severity,
                    likelihood="medium",
                    coaching_note="Provide active learning and practical evidence.",
                    suggested_framework="Gap-Action-Result",
                    do_not="Do not deny the gap; show plan and progress.",
                )
            )

    return questions[:8]


async def generate_interview_prep(canonical, red_flags: RedFlagSignal, ownership: list, alignment, model: str | None = None, intake_data: dict | None = None) -> list[InterviewQuestion]:
    payload = {
        "target_role": (intake_data or {}).get("target_role"),
        "red_flags": red_flags.model_dump(),
        "ownership": [o.model_dump() for o in ownership],
        "alignment": alignment.model_dump() if alignment else None,
    }
    llm = await call_gemini(INTERVIEW_PREP_PROMPT, str(payload), model=model or "gemini-2.5-flash")
    if isinstance(llm, list):
        try:
            return [InterviewQuestion.model_validate(x) for x in llm]
        except Exception:
            pass
    return _fallback_questions(red_flags, ownership, alignment)
