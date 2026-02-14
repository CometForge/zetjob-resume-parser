import json
import os
from typing import Any, Dict, Optional
import httpx

from .config import config

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """You are a resume parser. Extract structured fields and return ONLY valid JSON matching this schema:
{
  "fields": {
    "name": {"value": "", "confidence": 0.0},
    "email": {"value": "", "confidence": 0.0},
    "phone": {"value": "", "confidence": 0.0},
    "location": {"value": "", "confidence": 0.0},
    "linkedinUrl": {"value": "", "confidence": 0.0},
    "githubUrl": {"value": "", "confidence": 0.0},
    "role": {"value": "", "confidence": 0.0},
    "functionArea": {"value": "", "confidence": 0.0},
    "experience": {"value": "", "confidence": 0.0}
  }
}
Use empty strings for unknown values and low confidence (0.1-0.4). Confidence is 0-1.
"""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # try to find first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def extract_fields_llm(text: str, model_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
    api_key = os.getenv(config.gemini.api_key_env)
    if not api_key:
        return None

    model = model_override or config.gemini.model_flash
    url = GEMINI_URL.format(model=model)

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": "Resume text:\n" + text[:12000]},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, params={"key": api_key}, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    try:
        candidate = data.get("candidates", [])[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_out = "".join(part.get("text", "") for part in parts)
    except Exception:
        return None

    parsed = _extract_json(text_out)
    if not parsed:
        return None

    fields = parsed.get("fields") if isinstance(parsed, dict) else None
    if not isinstance(fields, dict):
        return None

    return fields
