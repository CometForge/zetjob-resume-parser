from app.v2.extractors.impact import _heuristic_impact
from app.v2.extractors.ownership import _heuristic_ownership
from app.v2.extractors.red_flags import _heuristic_red_flags
from app.v2.extractors.skills import _heuristic_skills
from app.v2.types import CanonicalExperience, CanonicalResume, ResumeMetadata


def _canonical_for_extractors() -> CanonicalResume:
    return CanonicalResume(
        summary="Engineer",
        experience=[
            CanonicalExperience(
                company="Acme",
                title="Engineer",
                start_date="2019-01",
                end_date="2020-01",
                bullets=[
                    "Led migration that reduced infra cost by 25%",
                    "Responsible for various backend tasks",
                    "Collaborated with cross-functional team and showed ownership",
                ],
            ),
            CanonicalExperience(
                company="Beta",
                title="Engineer",
                start_date="2021-08",
                end_date="2022-01",
                bullets=["Worked on legacy jQuery admin dashboard"],
            ),
        ],
        skills=["Python", "FastAPI"],
        metadata=ResumeMetadata(estimated_word_count=500, bullet_count=4, bullet_ratio=0.4),
    )


def test_skills_extractor_heuristic_builds_hard_and_soft_skills():
    signal = _heuristic_skills(_canonical_for_extractors())
    hard_names = {s.name.lower() for s in signal.hard_skills}
    assert "python" in hard_names
    assert any(s.name.lower() in {"collaboration", "ownership", "leadership"} for s in signal.soft_skills)


def test_impact_extractor_heuristic_detects_metric_and_duty_bullets():
    impacts = _heuristic_impact(_canonical_for_extractors())
    assert any(i.quantification == "strong" for i in impacts)
    assert any(i.impact_type == "duty" for i in impacts)


def test_ownership_extractor_heuristic_detects_led_scope_and_passive_flags():
    ownership = _heuristic_ownership(_canonical_for_extractors())
    assert ownership[0].ownership_level == "led"
    assert ownership[0].scope == "cross-functional"
    assert "responsible for" in ownership[0].passive_flags


def test_red_flags_extractor_heuristic_detects_gap_generic_and_stale_tech():
    red_flags = _heuristic_red_flags(_canonical_for_extractors())
    types = {f.type for f in red_flags.flags}
    assert "employment_gap" in types
    assert "generic_language" in types
    assert "stale_tech" in types
