"""Operational health of the running system, read from the audit database alone.

Used by GET /audit/monitoring, by `python -m ops.monitor` on the command line,
and by CI after the smoke run. Nothing here calls a model or changes a row.
"""
from collections import Counter
from datetime import datetime, timedelta, UTC
import statistics

from sqlalchemy import select

from config import config
from persistence.database import session_factory
from persistence.models import AgentRun, ChatTurn, ControllerDecision, LlmCall, PayQuery

STUCK_AFTER_MINUTES = 15


def _percentile(values, share):
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(share * (len(ordered) - 1)))))
    return int(ordered[index])


def collect_monitoring_snapshot():
    with session_factory() as session:
        runs = session.execute(select(AgentRun.run_id, AgentRun.status, AgentRun.llm_call_count,
                                      AgentRun.started_at)).all()
        calls = session.execute(select(LlmCall.run_id, LlmCall.agent_name, LlmCall.latency_milliseconds)).all()
        decisions = session.execute(select(ControllerDecision.assessment_id, ControllerDecision.decision)).all()
        statuses = session.execute(select(PayQuery.status)).scalars().all()
        chats = session.execute(select(ChatTurn.question_type, ChatTurn.was_refused, ChatTurn.closest_distance)).all()

    calls_by_run = Counter(call.run_id for call in calls)
    decision_by_run = {}
    with session_factory() as session:
        for run_id, decision in session.execute(
                select(PayQuery.run_id, ControllerDecision.decision)
                .join(ControllerDecision, ControllerDecision.assessment_id == PayQuery.assessment_id)).all():
            decision_by_run[run_id] = decision

    alerts = []
    now = datetime.now(UTC).replace(tzinfo=None)
    for run in runs:
        expected = (config.LLM_CALLS_BY_DECISION[decision_by_run[run.run_id]] if run.run_id in decision_by_run
                    else config.LLM_CALLS_BEFORE_DECISION)
        made = calls_by_run.get(run.run_id, 0)
        if run.status == config.AGENT_RUN_STATUS_FAILED:
            alerts.append({"severity": "high", "run_id": run.run_id, "alert": "run failed", "calls_made": made})
        elif made > expected:
            alerts.append({"severity": "high", "run_id": run.run_id, "alert": "call budget exceeded",
                           "calls_made": made, "calls_expected": expected})
        elif run.status == config.AGENT_RUN_STATUS_RUNNING and run.started_at and \
                now - run.started_at > timedelta(minutes=STUCK_AFTER_MINUTES):
            alerts.append({"severity": "medium", "run_id": run.run_id, "alert": "run still running after "
                           f"{STUCK_AFTER_MINUTES} minutes"})

    latency_by_agent = {}
    for call in calls:
        latency_by_agent.setdefault(call.agent_name, []).append(call.latency_milliseconds)
    refused = sum(1 for chat in chats if chat.was_refused)
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "runs_by_status": dict(Counter(run.status for run in runs)),
        "assessments_by_status": dict(Counter(statuses)),
        "decisions_by_outcome": dict(Counter(decision.decision for decision in decisions)),
        "llm_calls": len(calls),
        "latency_ms": {"p50": _percentile([c.latency_milliseconds for c in calls], 0.5),
                       "p95": _percentile([c.latency_milliseconds for c in calls], 0.95)},
        "latency_ms_by_agent": {agent: {"calls": len(values), "median": int(statistics.median(values)),
                                        "p95": _percentile(values, 0.95)}
                                for agent, values in sorted(latency_by_agent.items())},
        "chat": {"questions": len(chats), "refused": refused,
                 "refusal_rate": round(refused / len(chats), 4) if chats else 0.0,
                 "by_type": dict(Counter(chat.question_type for chat in chats))},
        "alerts": alerts,
    }
