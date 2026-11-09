"""The REST service: queue, query detail, assessment workflow, decision, call budget, chat and audit.

Every figure the dashboard shows is produced here, from the same objects the
workflow uses, so the queue, the detail page and the stored assessment agree.
"""
import threading
import uuid
from typing import Annotated, Optional

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors
from langgraph.types import Command
from sqlalchemy import true
import hmac
import secrets

from access.password_security import hash_password
from access.permissions import authorize_request
from agentic import nodes
from agentic.graph import build_workflow
from api.schemas import (AssessmentRequest, CallBudgetResponse, ChatRequest, ChatResponse, ChatTurnResponse,
                         DecisionRequest, DirectionFilter, PayQueryResponse, QueryDetailResponse, QueryStatusValue,
                         QueueRow, SignedInUserResponse, SignedOutResponse, SignInRequest)
from chat.conversation_memory import recall_conversation
from chat.payroll_assistant import answer_from_documents
from chat.query_status_answer import answer_query_status
from config import config
from persistence import repository
from persistence.database import session_factory
from persistence.models import ChatTurn, PayQuery, UserAccount
from tools import pay_tools, prediction_tools, query_data_tools
from tools.messages import fill_template

# ----------------------------------------------------------------- built once at import
assessment_graph = build_workflow(config.CHECKPOINT_DATABASE_FILE)
correction_facts_by_reference = {
    reference: facts for reference, facts in zip(
        nodes.open_queries[config.QUERY_REFERENCE_COLUMN],
        prediction_tools.build_correction_facts(nodes.correction_model, nodes.correction_feature_names,
                                                nodes.open_queries))}
query_queue = [{**row, **correction_facts_by_reference[row[config.QUERY_REFERENCE_COLUMN]]}
               for row in pay_tools.rank_query_queue(nodes.open_queries, nodes.pay_schedules)]

SessionTokenHeader = Annotated[Optional[str], Header(alias=config.SESSION_TOKEN_HEADER)]
SignedInUser = Annotated[dict, Depends(authorize_request)]

public_router = APIRouter()
guarded_router = APIRouter()
_decision_locks = {}
_decision_locks_guard = threading.Lock()


def _thread_config(thread_id):
    return {"configurable": {"thread_id": thread_id}}


def _not_in_queue(reference):
    return HTTPException(status_code=404, detail=fill_template(config.QUERY_NOT_IN_QUEUE_MESSAGE, reference,
                                                               query_reference=reference))


def _one_record(assessment_id):
    with session_factory() as session:
        records = repository.fetch_query_records(session, PayQuery.assessment_id == assessment_id)
    if not records:
        raise HTTPException(status_code=404, detail=config.ASSESSMENT_NOT_FOUND_MESSAGE)
    return records[0]


# ----------------------------------------------------------------- public
@public_router.post("/auth/signin", response_model=SignedInUserResponse)
def sign_in_user(sign_in_request: SignInRequest):
    with session_factory() as session:
        account = repository.fetch_user_account(session, UserAccount.username == sign_in_request.username)
        if account is None or not hmac.compare_digest(
                hash_password(sign_in_request.password, account["password_salt"]), account["password_hash"]):
            raise HTTPException(status_code=401, detail=config.SIGN_IN_FAILED_MESSAGE)
        token = secrets.token_urlsafe(config.SESSION_TOKEN_BYTES)
        repository.update_session_token(session, account["username"], token)
    return {"username": account["username"], "display_name": account["display_name"], "role": account["role"],
            "session_token": token, "pages": list(config.ROLE_PAGE_ACCESS[account["role"]]),
            "areas": list(config.ROLE_AREA_ACCESS[account["role"]])}


@public_router.post("/auth/signout", response_model=SignedOutResponse)
def sign_out_user(session_token: SessionTokenHeader = None):
    with session_factory() as session:
        account = (repository.fetch_user_account(session, UserAccount.session_token == session_token)
                   if session_token else None)
        if account is None:
            raise HTTPException(status_code=401, detail=config.SIGN_IN_REQUIRED_MESSAGE)
        repository.update_session_token(session, account["username"], None)
    return {"username": account["username"], "signed_out": True}


