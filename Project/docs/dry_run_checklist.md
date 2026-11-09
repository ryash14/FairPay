# Dry-run checklist (Day 5)

- [ ] Fresh clone into an empty folder; capstone config, data, docs and `.env` copied in
- [ ] `pip install -r requirements.txt` with no errors
- [ ] Steps 1 to 4 run with output matching the SRS shape
- [ ] `python -m ops.model_gate` passes
- [ ] `make fresh`, then `python -m pytest tests.py` passes all 50 checks (real Gemini)
- [ ] `python -m pytest tests_fairpay` passes
- [ ] Demo script timed twice, under 8 minutes each
- [ ] Backup screen recording saved locally
- [ ] Offline fallback (`FAIRPAY_OFFLINE_LLM=1`) tested
- [ ] Slides final; every figure on them matches this run's `model_metrics.json`
- [ ] Each team member can answer: why no float, why no similarity search for rates, why the gate, why 403 rather than hiding the page
