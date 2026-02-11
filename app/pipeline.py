from typing import Dict, Any
from .schemas import PIPELINE_STEPS, RESUME_OUTPUT_SCHEMA

async def run_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder pipeline stub."""
    # TODO: implement actual steps
    return {
        "steps": PIPELINE_STEPS,
        "schema": RESUME_OUTPUT_SCHEMA,
        "text": None,
        "scores": {
            "readability": None,
            "ats": None,
            "match": None,
        },
        "fields": {},
    }