@public_router.get("/health")
def report_health():
    """Liveness for containers and the dry run: no figures, no sign-in."""
    return {"status": "ok", "open_queries": len(query_queue), "title": config.API_TITLE}


# ----------------------------------------------------------------- intake
@guarded_router.get("/queue", response_model=list[QueueRow])
def list_query_queue(direction: Annotated[DirectionFilter, Query()]):
    if direction == config.QUEUE_DIRECTION_ALL:
        return query_queue
    return [row for row in query_queue if row["direction"] == direction]


@guarded_router.get("/queue/{query_reference}", response_model=QueryDetailResponse)
def get_query_detail(query_reference: str):
    if query_reference not in correction_facts_by_reference:
        raise _not_in_queue(query_reference)
    profile = query_data_tools.fetch_query_profile(nodes.open_queries, query_reference)
    note_texts = query_data_tools.fetch_query_notes(nodes.open_query_notes, query_reference)
    correction = correction_facts_by_reference[query_reference]
    category = prediction_tools.build_category_facts(nodes.category_model, note_texts)
    pay = nodes.build_pay_facts(profile)
    effort = prediction_tools.estimate_remediation_effort(
        nodes.effort_model, nodes.effort_feature_names, profile, correction["correction_band"],
        category["query_category"], pay["pieces"], pay["comparison"]["money_at_stake_aud"])
    return {"profile": {key: (None if pd.isna(value) else value) for key, value in profile.items()},
            "note_texts": note_texts, "correction": correction, "category": category, "pay": pay, "effort": effort}


# ----------------------------------------------------------------- assessment
@guarded_router.post("/assessments", response_model=PayQueryResponse, status_code=201)
def start_query_assessment(assessment_request: AssessmentRequest, signed_in_user: SignedInUser, request: Request):
    reference = assessment_request.query_reference
    if reference not in correction_facts_by_reference:
        raise _not_in_queue(reference)
    thread_id = f"{reference}-{uuid.uuid4().hex.upper()[:config.IDENTIFIER_HEX_LENGTH]}"
    request.state.opened_thread_id = thread_id
    assessment_graph.invoke({"query_reference": reference, "analyst_request": assessment_request.analyst_request,
                             "analyst_id": signed_in_user["username"], "thread_id": thread_id},
                            _thread_config(thread_id))
    assessment_id = assessment_graph.get_state(_thread_config(thread_id)).values["assessment_id"]
    return _one_record(assessment_id)


# ----------------------------------------------------------------- audit
@guarded_router.get("/queries", response_model=list[PayQueryResponse])
def list_queries(status_value: Annotated[list[QueryStatusValue], Query()]):
    with session_factory() as session:
        return repository.fetch_query_records(session, PayQuery.status.in_(status_value))


@guarded_router.post("/queries/{assessment_id}/decision", response_model=PayQueryResponse)
def submit_controller_decision(assessment_id: str, decision_request: DecisionRequest, signed_in_user: SignedInUser):
    with _decision_locks_guard:
        lock = _decision_locks.setdefault(assessment_id, threading.Lock())
    record = _one_record(assessment_id)
    if record["analyst_id"] == signed_in_user["username"]:
        raise HTTPException(status_code=403, detail=config.OWN_ASSESSMENT_REFUSED_MESSAGE)
    if record["status"] != config.QUERY_STATUS_PENDING:
        raise HTTPException(status_code=409, detail=config.ALREADY_DECIDED_MESSAGE)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=fill_template(config.DECISION_IN_PROGRESS_MESSAGE,
                                                                  decision_request.decision,
                                                                  decision=decision_request.decision))
    try:
        snapshot = assessment_graph.get_state(_thread_config(record["thread_id"]))
        held = (snapshot.values or {}).get("controller_decision")
        if held and held.get("decision") != decision_request.decision:
            raise HTTPException(status_code=409, detail=fill_template(config.DECISION_IN_PROGRESS_MESSAGE,
                                                                      held["decision"], decision=held["decision"]))
        assessment_graph.invoke(Command(resume={
            "decision": decision_request.decision, "decided_by": signed_in_user["display_name"],
            "decided_by_role": signed_in_user["role"], "decision_reason": decision_request.decision_reason,
        }), _thread_config(record["thread_id"]))
    finally:
        lock.release()
    return _one_record(assessment_id)


