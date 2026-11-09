"""The ten workflow steps, the router out of the gate, and the one helper that builds the pay facts.

Everything the nodes need is loaded once, here, when the module is first
imported; the REST service reads these same objects rather than loading its
own copies, so the queue, the detail page and the stored assessment agree.
"""
import uuid

import pandas as pd
from langgraph.types import interrupt

from agentic import agents
from config import config
from data_pipeline.dataset_loader import load_raw_dataset
from knowledge.schedule_reading import read_commitment_payments, read_pay_schedule
from knowledge.vector_index import open_vector_index
from modeling.model_registry import load_feature_schema, load_model
from persistence import repository
from persistence.database import session_factory
from tools import pay_tools, prediction_tools, query_data_tools, retrieval_tools

# ----------------------------------------------------------------- loaded once
correction_model = load_model(config.CORRECTION_MODEL_FILE)
effort_model = load_model(config.EFFORT_MODEL_FILE)
category_model = load_model(config.CATEGORY_MODEL_FILE)
correction_feature_names = load_feature_schema(config.CORRECTION_SCHEMA_FILE)
effort_feature_names = load_feature_schema(config.EFFORT_SCHEMA_FILE)
open_queries = load_raw_dataset(config.OPEN_QUERIES_FILE, config.NULL_TOKENS)
open_query_notes = load_raw_dataset(config.OPEN_QUERY_NOTES_FILE, config.NULL_TOKENS)
knowledge_collection = open_vector_index(config.VECTOR_STORE_DIRECTORY, config.VECTOR_COLLECTION_NAME)
pay_schedules = {classification: read_pay_schedule(knowledge_collection, classification)
                 for classification in config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION}
commitment_payments = read_commitment_payments(knowledge_collection)


def _new_identifier(prefix):
    return prefix + uuid.uuid4().hex.upper()[:config.IDENTIFIER_HEX_LENGTH]


def _record_call(run_id, call_record):
    with session_factory() as session:
        repository.insert_llm_call(session, run_id, call_record)


def _labelled_text(fields):
    return "\n\n".join(f"{label}: {text}" for label, text in fields.items())


# ----------------------------------------------------------------- pay facts
def build_pay_facts(query_profile):
    """The pay owed for one query, worked out in one place for the workflow and the detail page alike."""
    hours = pay_tools.measure_hours(query_profile)
    pieces = pay_tools.build_pay_pieces(query_profile, pay_schedules)
    entitled = pay_tools.compute_entitled_pay(pieces, hours)
    schedules_used = {}
    for classification in [piece["classification"] for piece in pieces] + \
            [query_profile[config.PAID_CLASSIFICATION_COLUMN]]:
        schedules_used.setdefault(classification, pay_schedules[classification])
    return {
        "pay_schedules": schedules_used,
        "hours": hours,
        "pieces": entitled["pieces"],
        "comparison": pay_tools.compare_with_paid(query_profile, entitled["entitled_pay_aud"]),
        "commitments": pay_tools.compute_commitment_payments(query_profile, commitment_payments),
    }


# ----------------------------------------------------------------- nodes
def load_query_context_node(state):
    reference = state["query_reference"]
    profile = query_data_tools.fetch_query_profile(open_queries, reference)
    notes = query_data_tools.fetch_query_notes(open_query_notes, reference)
    correction_facts = prediction_tools.build_correction_facts(correction_model, correction_feature_names,
                                                               pd.DataFrame([profile]))[0]
    category_facts = prediction_tools.build_category_facts(category_model, notes)
    run_id = _new_identifier(config.RUN_ID_PREFIX)
    assessment_id = _new_identifier(config.ASSESSMENT_ID_PREFIX)
    with session_factory() as session:
        repository.insert_agent_run(session, {
            "run_id": run_id, "thread_id": state["thread_id"], "query_reference": reference,
            "analyst_id": state["analyst_id"], "analyst_request": state["analyst_request"],
            "status": config.AGENT_RUN_STATUS_RUNNING})
    return {"run_id": run_id, "assessment_id": assessment_id, "query_profile": profile,
            "correction_facts": correction_facts, "category_facts": category_facts}


def plan_assessment_node(state):
    result = agents.plan_assessment(state["query_profile"], state["analyst_request"])
    _record_call(state["run_id"], result["call_record"])
    return {"assessment_plan": result["assessment_plan"], "llm_call_log": [result["call_record"]]}


def assess_correction_risk_node(state):
    result = agents.assess_correction_risk(state["correction_facts"], state["query_profile"], state["assessment_plan"])
    _record_call(state["run_id"], result["call_record"])
    return {"correction_assessment": result["correction_assessment"], "llm_call_log": [result["call_record"]]}


def identify_category_node(state):
    result = agents.identify_category(state["category_facts"], state["query_profile"], state["assessment_plan"],
                                      state["correction_assessment"])
    _record_call(state["run_id"], result["call_record"])
    return {"category_analysis": result["category_analysis"], "llm_call_log": [result["call_record"]]}


def check_pay_rates_node(state):
    pay_facts = build_pay_facts(state["query_profile"])
    result = agents.advise_on_pay_rates(pay_facts, state["query_profile"], state["assessment_plan"])
    _record_call(state["run_id"], result["call_record"])
    return {"pay_facts": pay_facts, "pay_rate_advice": result["pay_rate_advice"], "llm_call_log": [result["call_record"]]}


