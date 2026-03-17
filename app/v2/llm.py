import json
import os
import re

import httpx


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _repair_truncated_json(text: str) -> str:
    """Attempt to repair truncated JSON by finding last valid structure point and closing."""
    # Strategy: walk backwards from end, find last complete value, close all brackets
    # First try to find the last complete JSON object/array boundary
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape = False
    last_good = 0
    
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace -= 1
            last_good = i + 1
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket -= 1
            last_good = i + 1
        elif ch == ',' and depth_brace >= 0 and depth_bracket >= 0:
            last_good = i
    
    if last_good > 0:
        repaired = text[:last_good].rstrip().rstrip(',')
    else:
        repaired = text.rstrip().rstrip(',')
    
    # Recount open brackets/braces
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape = False
    for ch in repaired:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{': depth_brace += 1
        elif ch == '}': depth_brace -= 1
        elif ch == '[': depth_bracket += 1
        elif ch == ']': depth_bracket -= 1
    
    repaired += ']' * max(0, depth_bracket)
    repaired += '}' * max(0, depth_brace)
    return repaired


def _extract_json_blob(text: str) -> dict | list | None:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    first_obj = cleaned.find("{")
    last_obj = cleaned.rfind("}")
    if first_obj != -1 and last_obj > first_obj:
        try:
            return json.loads(cleaned[first_obj : last_obj + 1])
        except Exception:
            pass

    first_arr = cleaned.find("[")
    last_arr = cleaned.rfind("]")
    if first_arr != -1 and last_arr > first_arr:
        try:
            return json.loads(cleaned[first_arr : last_arr + 1])
        except Exception:
            pass

    # Try repairing truncated JSON
    start = cleaned.find("{") if cleaned.find("{") != -1 else cleaned.find("[")
    if start != -1:
        try:
            repaired = _repair_truncated_json(cleaned[start:])
            return json.loads(repaired)
        except Exception:
            pass

    return None


async def call_gemini(
    prompt: str,
    text: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
    max_tokens: int = 8192,
) -> dict | list | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"text": f"INPUT:\n{text[:50000]}"},
                ],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                GEMINI_URL.format(model=model), params={"key": api_key}, json=payload
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return None

    try:
        parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
        text_out = "".join(part.get("text", "") for part in parts)
    except Exception:
        return None

    if not text_out:
        return None
    return _extract_json_blob(text_out)
