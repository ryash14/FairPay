"""What the assessment workflow carries from one node to the next."""
import operator
from typing import Annotated, Optional, TypedDict


class QueryAssessmentState(TypedDict):
    query_reference: str
    analyst_request: str
    analyst_id: str
    thread_id: str
    run_id: str
    assessment_id: str
    query_profile: dict
    correction_facts: dict
    category_facts: dict
    pay_facts: dict
    assessment_plan: dict
    correction_assessment: dict
    category_analysis: dict
    pay_rate_advice: dict
    controller_decision: dict
    remediation_letter: dict
    pay_statement: dict
    settlement: Optional[dict]
    llm_call_log: Annotated[list, operator.add]
