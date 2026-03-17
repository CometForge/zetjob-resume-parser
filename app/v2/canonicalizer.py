import math
import re

from .llm import call_gemini
from .prompts import CANONICALIZER_PROMPT
from .types import (
    CanonicalEducation,
    CanonicalExperience,
    CanonicalProject,
    CanonicalResume,
    Certification,
    ResumeMetadata,
)

HEADER_MAP = {
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "education": ["education", "academic"],
    "skills": ["skills", "technical skills", "core skills", "technologies"],
    "projects": ["projects", "personal projects"],
    "certifications": ["certifications", "licenses", "certificates"],
    "awards": ["awards", "honors", "achievements"],
    "summary": ["summary", "profile", "about"],
}

MONTHS = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}

BULLET_RE = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+(.+)$")
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:[A-Za-z]{3,9}\s+)?\d{4})\s*(?:-|–|to)\s*(?P<end>(?:[A-Za-z]{3,9}\s+)?\d{4}|present|current)",
    re.IGNORECASE,
)


def _normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value in {"present", "current"}:
        return None
    year = re.search(r"(19|20)\d{2}", value)
    if not year:
        return None
    month = "01"
    for m, n in MONTHS.items():
        if m in value:
            month = n
            break
    return f"{year.group(0)}-{month}"


def _detect_header(line: str) -> str | None:
    cleaned = re.sub(r"[^a-zA-Z ]", "", line).strip().lower()
    for section, names in HEADER_MAP.items():
        if cleaned in names:
            return section
    return None


def _segment_sections(text: str) -> tuple[dict[str, list[str]], list[str]]:
    sections: dict[str, list[str]] = {k: [] for k in HEADER_MAP}
    section_order: list[str] = []
    current = "summary"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        header = _detect_header(line)
        if header:
            current = header
            if header not in section_order:
                section_order.append(header)
            continue
        sections[current].append(line)
    return sections, section_order


def _parse_experience(lines: list[str]) -> list[CanonicalExperience]:
    roles: list[CanonicalExperience] = []
    current: CanonicalExperience | None = None

    for line in lines:
        bullet = BULLET_RE.match(line)
        if bullet and current:
            current.bullets.append(bullet.group(1).strip())
            continue

        date_match = DATE_RANGE_RE.search(line)
        if date_match:
            prefix = line[: date_match.start()].strip(" -|,")
            parts = [p.strip() for p in re.split(r"\||,", prefix) if p.strip()]
            title = parts[0] if parts else prefix
            company = parts[1] if len(parts) > 1 else (roles[-1].company if roles else "")
            start = _normalize_date(date_match.group("start")) or ""
            end_raw = date_match.group("end")
            end = _normalize_date(end_raw)
            current = CanonicalExperience(
                company=company,
                title=title,
                start_date=start,
                end_date=end,
                is_current=end_raw.lower() in {"present", "current"},
                date_ambiguous=False,
                bullets=[],
            )
            roles.append(current)
            continue

        if not current and line:
            pieces = [p.strip() for p in re.split(r"\||,", line) if p.strip()]
            if len(pieces) >= 2:
                current = CanonicalExperience(company=pieces[1], title=pieces[0], start_date="", bullets=[])
                roles.append(current)
            continue

        if current and line and len(line.split()) <= 8 and not BULLET_RE.match(line):
            if not current.location and any(k in line.lower() for k in [",", "remote", "india", "usa", "uk"]):
                current.location = line
    return roles


def _parse_education(lines: list[str]) -> list[CanonicalEducation]:
    items: list[CanonicalEducation] = []
    for line in lines:
        if len(line) < 4:
            continue
        years = re.findall(r"(?:19|20)\d{2}", line)
        parts = [p.strip() for p in re.split(r"\||,", line) if p.strip()]
        institution = parts[0] if parts else line
        degree = parts[1] if len(parts) > 1 else None
        start_date = f"{years[0]}-01" if years else None
        end_date = f"{years[-1]}-01" if len(years) > 1 else None
        items.append(
            CanonicalEducation(
                institution=institution,
                degree=degree,
                start_date=start_date,
                end_date=end_date,
            )
        )
    return items


