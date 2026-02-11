# resume-parser

Minimal FastAPI service skeleton for resume parsing pipeline.

## Endpoints
- `POST /parse` — enqueue parse job (async stub)
- `GET /status/{id}` — get job status
- `DELETE /resume/{id}` — delete resume/job data (stub)

## OCR & Antivirus (stubs)
- OCR provider: configured via `OCR_PROVIDER` (default: `stub`).
- Antivirus provider: configured via `AV_PROVIDER` (default: `stub`).
- Pipeline returns `needsOcr` / `ocr_status` and `antivirus` placeholders.

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
