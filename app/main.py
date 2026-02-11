from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import datetime, timezone

from .schemas import ParseRequest, ParseResponse, StatusResponse, Telemetry, RESUME_OUTPUT_SCHEMA
from .pipeline import run_pipeline
from .config import config

app = FastAPI(title="resume-parser", version="0.1.0")

# in-memory store (stub)
JOBS = {}

@app.post("/parse", response_model=ParseResponse)
async def parse_resume(req: ParseRequest):
    job_id = str(uuid4())
    received_at = datetime.now(timezone.utc).isoformat()
    telemetry = {
        "request_id": job_id,
        "received_at": received_at,
        "pipeline_version": "0.1.0",
        "model_used": (req.models or {}).get("parse"),
    }

    result = await run_pipeline(req.model_dump())

    return ParseResponse(
        status="parsed",
        text=result.get("text"),
        scores=result.get("scores"),
        fields=result.get("fields"),
        telemetry=Telemetry(**telemetry),
    )

@app.get("/status/{id}", response_model=StatusResponse)
async def status(id: str):
    job = JOBS.get(id)
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    telemetry = Telemetry(**job.get("telemetry"))
    return StatusResponse(id=id, status=job["status"], result=job.get("result"), telemetry=telemetry)

@app.delete("/resume/{id}")
async def delete_resume(id: str):
    if id in JOBS:
        del JOBS[id]
        return JSONResponse({"deleted": True, "id": id})
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/")
async def root():
    return {
        "service": "resume-parser",
        "env": config.env,
        "models": {
            "flash": config.gemini.model_flash,
            "pro": config.gemini.model_pro,
        },
        "stubs": {
            "ocr_provider": config.ocr.provider,
            "antivirus_provider": config.antivirus.provider,
        },
        "schema": RESUME_OUTPUT_SCHEMA,
    }