def _parse_skills(lines: list[str]) -> list[str]:
    joined = ",".join(lines)
    raw = re.split(r"[,|/•]", joined)
    skills = []
    seen = set()
    for token in raw:
        s = token.strip()
        if not s or len(s) > 40:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            skills.append(s)
    return skills


def _parse_projects(lines: list[str]) -> list[CanonicalProject]:
    projects: list[CanonicalProject] = []
    for line in lines:
        if len(line.split()) < 2:
            continue
        bits = [b.strip() for b in line.split("-", 1)]
        name = bits[0]
        description = bits[1] if len(bits) > 1 else ""
        projects.append(CanonicalProject(name=name, description=description))
    return projects


def _parse_certifications(lines: list[str]) -> list[Certification]:
    certs: list[Certification] = []
    for line in lines:
        parts = [p.strip() for p in re.split(r"\||,", line) if p.strip()]
        if not parts:
            continue
        certs.append(Certification(name=parts[0], issuer=parts[1] if len(parts) > 1 else None))
    return certs


def _heuristic_canonicalize(text: str) -> CanonicalResume:
    sections, section_order = _segment_sections(text)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    bullet_count = sum(1 for ln in lines if BULLET_RE.match(ln))
    word_count = len(re.findall(r"\b\w+\b", text))
    bullet_ratio = round(bullet_count / max(len(lines), 1), 3)

    metadata = ResumeMetadata(
        estimated_word_count=word_count,
        section_order=section_order,
        page_estimate=max(1, math.ceil(word_count / 500)) if word_count else 0,
        bullet_count=bullet_count,
        bullet_ratio=bullet_ratio,
        needs_ocr=len(text.strip()) < 200,
    )

    summary = " ".join(sections.get("summary", [])[:3]) if sections.get("summary") else None
    return CanonicalResume(
        summary=summary,
        experience=_parse_experience(sections.get("experience", [])),
        education=_parse_education(sections.get("education", [])),
        skills=_parse_skills(sections.get("skills", [])),
        projects=_parse_projects(sections.get("projects", [])),
        certifications=_parse_certifications(sections.get("certifications", [])),
        awards=[{"text": line} for line in sections.get("awards", [])],
        metadata=metadata,
    )


def _merge_canonical(primary: CanonicalResume, fallback: CanonicalResume) -> CanonicalResume:
    merged = primary.model_copy(deep=True)
    if not merged.summary:
        merged.summary = fallback.summary
    if not merged.experience:
        merged.experience = fallback.experience
    else:
        for i, exp in enumerate(merged.experience):
            if i < len(fallback.experience):
                fb = fallback.experience[i]
                if not exp.bullets:
                    exp.bullets = fb.bullets
                if not exp.company:
                    exp.company = fb.company
                if not exp.title:
                    exp.title = fb.title
                if not exp.start_date:
                    exp.start_date = fb.start_date
    if not merged.education:
        merged.education = fallback.education
    if not merged.skills:
        merged.skills = fallback.skills
    if not merged.projects:
        merged.projects = fallback.projects
    if not merged.certifications:
        merged.certifications = fallback.certifications
    if not merged.awards:
        merged.awards = fallback.awards

    meta = merged.metadata
    fbm = fallback.metadata
    meta.estimated_word_count = meta.estimated_word_count or fbm.estimated_word_count
    meta.section_order = meta.section_order or fbm.section_order
    meta.page_estimate = meta.page_estimate or fbm.page_estimate
    meta.bullet_count = meta.bullet_count or fbm.bullet_count
    meta.bullet_ratio = meta.bullet_ratio or fbm.bullet_ratio
    meta.needs_ocr = meta.needs_ocr or fbm.needs_ocr
    merged.metadata = meta
    return merged


async def canonicalize(text: str, model: str | None = None) -> CanonicalResume:
    heuristic = _heuristic_canonicalize(text)

    llm_raw = await call_gemini(
        prompt=CANONICALIZER_PROMPT,
        text=text,
        model=model or "gemini-2.5-flash",
        temperature=0.1,
        max_tokens=16384,
    )

    llm_resume: CanonicalResume | None = None
    if isinstance(llm_raw, dict):
        try:
            llm_resume = CanonicalResume.model_validate(llm_raw)
        except Exception:
            llm_resume = None

    if not llm_resume:
        return heuristic
    return _merge_canonical(llm_resume, heuristic)
