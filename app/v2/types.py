from pydantic import BaseModel, Field


class CanonicalExperience(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str | None = None
    is_current: bool = False
    date_ambiguous: bool = False
    location: str | None = None
    bullets: list[str] = Field(default_factory=list)


class CanonicalEducation(BaseModel):
    institution: str = ""
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None


class CanonicalProject(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class Certification(BaseModel):
    name: str = ""
    issuer: str | None = None
    date: str | None = None


class ResumeMetadata(BaseModel):
    estimated_word_count: int = 0
    section_order: list[str] = Field(default_factory=list)
    page_estimate: int = 0
    bullet_count: int = 0
    bullet_ratio: float = 0.0
    needs_ocr: bool = False


class CanonicalResume(BaseModel):
    summary: str | None = None
    experience: list[CanonicalExperience] = Field(default_factory=list)
    education: list[CanonicalEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[CanonicalProject] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    awards: list[dict] = Field(default_factory=list)
    metadata: ResumeMetadata = Field(default_factory=ResumeMetadata)


class ImpactSignal(BaseModel):
    role_index: int
    bullet_index: int
    text: str
    impact_type: str
    quantification: str
    star_score: float
    verbs: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)


class OwnershipSignal(BaseModel):
    role_index: int
    company: str
    title: str
    ownership_level: str
    scope: str
    evidence: list[str] = Field(default_factory=list)
    passive_flags: list[str] = Field(default_factory=list)


class ExtractedSkill(BaseModel):
    name: str
    depth: str
    last_used: str = ""
    context: str | None = None


class EvidencedSoftSkill(BaseModel):
    name: str
    evidence: str = ""


class SkillSignal(BaseModel):
    hard_skills: list[ExtractedSkill] = Field(default_factory=list)
    soft_skills: list[EvidencedSoftSkill] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ATSCheck(BaseModel):
    rule: str
    passed: bool
    detail: str | None = None


class ATSSignal(BaseModel):
    overall_pass: bool = True
    pass_rate: float = 0.0
    checks: list[ATSCheck] = Field(default_factory=list)


class RedFlag(BaseModel):
    type: str
    severity: str
    detail: str
    location: str = ""


class RedFlagSignal(BaseModel):
    flags: list[RedFlag] = Field(default_factory=list)


class AlignmentGap(BaseModel):
    area: str
    severity: str
    detail: str


class RoleAlignment(BaseModel):
    fit_score: float = 0.0
    strength_alignment: list[str] = Field(default_factory=list)
    gaps: list[AlignmentGap] = Field(default_factory=list)
    narrative_assessment: str = ""
    market_notes: str | None = None


class DimensionScore(BaseModel):
    score: float
    weight: float
    weighted_contribution: float = 0.0
    rationale: str = ""


class ResumeScore(BaseModel):
    overall: float = 0.0
    confidence: float = 0.0
    dimensions: dict[str, DimensionScore] = Field(default_factory=dict)
    tier: str = "needs-work"


class InterviewQuestion(BaseModel):
    question: str
    source: str
    severity: str
    likelihood: str
    coaching_note: str = ""
    suggested_framework: str = ""
    do_not: str = ""


class Recommendation(BaseModel):
    id: str = ""
    priority: int = 0
    title: str = ""
    dimension: str = ""
    effort: str = "moderate"
    estimated_score_impact: float = 0.0
    description: str = ""
    before: str | None = None
    after: str | None = None
    location: str = ""


class PipelineTelemetry(BaseModel):
    request_id: str = ""
    pipeline_version: str = "2.0"
    total_duration_ms: int = 0
    step_durations: dict[str, int] = Field(default_factory=dict)
    models_used: dict[str, str] = Field(default_factory=dict)


class ResumeDoctorResult(BaseModel):
    version: str = "2.0"
    resume_version_id: str | None = None
    user_id: str | None = None
    target_role: str
    canonical: CanonicalResume
    signals: dict
    alignment: RoleAlignment | None = None
    score: ResumeScore
    recommendations: list[Recommendation] = Field(default_factory=list)
    interview_prep: list[InterviewQuestion] = Field(default_factory=list)
    telemetry: PipelineTelemetry = Field(default_factory=PipelineTelemetry)


class V2AnalyzeRequest(BaseModel):
    file_base64: str = Field(..., alias="fileBase64")
    file_name: str | None = Field(None, alias="fileName")
    mime_type: str | None = Field(None, alias="mimeType")
    target_role: str = Field(..., alias="targetRole")
    intake_data: dict | None = Field(None, alias="intakeData")
    models: dict[str, str] | None = None
    options: dict[str, bool] | None = None

    model_config = {"populate_by_name": True}
