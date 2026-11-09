import pytest

from access.password_security import hash_password
from access.permissions import resolve_area
from agentic.agents import parse_labelled_response
from config import config
from tools.messages import fill_template


def test_decorated_reply_is_read_back_whole():
    reply = "Here you go:\n## **PRIORITY:** [High]\n- CHECKS: 1. clock\n2. rates\n**Rationale**: two sentences.\nPRIORITY: again"
    fields = parse_labelled_response(reply, ["PRIORITY", "CHECKS", "RATIONALE"], "planner")
    assert fields == {"PRIORITY": "High\nagain", "CHECKS": "1. clock\n2. rates", "RATIONALE": "two sentences."}


def test_missing_label_is_refused():
    with pytest.raises(ValueError, match="replied without RATIONALE"):
        parse_labelled_response("PRIORITY: x\nCHECKS: y", ["PRIORITY", "CHECKS", "RATIONALE"], "planner")


def test_decision_post_belongs_to_the_decision_area():
    assert resolve_area("/queries/PQA-1/decision", "POST") == config.AREA_DECISION
    assert resolve_area("/queries/PQA-1/calls", "GET") == config.AREA_AUDIT
    assert resolve_area("/queue/PQR-SYD-0000000", "GET") == config.AREA_INTAKE


def test_password_hash_is_salted_and_stable():
    assert hash_password("secret", "a") == hash_password("secret", "a") != hash_password("secret", "b")


def test_templates_fill_in_any_style():
    assert fill_template("{} is {}", "a", "b") == "a is b"
    assert fill_template("{query_reference} gone", "X", query_reference="X") == "X gone"
