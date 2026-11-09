# FairPay AI

Payroll query assessment and back-pay remediation for Kestrel Hospitality Group.

When an employee says their pay is wrong, FairPay AI ranks the open queue by the money at stake, works the pay period out again to the cent from the company's own pay schedules, has five agents write up what went wrong, and then stops. A Remediation Controller who did not open the case decides. Only after that is a letter or a pay correction statement written.

> Models and documents give the facts. Plain code does the maths. The language model writes the words. A person decides.

---

## Quick start

From the `Project` folder:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # or devkit/requirements.txt outside the capstone

python devkit/bootstrap_demo.py            # only fills gaps: never overwrites config, data, docs or .env
# put GEMINI_API_KEY and GEMINI_MODEL in .env  (or FAIRPAY_OFFLINE_LLM=1 for a no-cost rehearsal)

python run_database_setup.py               # 1. database, six tables, fifteen accounts
python run_data_pipeline.py                # 2. clean five extracts + data_quality_report.json
python run_model_training.py               # 3. three models + model_metrics.json
python run_knowledge_indexing.py           # 4. sixteen PDFs into Chroma, rates read back

python run_api_service.py                  # 5. REST service on :8081 (docs at /docs)
streamlit run run_dashboard.py             # 6. dashboard on :8080
python -m pytest tests.py                  # 7. the marking suite (start from an empty database)
```

`make build`, `make api`, `make dashboard`, `make test` do the same. `make help` lists everything.

### Accounts

| Role | Usernames | Password |
|---|---|---|
| Remediation Controller | olivia, marcus, priya | `Controller#2025` |
| Payroll Analyst | daniel, sofia, liam, aisha, tom, grace | `Analyst#2025` |
| HR Service Desk Agent | hannah, ravi, chloe, jack, mei, omar | `Desk#2025` |

These are the devkit's seeded accounts. In the capstone environment the accounts come from the pre-loaded `config.SEED_USER_ACCOUNTS`.

---

## What is in here

```
access/          sign-in hashing and the role guard every endpoint sits behind
agentic/         seven agents, ten workflow nodes, the LangGraph graph and checkpoint
api/             FastAPI schemas and routes, one failure handler
chat/            payroll assistant (one call per question), memory, status answers
dashboard/       five Streamlit pages; every figure comes from the service
data_pipeline/   loaders, shared repairs, three cleaning runs, features, quality profiler
knowledge/       PDF text, sections and passages, Chroma index, schedule reader
modeling/        correction, effort and category models, evaluation, registry
persistence/     SQLAlchemy engine, six tables, the repository
tools/           pay calculator, predictions, queue records, guide retrieval
experiments/     training-run ledger and baseline comparison (Day 2)
ops/             monitoring snapshot, alerts, CI model gate (Day 4)
tests_fairpay/   our own 23 tests: unit and end to end, on the offline model
devkit/          stand-in config, demo data and PDF generators, bootstrap
docs/            architecture, runbook, demo script, dry-run checklist, slides
```

## Design decisions worth knowing

**No rate lives in code.** Every rate window, traineeship move and commitment payment is read from its own PDF when the service starts. Rates are read by pattern from the whole schedule, never by similarity search, because the five schedules share a template and a search would happily return the wrong classification's rate.

**Money never touches a float.** Hours and amounts are `Decimal`, every step in between is a `Fraction`, and the total is rounded once at the end. Piece figures are rounded for display only and never added up. The published worked example (`PQR-SYD-0041927`) comes out to AUD 4203.47 owed against AUD 3688.40 paid: underpaid by AUD 515.07.

**Agents write, they don't calculate.** Each agent is exactly one Gemini call that receives finished figures and replies in labelled fields. The pay statement is checked after the call: every piece amount has to appear exactly once, or the run fails rather than storing a wrong statement.

**The pause survives a restart.** The workflow stops inside the gate with LangGraph's `interrupt`, checkpointed to SQLite after every node. A different controller resumes it with `Command(resume=...)`, in another request or after a reboot.

**The service decides access, not the dashboard.** The guard is a router-wide dependency, so a new endpoint can't forget it. An HR Service Desk Agent who calls `/queue` directly gets 403. In the chat they hear a query's status and when it last changed, never an amount.

## Beyond the brief

These are additions on top of the SRS. Nothing in the specified behaviour changes.

- **Offline rehearsal model** (`FAIRPAY_OFFLINE_LLM=1`). A deterministic stand-in for Gemini that only quotes facts already in the prompt. Use it for dry runs, CI and demos without a key. Leave it unset for the real system and for `tests.py`.
- **Experiment tracking.** Every training run is appended to `output/experiments/training_runs.jsonl` with data fingerprints and the git commit. `python -m experiments.compare_baselines` compares each model with simple baselines on the same held-out rows.
- **Monitoring and alerts.** `GET /audit/monitoring` and `python -m ops.monitor` report runs by status, call budgets, latency p50/p95 per agent and the chat refusal rate. They raise alerts for failed runs, runs over budget and runs stuck in `running`.
- **CI/CD.** `.github/workflows/ci.yml` runs lint, then all four build steps, then the model gate, the team tests and the monitor, then a Docker build. It uploads the quality report, metrics and test results as evidence.
- **Docker.** `docker compose up --build` runs the service and dashboard together, with the database on a volume.

## Before you submit

1. Keep the capstone's own `config/config.py`, data, documents, `.env`, `.streamlit/config.toml` and `requirements.txt`. The bootstrap never overwrites them.
2. Delete `database/fairpay.db` and `database/checkpoint.db`, then run step 1 again (`make fresh`).
3. Run `python -m pytest tests.py`. The workflow and chat checks make real Gemini calls, so the key must be set and `FAIRPAY_OFFLINE_LLM` must not be.
