from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class Telemetry(BaseModel):
    request_id: str = Field(..., description="Client or server generated request id")
    trace_id: Optional[str] = Field(None, description="Distributed tracing id")
    received_at: str = Field(..., description="ISO8601 timestamp")
    processing_ms: Optional[int] = Field(None, description="Processing time in ms")
    model_used: Optional[str] = Field(None, description="LLM model id")
    pipeline_version: str = Field("0.1.0")

class ParseRequest(BaseModel):
    file_base64: str = Field(..., alias="fileBase64", description="Base64-encoded resume file")
    file_name: Optional[str] = Field(None, alias="fileName", description="Original filename")
    mime_type: Optional[str] = Field(None, alias="mimeType", description="MIME type if known")
    target_role: Optional[str] = Field(None, alias="targetRole", description="Target role (optional)")
    models: Optional[Dict[str, str]] = Field(None, description="Model overrides")

    model_config = {
        "populate_by_name": True
    }

class ParseResponse(BaseModel):
    status: str
    text: Optional[str] = None
    scores: Optional[Dict[str, Any]] = None
    fields: Optional[Dict[str, Any]] = None
    telemetry: Optional[Telemetry] = None

class StatusResponse(BaseModel):
    id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    telemetry: Optional[Telemetry] = None

# Strict JSON schema draft for output (skeleton)
RESUME_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ParsedResume",
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate", "experience", "education", "skills", "telemetry"],
    "properties": {
        "scores": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "readability": {"type": ["number", "string"]},
                "ats": {"type": ["number", "string"]},
                "match": {"type": ["number", "string"]}
            }
        },
        "fields": {
            "type": "object",
            "additionalProperties": True
        },
        "candidate": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
                "links": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"}
                }
            }
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["company", "title"],
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "highlights": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["institution"],
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"}
                }
            }
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"}
        },
        "telemetry": {
            "type": "object",
            "additionalProperties": False,
            "required": ["request_id", "received_at", "pipeline_version"],
            "properties": {
                "request_id": {"type": "string"},
                "trace_id": {"type": "string"},
                "received_at": {"type": "string", "format": "date-time"},
                "processing_ms": {"type": "integer"},
                "model_used": {"type": "string"},
                "pipeline_version": {"type": "string"}
            }
        }
    }
}

PIPELINE_STEPS: List[str] = [
    "ingest",
    "normalize",
    "segment",
    "extract",
    "validate",
    "enrich",
    "export",
]
