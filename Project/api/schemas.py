"""The shape of every request the service accepts and every reply it returns.

Money is Decimal, so it travels as exact text in JSON and is never rounded by a
float on the way. A reply carries exactly the fields declared here.
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from config import config

DirectionFilter = Literal[tuple(config.QUEUE_DIRECTION_OPTIONS)]
QueryStatusValue = Literal[tuple(config.QUERY_STATUS_OPTIONS)]
DecisionValue = Literal[tuple(config.DECISION_OPTIONS)]


class SignInRequest(BaseModel):
    username: str
    password: str


class SignedInUserResponse(BaseModel):
    username: str
    display_name: str
    role: str
    session_token: str
    pages: list[str]
    areas: list[str]


class SignedOutResponse(BaseModel):
    username: str
    signed_out: bool


class QueueRow(BaseModel):
    query_reference: str
    payroll_centre: str
    paid_classification: str
    entitled_classification: str
    amount_paid_aud: Decimal
    entitled_pay_aud: Decimal
    difference_aud: Decimal
    money_at_stake_aud: Decimal
    direction: str
    correction_warranted: bool
    correction_probability: float
    correction_band: str


class QueryDetailResponse(BaseModel):
    profile: dict
    note_texts: list[str]
    correction: dict
    category: dict
    pay: dict
    effort: dict


class AssessmentRequest(BaseModel):
    query_reference: str
    analyst_request: str = Field(min_length=config.ANALYST_REQUEST_MINIMUM_CHARACTERS)


class DecisionRequest(BaseModel):
    decision: DecisionValue
    decision_reason: str = Field(min_length=config.DECISION_REASON_MINIMUM_CHARACTERS)


class PayQueryResponse(BaseModel):
    assessment_id: str
    run_id: str
    thread_id: str
    analyst_id: str
    query_reference: str
    query_id: str
    employee_number: str
    payroll_centre: str
    analyst_request: str
    correction_probability: float
    category_agreement: float
    effort_needed_hours: float
    correction_band: str
    query_category: str
    paid_classification: str
    entitled_classification: str
    classifications_owed: str
    amount_paid_aud: Decimal
    entitled_pay_aud: Decimal
    difference_aud: Decimal
    commitment_total_aud: Decimal
    direction: str
    breached_commitments: str
    assessment_plan_text: str
    assessment_text: str
    recommended_decision: str
    status: str
    correction_warranted: bool
    senior_review_required: bool
    remediation_letter_text: Optional[str]
    pay_statement_text: Optional[str]
    settlement_direction: Optional[str]
    settled_amount_aud: Optional[Decimal]
    created_at: datetime
    llm_call_count: int
    decision: Optional[str]
    decided_by: Optional[str]
    decided_by_role: Optional[str]
    decision_reason: Optional[str]
    decided_at: Optional[datetime]


class CallBudgetResponse(BaseModel):
    assessment_id: str
    run_id: str
    call_count: int
    expected_call_count: int
    total_latency_milliseconds: int
    calls: list[dict]


class ChatRequest(BaseModel):
    question: str = Field(min_length=config.CHAT_QUESTION_MINIMUM_CHARACTERS)


class ChatResponse(BaseModel):
    question_type: str
    query_reference: Optional[str]
    answer: str
    source_documents: list[str]
    was_refused: bool


class ChatTurnResponse(BaseModel):
    turn_id: int
    username: str
    user_role: str
    question_text: str
    question_type: str
    query_reference: Optional[str]
    answer_text: str
    source_documents: str
    closest_distance: float
    was_refused: bool
    asked_at: datetime
