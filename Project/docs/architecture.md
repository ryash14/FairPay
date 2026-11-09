# Architecture

See `flowchart.png` for the picture and `project_notes.html` for the plain-language version.

## Layers

| Layer | Folder | Rule it keeps |
|---|---|---|
| Data preparation | `data_pipeline/` | Nothing is guessed; an unreadable value stops the run. Every repair is counted in the quality report. |
| Models | `modeling/` | Preparation is saved inside each pipeline, so a live row is prepared exactly like training rows. |
| Knowledge | `knowledge/` | Rates are read by pattern from the whole schedule, never by similarity search. |
| Tools | `tools/` | All money is Decimal/Fraction and rounded once. Tools read no file and change nothing. |
| Workflow | `agentic/` | One model call per agent. Agents quote figures; they never compute them. |
| Persistence | `persistence/` | Only the repository touches the tables. Money is stored as exact text. |
| Access | `access/` | The service enforces roles; the dashboard hiding a page is not the control. |
| Service | `api/` | Every figure the dashboard shows comes from here. |
| Chat | `chat/` | One call per question, refuses when the documents don't cover it, the casebook is never read. |
| Dashboard | `dashboard/` | No business rules, no file reads. |
| Ops | `ops/`, `experiments/` | Monitoring, alerts, model gate and experiment ledger. All read-only. |

## The workflow

```
load_query_context → plan_assessment → assess_correction_risk → identify_category
  → check_pay_rates → compose_query_assessment → request_controller_decision (interrupt)
      UPHOLD PAY ─────────────────────────────────────────────→ record_query_outcome
      CORRECT PAY ───────────────────────→ draft_pay_statement → record_query_outcome
      CORRECT AND COMPENSATE → draft_remediation_letter → draft_pay_statement → record_query_outcome
```

5 model calls before the gate, then 0, 1 or 2 more. Checkpointed to `database/checkpoint.db` after every node.
