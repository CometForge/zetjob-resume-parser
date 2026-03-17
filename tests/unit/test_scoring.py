from app.v2.scoring import _tier, compute_score
from app.v2.types import (
    ATSSignal,
    CanonicalExperience,
    CanonicalResume,
    ExtractedSkill,
    ImpactSignal,
    OwnershipSignal,
    RedFlag,
    RedFlagSignal,
    ResumeMetadata,
    RoleAlignment,
    SkillSignal,
)


def _sample_canonical() -> CanonicalResume:
    return CanonicalResume(
        summary="Backend engineer",
        experience=[CanonicalExperience(company="Acme", title="Engineer", start_date="2021-01", bullets=["Built APIs"])],
        education=[],
        skills=["Python"],
        metadata=ResumeMetadata(estimated_word_count=450, bullet_count=1, bullet_ratio=0.2),
    )


def test_tier_thresholds():
    assert _tier(85) == "strong"
    assert _tier(70) == "competitive"
    assert _tier(50) == "needs-work"
    assert _tier(20) == "major-gaps"


def test_compute_score_returns_weighted_dimensions_and_confidence():
    canonical = _sample_canonical()
    signals = {
        "impact": [ImpactSignal(role_index=0, bullet_index=0, text="Increased conversion 20%", impact_type="metric", quantification="strong", star_score=0.9)],
        "ownership": [OwnershipSignal(role_index=0, company="Acme", title="Engineer", ownership_level="led", scope="team")],
        "skills": SkillSignal(hard_skills=[ExtractedSkill(name="Python", depth="expert")]),
        "ats": ATSSignal(overall_pass=True, pass_rate=0.8),
        "red_flags": RedFlagSignal(flags=[RedFlag(type="generic_language", severity="low", detail="x")]),
    }
    alignment = RoleAlignment(fit_score=72)

    score = compute_score(canonical, signals, alignment, target_role="Backend Engineer")

    assert score.overall > 0
    assert score.confidence > 60
    assert set(score.dimensions.keys()) == {
        "impact_quality",
        "ownership",
        "skills_relevance",
        "ats_compliance",
        "red_flag_penalty",
        "narrative_coherence",
    }
    total_weighted = sum(d.weighted_contribution for d in score.dimensions.values())
    assert round(total_weighted, 2) == score.overall