def compose_query_assessment_node(state):
    profile, pay_facts = state["query_profile"], state["pay_facts"]
    comparison, commitments = pay_facts["comparison"], pay_facts["commitments"]
    effort = prediction_tools.estimate_remediation_effort(
        effort_model, effort_feature_names, profile, state["correction_facts"]["correction_band"],
        state["category_facts"]["query_category"], pay_facts["pieces"], comparison["money_at_stake_aud"])
    result = agents.write_query_assessment(profile, state["analyst_request"], state["correction_facts"], pay_facts,
                                           effort, state["correction_assessment"], state["category_analysis"],
                                           state["pay_rate_advice"])
    written = result["query_assessment"]
    owed = []
    for piece in pay_facts["pieces"]:
        if piece["classification"] not in owed:
            owed.append(piece["classification"])
    with session_factory() as session:
        repository.insert_llm_call(session, state["run_id"], result["call_record"])
        repository.insert_pay_query(session, {
            "assessment_id": state["assessment_id"], "run_id": state["run_id"],
            "query_reference": profile[config.QUERY_REFERENCE_COLUMN], "query_id": profile["query_id"],
            "employee_number": profile["employee_number"], "payroll_centre": profile[config.PAYROLL_CENTRE_COLUMN],
            "analyst_request": state["analyst_request"],
            "correction_probability": state["correction_facts"]["correction_probability"],
            "correction_band": state["correction_facts"]["correction_band"],
            "query_category": state["category_facts"]["query_category"],
            "category_agreement": state["category_facts"]["agreement"],
            "paid_classification": profile[config.PAID_CLASSIFICATION_COLUMN],
            "entitled_classification": profile[config.ENTITLED_CLASSIFICATION_COLUMN],
            "classifications_owed": ", ".join(owed),
            "amount_paid_aud": str(comparison["amount_paid_aud"]),
            "entitled_pay_aud": str(comparison["entitled_pay_aud"]),
            "difference_aud": str(comparison["difference_aud"]),
            "direction": comparison["direction"],
            "correction_warranted": comparison["correction_warranted"],
            "breached_commitments": ", ".join(entry["commitment_code"] for entry in commitments["breached_commitments"]),
            "commitment_total_aud": str(commitments["commitment_total_aud"]),
            "effort_needed_hours": effort["effort_needed_hours"],
            "senior_review_required": effort["senior_review_required"],
            "assessment_plan_text": _labelled_text(state["assessment_plan"]),
            "assessment_text": written["ASSESSMENT"],
            "recommended_decision": written["RECOMMENDED DECISION"],
            "status": config.QUERY_STATUS_PENDING,
        })
    return {"llm_call_log": [result["call_record"]]}


def request_controller_decision_node(state):
    with session_factory() as session:
        repository.update_agent_run(session, state["run_id"], config.AGENT_RUN_STATUS_AWAITING_DECISION,
                                    len(state["llm_call_log"]))
    controller_decision = interrupt(state["assessment_id"])
    settlement = pay_tools.compute_settled_amount(controller_decision["decision"],
                                                  state["pay_facts"]["comparison"]["difference_aud"],
                                                  state["pay_facts"]["commitments"]["commitment_total_aud"])
    return {"controller_decision": controller_decision, "remediation_letter": {}, "pay_statement": {},
            "settlement": settlement}


def route_controller_decision(state):
    return state["controller_decision"]["decision"]


def draft_remediation_letter_node(state):
    steps = retrieval_tools.read_employee_steps(knowledge_collection, state["category_facts"]["query_category"])
    result = agents.draft_remediation_letter(state["query_profile"], state["pay_facts"]["commitments"], steps)
    _record_call(state["run_id"], result["call_record"])
    return {"remediation_letter": result["remediation_letter"], "llm_call_log": [result["call_record"]]}


def draft_pay_statement_node(state):
    result = agents.draft_pay_statement(state["query_profile"], state["pay_facts"], state["remediation_letter"],
                                        state["settlement"])
    _record_call(state["run_id"], result["call_record"])
    return {"pay_statement": result["pay_statement"], "llm_call_log": [result["call_record"]]}


def record_query_outcome_node(state):
    decision = state["controller_decision"]
    settlement = state["settlement"]
    with session_factory() as session:
        repository.insert_controller_decision(session, {
            "assessment_id": state["assessment_id"], "run_id": state["run_id"], "decision": decision["decision"],
            "decided_by": decision["decided_by"], "decided_by_role": decision["decided_by_role"],
            "decision_reason": decision["decision_reason"]})
        repository.record_query_outcome(session, state["assessment_id"], {
            "status": config.QUERY_STATUS_BY_DECISION[decision["decision"]],
            "remediation_letter_text": _labelled_text(state["remediation_letter"]) if state["remediation_letter"] else None,
            "pay_statement_text": _labelled_text(state["pay_statement"]) if state["pay_statement"] else None,
            "settled_amount_aud": str(settlement["settled_amount_aud"]) if settlement else None,
            "settlement_direction": settlement["direction"] if settlement else None,
        })
        repository.update_agent_run(session, state["run_id"], config.AGENT_RUN_STATUS_COMPLETE,
                                    len(state["llm_call_log"]))
    return {}
