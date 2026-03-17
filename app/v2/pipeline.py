import asyncio
import base64
import time
from uuid import uuid4

from app.pipeline import _extract_text, _is_safe_text

from .alignment import run_role_alignment
from .canonicalizer import canonicalize
from .extractors import (
    extract_ats,
    extract_impact,
    extract_ownership,
    extract_red_flags,
    extract_skills,
    generate_interview_prep,
)
from .recommendations import generate_recommendations
from .scoring import compute_score
from .types import PipelineTelemetry, ResumeDoctorResult


async def run_v2_pipeline(payload: dict) -> dict:
    t0 = time.perf_counter()
    step_durations: dict[str, int] = {}
    models = payload.get("models") or {}

    req_id = str(uuid4())
    target_role = payload.get("target_role") or payload.get("targetRole") or "Unknown"
    intake_data = payload.get("intake_data") or payload.get("intakeData") or {}

    t = time.perf_counter()
    file_base64 = payload.get("file_base64") or payload.get("fileBase64") or ""
    file_name = payload.get("file_name") or payload.get("fileName")
    mime_type = payload.get("mime_type") or payload.get("mimeType")
    file_bytes = base64.b64decode(file_base64)
    text = _extract_text(file_bytes, mime_type, file_name)
    step_durations["ingest_extract_text"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    is_safe, reason = _is_safe_text(text)
    if not is_safe:
        raise ValueError(reason or "Unsafe resume text")
    step_durations["safety_check"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    canonical = await canonicalize(text, model=models.get("canonicalizer"))
    step_durations["canonicalize"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    impact, ownership, skills, ats, red_flags = await asyncio.gather(
        extract_impact(canonical, model=models.get("impact"), intake_data=intake_data),
        extract_ownership(canonical, model=models.get("ownership"), intake_data=intake_data),
        extract_skills(canonical, model=models.get("skills"), intake_data=intake_data),
        extract_ats(canonical, model=models.get("ats"), intake_data=intake_data),
        extract_red_flags(canonical, model=models.get("red_flags"), intake_data=intake_data),
    )
    step_durations["extractors_parallel"] = int((time.perf_counter() - t) * 1000)

    signals = {
        "impact": impact,
        "ownership": ownership,
        "skills": skills,
        "ats": ats,
        "red_flags": red_flags,
    }

    t = time.perf_counter()
    alignment = await run_role_alignment(target_role, canonical, signals, model=models.get("alignment"))
    step_durations["alignment"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    score = compute_score(canonical, signals, alignment, target_role)
    step_durations["scoring"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    recommendations = await generate_recommendations(
        target_role=target_role,
        canonical=canonical,
        signals=signals,
        alignment=alignment,
        score=score,
        model=models.get("recommendations"),
    )
    step_durations["recommendations"] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    interview_prep = await generate_interview_prep(
        canonical=canonical,
        red_flags=red_flags,
        ownership=ownership,
        alignment=alignment,
        model=models.get("interview_prep"),
        intake_data={**intake_data, "target_role": target_role},
    )
    step_durations["interview_prep"] = int((time.perf_counter() - t) * 1000)

    telemetry = PipelineTelemetry(
        request_id=req_id,
        pipeline_version="2.0",
        total_duration_ms=int((time.perf_counter() - t0) * 1000),
        step_durations=step_durations,
        models_used={
            "canonicalizer": models.get("canonicalizer", "gemini-2.5-flash"),
            "impact": models.get("impact", "gemini-2.5-flash"),
            "ownership": models.get("ownership", "gemini-2.5-flash"),
            "skills": models.get("skills", "gemini-2.5-flash"),
            "ats": models.get("ats", "gemini-2.5-flash"),
            "red_flags": models.get("red_flags", "gemini-2.5-flash"),
            "alignment": models.get("alignment", "gemini-2.5-flash"),
            "recommendations": models.get("recommendations", "gemini-2.5-flash"),
            "interview_prep": models.get("interview_prep", "gemini-2.5-flash"),
        },
    )

    result = ResumeDoctorResult(
        target_role=target_role,
        resume_version_id=payload.get("resume_version_id"),
        user_id=payload.get("user_id"),
        canonical=canonical,
        signals={
            "impact": [x.model_dump() for x in impact],
            "ownership": [x.model_dump() for x in ownership],
            "skills": skills.model_dump(),
            "ats": ats.model_dump(),
            "red_flags": red_flags.model_dump(),
        },
        alignment=alignment,
        score=score,
        recommendations=recommendations,
        interview_prep=interview_prep,
        telemetry=telemetry,
    )
    return result.model_dump()
