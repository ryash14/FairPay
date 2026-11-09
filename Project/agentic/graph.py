"""The order the nodes run in, the gate, the branch and the checkpoint."""
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from agentic import nodes
from agentic.state import QueryAssessmentState
from config import config


def build_workflow(checkpoint_path):
    """Ten nodes, one conditional branch after the gate, checkpointed to SQLite after every node."""
    graph = StateGraph(QueryAssessmentState)
    graph.add_node("load_query_context", nodes.load_query_context_node)
    graph.add_node("plan_assessment", nodes.plan_assessment_node)
    graph.add_node("assess_correction_risk", nodes.assess_correction_risk_node)
    graph.add_node("identify_category", nodes.identify_category_node)
    graph.add_node("check_pay_rates", nodes.check_pay_rates_node)
    graph.add_node("compose_query_assessment", nodes.compose_query_assessment_node)
    graph.add_node("request_controller_decision", nodes.request_controller_decision_node)
    graph.add_node("draft_remediation_letter", nodes.draft_remediation_letter_node)
    graph.add_node("draft_pay_statement", nodes.draft_pay_statement_node)
    graph.add_node("record_query_outcome", nodes.record_query_outcome_node)

    graph.add_edge(START, "load_query_context")
    graph.add_edge("load_query_context", "plan_assessment")
    graph.add_edge("plan_assessment", "assess_correction_risk")
    graph.add_edge("assess_correction_risk", "identify_category")
    graph.add_edge("identify_category", "check_pay_rates")
    graph.add_edge("check_pay_rates", "compose_query_assessment")
    graph.add_edge("compose_query_assessment", "request_controller_decision")
    graph.add_conditional_edges("request_controller_decision", nodes.route_controller_decision, {
        config.DECISION_UPHOLD_PAY: "record_query_outcome",
        config.DECISION_CORRECT_PAY: "draft_pay_statement",
        config.DECISION_CORRECT_AND_COMPENSATE: "draft_remediation_letter",
    })
    graph.add_edge("draft_remediation_letter", "draft_pay_statement")
    graph.add_edge("draft_pay_statement", "record_query_outcome")
    graph.add_edge("record_query_outcome", END)

    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    return graph.compile(checkpointer=SqliteSaver(connection))
