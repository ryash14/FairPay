"""Every read and write against the six tables.

Callers get plain dictionaries keyed by column name, never ORM objects. Each
function works in a session its caller opened and commits its writes before
returning.
"""
from sqlalchemy import func, select, update

from config import config

from persistence.models import AgentRun, ChatTurn, ControllerDecision, LlmCall, PayQuery, UserAccount


def _row(instance):
    return {column.key: getattr(instance, column.key) for column in instance.__table__.columns}


# ----------------------------------------------------------------- accounts
def insert_user_account(session, account_record):
    account = UserAccount(**account_record, session_token=None)
    session.add(account)
    session.commit()
    return account.username


def fetch_user_account(session, condition):
    account = session.scalars(select(UserAccount).where(condition).limit(1)).first()
    return _row(account) if account is not None else None


def update_session_token(session, username, session_token):
    account = session.get(UserAccount, username)
    account.session_token = session_token
    session.commit()
    return username


# ----------------------------------------------------------------- runs and calls
def insert_agent_run(session, run_record):
    run = AgentRun(**run_record)
    session.add(run)
    session.commit()
    return run.run_id


def update_agent_run(session, run_id, status_value, llm_call_count):
    run = session.get(AgentRun, run_id)
    run.status = status_value
    run.llm_call_count = llm_call_count
    if status_value in config.AGENT_RUN_FINISHED_STATUSES:
        run.finished_at = session.scalar(select(func.now()))
    session.commit()
    return run_id


def insert_llm_call(session, run_id, call_record):
    call = LlmCall(run_id=run_id, **call_record)
    session.add(call)
    session.commit()
    return call.call_id


def fetch_llm_calls(session, run_id):
    calls = session.scalars(select(LlmCall).where(LlmCall.run_id == run_id).order_by(LlmCall.call_id))
    return [_row(call) for call in calls]


# ----------------------------------------------------------------- assessments
def insert_pay_query(session, query_record):
    record = PayQuery(**query_record, remediation_letter_text=None, pay_statement_text=None,
                      settled_amount_aud=None, settlement_direction=None)
    session.add(record)
    session.commit()
    return record.assessment_id


def record_query_outcome(session, assessment_id, outcome_record):
    result = session.execute(update(PayQuery).where(PayQuery.assessment_id == assessment_id).values(**outcome_record))
    if result.rowcount != 1:
        session.rollback()
        raise ValueError(f"No pay query record has the assessment {assessment_id}")
    session.commit()
    return assessment_id


def fetch_query_records(session, condition):
    columns = [*PayQuery.__table__.columns, AgentRun.thread_id, AgentRun.analyst_id, AgentRun.llm_call_count,
               ControllerDecision.decision, ControllerDecision.decided_by, ControllerDecision.decided_by_role,
               ControllerDecision.decision_reason, ControllerDecision.decided_at]
    statement = (select(*columns)
                 .join(AgentRun, AgentRun.run_id == PayQuery.run_id)
                 .outerjoin(ControllerDecision, ControllerDecision.assessment_id == PayQuery.assessment_id)
                 .where(condition)
                 .order_by(PayQuery.created_at.desc(), PayQuery.assessment_id.desc()))
    return [dict(row) for row in session.execute(statement).mappings()]


def insert_controller_decision(session, decision_record):
    decision = ControllerDecision(**decision_record)
    session.add(decision)
    session.commit()
    return decision.decision_id


# ----------------------------------------------------------------- chat
def insert_chat_turn(session, turn_record):
    turn = ChatTurn(**turn_record)
    session.add(turn)
    session.commit()
    return turn.turn_id


def fetch_chat_turns(session, condition, turn_limit):
    turns = session.scalars(select(ChatTurn).where(condition).order_by(ChatTurn.turn_id.desc()).limit(turn_limit))
    return [_row(turn) for turn in turns]