@guarded_router.get("/queries/{assessment_id}/calls", response_model=CallBudgetResponse)
def get_call_budget(assessment_id: str):
    record = _one_record(assessment_id)
    with session_factory() as session:
        calls = repository.fetch_llm_calls(session, record["run_id"])
    expected = (config.LLM_CALLS_BEFORE_DECISION if record["decision"] is None
                else config.LLM_CALLS_BY_DECISION[record["decision"]])
    return {"assessment_id": assessment_id, "run_id": record["run_id"], "call_count": len(calls),
            "expected_call_count": expected,
            "total_latency_milliseconds": sum(call["latency_milliseconds"] for call in calls), "calls": calls}


# ----------------------------------------------------------------- chat
@guarded_router.post("/chat/ask", response_model=ChatResponse)
def ask_payroll_assistant(chat_request: ChatRequest, signed_in_user: SignedInUser):
    question = chat_request.question
    with session_factory() as session:
        conversation = recall_conversation(session, signed_in_user["username"], question)
    result = answer_from_documents(nodes.knowledge_collection, question, conversation)
    with session_factory() as session:
        if result["question_type"] == config.CHAT_TYPE_QUERY_STATUS:
            result.update(answer_query_status(session, nodes.open_queries, signed_in_user["role"],
                                              result["query_reference"]))
        repository.insert_chat_turn(session, {
            "username": signed_in_user["username"], "user_role": signed_in_user["role"], "question_text": question,
            "question_type": result["question_type"], "query_reference": result["query_reference"],
            "answer_text": result["answer"], "source_documents": ", ".join(result["source_documents"]),
            "closest_distance": result["closest_distance"], "was_refused": result["was_refused"]})
    return result


@guarded_router.get("/chat/turns", response_model=list[ChatTurnResponse])
def list_own_chat_turns(signed_in_user: SignedInUser,
                        turn_limit: Annotated[int, Query(ge=1, le=config.CHAT_AUDIT_MAX_ROWS)]):
    with session_factory() as session:
        return repository.fetch_chat_turns(session, ChatTurn.username == signed_in_user["username"], turn_limit)


@guarded_router.get("/audit/chat-turns", response_model=list[ChatTurnResponse])
def list_recent_chat_turns(turn_limit: Annotated[int, Query(ge=1, le=config.CHAT_AUDIT_MAX_ROWS)]):
    with session_factory() as session:
        return repository.fetch_chat_turns(session, true(), turn_limit)


@guarded_router.get("/audit/monitoring")
def report_monitoring():
    """Operational health for the audit trail: runs, budgets, latency and refusals. No language model call."""
    from ops.monitoring import collect_monitoring_snapshot
    return collect_monitoring_snapshot()


# ----------------------------------------------------------------- failures
def report_failed_request(request: Request, failure: Exception):
    """One 502 reply for every failure, and a failed run is never left looking as though it is running."""
    thread_id = getattr(request.state, "opened_thread_id", None)
    if thread_id:
        try:
            run_id = (assessment_graph.get_state(_thread_config(thread_id)).values or {}).get("run_id")
        except Exception:  # noqa: BLE001 - a broken checkpoint must not hide the original failure
            run_id = None
        if run_id:
            with session_factory() as session:
                calls = repository.fetch_llm_calls(session, run_id)
                repository.update_agent_run(session, run_id, config.AGENT_RUN_STATUS_FAILED, len(calls))
    return JSONResponse(status_code=502, content={
        "detail": f"{request.method} {request.url.path} could not be completed: {failure}"})


service_application = FastAPI(title=config.API_TITLE)
service_application.include_router(public_router)
service_application.include_router(guarded_router, dependencies=[Depends(authorize_request)])
for failure_type in (ValueError, genai_errors.APIError, httpx.HTTPError):
    service_application.add_exception_handler(failure_type, report_failed_request)
