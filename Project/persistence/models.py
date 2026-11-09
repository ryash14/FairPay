"""The six tables, in SQLAlchemy's typed declarative style.

Money is text written from the exact Decimal, never a float. No foreign keys
are declared: the repository joins on run_id and assessment_id.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserAccount(Base):
    __tablename__ = "user_accounts"
    username: Mapped[str] = mapped_column(primary_key=True)
    display_name: Mapped[str]
    role: Mapped[str]
    password_hash: Mapped[str]
    password_salt: Mapped[str]
    session_token: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"
    run_id: Mapped[str] = mapped_column(primary_key=True)
    thread_id: Mapped[str]
    query_reference: Mapped[str]
    analyst_id: Mapped[str]
    analyst_request: Mapped[str] = mapped_column(Text)
    status: Mapped[str]
    llm_call_count: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[Optional[datetime]]


class PayQuery(Base):
    __tablename__ = "pay_queries"
    assessment_id: Mapped[str] = mapped_column(primary_key=True)
    run_id: Mapped[str]
    query_reference: Mapped[str]
    query_id: Mapped[str]
    employee_number: Mapped[str]
    payroll_centre: Mapped[str]
    analyst_request: Mapped[str] = mapped_column(Text)
    correction_probability: Mapped[float]
    correction_band: Mapped[str]
    query_category: Mapped[str]
    category_agreement: Mapped[float]
    paid_classification: Mapped[str]
    entitled_classification: Mapped[str]
    classifications_owed: Mapped[str]
    amount_paid_aud: Mapped[str]
    entitled_pay_aud: Mapped[str]
    difference_aud: Mapped[str]
    direction: Mapped[str]
    correction_warranted: Mapped[bool]
    breached_commitments: Mapped[str]
    commitment_total_aud: Mapped[str]
    effort_needed_hours: Mapped[float]
    senior_review_required: Mapped[bool]
    assessment_plan_text: Mapped[str] = mapped_column(Text)
    assessment_text: Mapped[str] = mapped_column(Text)
    recommended_decision: Mapped[str]
    status: Mapped[str]
    remediation_letter_text: Mapped[Optional[str]] = mapped_column(Text)
    pay_statement_text: Mapped[Optional[str]] = mapped_column(Text)
    settled_amount_aud: Mapped[Optional[str]]
    settlement_direction: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ControllerDecision(Base):
    __tablename__ = "controller_decisions"
    decision_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assessment_id: Mapped[str]
    run_id: Mapped[str]
    decision: Mapped[str]
    decided_by: Mapped[str]
    decided_by_role: Mapped[str]
    decision_reason: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LlmCall(Base):
    __tablename__ = "llm_calls"
    call_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str]
    agent_name: Mapped[str]
    model_name: Mapped[str]
    prompt_characters: Mapped[int]
    response_characters: Mapped[int]
    latency_milliseconds: Mapped[int]
    called_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ChatTurn(Base):
    __tablename__ = "chat_turns"
    turn_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str]
    user_role: Mapped[str]
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str]
    query_reference: Mapped[Optional[str]]
    answer_text: Mapped[str] = mapped_column(Text)
    source_documents: Mapped[str]
    closest_distance: Mapped[float]
    was_refused: Mapped[bool]
    asked_at: Mapped[datetime] = mapped_column(server_default=func.now())
