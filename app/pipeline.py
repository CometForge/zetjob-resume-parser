from typing import Dict, Any, Optional, Tuple
import base64
import re
from io import BytesIO
from .schemas import PIPELINE_STEPS, RESUME_OUTPUT_SCHEMA

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

try:
    from docx import Document
except Exception:  # pragma: no cover
    Document = None

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{8,}\d)")
URL_RE = re.compile(r"https?://[^\s]+", re.I)

SECTION_HEADINGS = [
    "experience",
    "education",
    "skills",
    "projects",
    "summary",
    "profile",
]


def _extract_pdf_text(data: bytes) -> str:
    if not fitz:
        return ""
    text_chunks = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_chunks.append(page.get_text("text"))
    return "\n".join(text_chunks).strip()


def _extract_docx_text(data: bytes) -> str:
    if not Document:
        return ""
    doc = Document(BytesIO(data))
    return "\n".join([p.text for p in doc.paragraphs]).strip()


def _extract_text(file_bytes: bytes, mime_type: Optional[str], file_name: Optional[str]) -> str:
    lower_name = (file_name or "").lower()
    if (mime_type and "pdf" in mime_type) or lower_name.endswith(".pdf"):
        return _extract_pdf_text(file_bytes)
    if (mime_type and "word" in mime_type) or lower_name.endswith(".docx"):
        return _extract_docx_text(file_bytes)
    if lower_name.endswith(".doc"):
        # legacy doc not supported yet
        return ""
    # default: try pdf
    return _extract_pdf_text(file_bytes)


def _count_headings(text: str) -> int:
    lower = text.lower()
    return sum(1 for h in SECTION_HEADINGS if h in lower)


def _score_readability(text: str) -> int:
    if not text:
        return 0
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines = [l for l in lines if l.startswith("-") or l.startswith("•") or l.startswith("*")]
    bullet_ratio = len(bullet_lines) / max(len(lines), 1)
    length_score = 40 if len(text) > 1500 else 20 if len(text) > 700 else 10
    bullet_score = 40 if bullet_ratio >= 0.3 else 20 if bullet_ratio >= 0.15 else 10
    return min(100, length_score + bullet_score)


def _score_ats(text: str) -> int:
    if not text:
        return 0
    headings = _count_headings(text)
    heading_score = 40 if headings >= 3 else 20 if headings >= 2 else 10
    length_score = 30 if len(text) > 1500 else 15
    return min(100, heading_score + length_score + 20)


def _score_match(text: str, target_role: Optional[str]) -> int:
    if not text or not target_role:
        return 0
    lower = text.lower()
    role = target_role.lower()
    hits = sum(1 for token in role.split() if token in lower)
    return min(100, hits * 20)


def _confidence(value: Optional[str]) -> float:
    if not value:
        return 0.0
    if len(value) > 3:
        return 0.8
    return 0.5


def _guess_role(lines):
    for line in lines[:6]:
        lower = line.lower()
        if any(keyword in lower for keyword in ["engineer", "developer", "designer", "product", "data", "analyst", "manager"]):
            return line
    return None


def _bucket_experience(years: int) -> str:
    if years <= 1:
        return "0-1"
    if years <= 3:
        return "1-3"
    if years <= 5:
        return "3-5"
    if years <= 10:
        return "5-10"
    return "10+"


def _extract_fields(text: str) -> Dict[str, Any]:
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    links = URL_RE.findall(text)
    location = None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        location = lines[0] if len(lines[0].split()) <= 6 else None

    fields: Dict[str, Any] = {}

    if emails:
        fields["email"] = {"value": emails[0], "confidence": 0.9}
    if phones:
        fields["phone"] = {"value": phones[0], "confidence": 0.7}
    if links:
        fields["links"] = {"value": links[:5], "confidence": 0.6}

    linkedin = next((url for url in links if "linkedin.com" in url), None)
    github = next((url for url in links if "github.com" in url), None)
    if linkedin:
        fields["linkedinUrl"] = {"value": linkedin, "confidence": 0.8}
    if github:
        fields["githubUrl"] = {"value": github, "confidence": 0.8}

    if location:
        fields["location"] = {"value": location, "confidence": _confidence(location)}

    role = _guess_role(lines)
    if role:
        fields["role"] = {"value": role, "confidence": 0.6}

    years_match = re.search(r"(\d{1,2})\s*\+?\s*years", text, re.I)
    if years_match:
        years = int(years_match.group(1))
        fields["experience"] = {"value": _bucket_experience(years), "confidence": 0.6}

    return fields


async def run_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Basic extraction + scoring pipeline."""
    file_base64 = payload.get("file_base64") or payload.get("fileBase64")
    file_name = payload.get("file_name") or payload.get("fileName")
    mime_type = payload.get("mime_type") or payload.get("mimeType")
    target_role = payload.get("target_role") or payload.get("targetRole")

    file_bytes = base64.b64decode(file_base64)
    text = _extract_text(file_bytes, mime_type, file_name)

    fields = _extract_fields(text)

    scores = {
        "readability": _score_readability(text),
        "ats": _score_ats(text),
        "match": _score_match(text, target_role),
    }

    if not text or len(text) < 200:
        fields["needsOcr"] = {"value": True, "confidence": 0.9, "ocr_status": "pending"}
    else:
        fields["needsOcr"] = {"value": False, "confidence": 0.9, "ocr_status": "not_required"}

    fields["antivirus"] = {"value": "pending", "confidence": 0.5, "scan_status": "not_implemented", "note": "stub"}

    return {
        "steps": PIPELINE_STEPS,
        "schema": RESUME_OUTPUT_SCHEMA,
        "text": text or None,
        "scores": scores,
        "fields": fields,
    }