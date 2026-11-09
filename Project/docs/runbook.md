# Runbook

## First run on a new machine
1. `python3.11 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt` (or `devkit/requirements.txt`)
3. `python devkit/bootstrap_demo.py`: adds config, demo data, PDFs and `.env` only where they are missing
4. Put `GEMINI_API_KEY` and `GEMINI_MODEL` in `.env`
5. `make build`, then `make api` in one terminal and `make dashboard` in another

## When something breaks

| Symptom | Cause | Fix |
|---|---|---|
| `The service cannot start. ... is missing` | A build step was skipped | Run the step it names |
| Dashboard says the API is not answering | Service not started, or a different port | `python run_api_service.py`, then reload |
| 502 `... must both be set in .env` | No Gemini key | Fill `.env`, or set `FAIRPAY_OFFLINE_LLM=1` for a rehearsal |
| 502 `replied without ...` | The model ignored the layout | Retry; the run is marked failed, nothing was stored |
| 403 on a decision | The decider opened the assessment | Sign in as a different controller |
| 409 on a decision | Already decided, or another decision is in progress | Refresh the decision queue |
| First indexing run is slow | Downloading the embedding model | Only happens once; it is cached afterwards |

## Health checks
- `GET /health` (no sign-in)
- `python -m ops.monitor`: exits 1 when a high-severity alert is open
- `python -m ops.model_gate`: exits 1 when a model is under its minimum

## Before marking
`make fresh` (empty the database), unset `FAIRPAY_OFFLINE_LLM`, then `python -m pytest tests.py`.
