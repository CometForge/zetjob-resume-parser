from app.v2.recommendations import _fallback_recommendations
from app.v2.types import ATSSignal, ImpactSignal, OwnershipSignal, ResumeScore


def test_fallback_recommendations_prioritize_gaps():
    score = ResumeScore(overall=52)
    signals = {
        "impact": [ImpactSignal(role_index=0, bullet_index=0, text="Worked on APIs", impact_type="duty", quantification="none", star_score=0.2)],
        "ownership": [OwnershipSignal(role_index=0, company="Acme", title="Engineer", ownership_level="contributed", scope="team")],
        "ats": ATSSignal(overall_pass=False, pass_rate=0.4),
    }

    recs = _fallback_recommendations(score, signals)

    assert recs
    assert recs[0].id == "rec-impact-1"
    assert any(r.dimension == "ownership" for r in recs)
    assert any(r.dimension == "ats_compliance" for r in recs)
    assert any(r.dimension == "narrative_coherence" for r in recs)
    assert [r.priority for r in recs] == list(range(1, len(recs) + 1))
