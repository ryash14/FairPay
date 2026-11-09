"""Full journeys through the REST service, on the offline rehearsal model."""
from config import config
from tests_fairpay.conftest import first_user, second_user, sign_in

EXAMPLE = "PQR-SYD-0041927"


def test_roles_reach_exactly_their_areas(service):
    desk = sign_in(service, first_user(config.ROLE_SERVICE_DESK))
    analyst = sign_in(service, first_user(config.ROLE_ANALYST))
    assert service.get("/queue", params={"direction": "All"}, headers=desk).status_code == 403
    assert service.get("/queue", params={"direction": "All"}).status_code == 401
    assert service.post("/queries/NOPE/decision", json={"decision": config.DECISION_UPHOLD_PAY,
                                                        "decision_reason": "x" * 30}, headers=analyst).status_code == 403


def test_assessment_waits_for_another_controller_then_settles(service):
    analyst = sign_in(service, first_user(config.ROLE_ANALYST))
    controller = sign_in(service, first_user(config.ROLE_CONTROLLER))
    opened = service.post("/assessments", json={"query_reference": EXAMPLE,
                                                "analyst_request": "Check the traineeship hand-over and the rate rise."},
                          headers=analyst)
    assert opened.status_code == 201, opened.text
    record = opened.json()
    assert record["status"] == config.QUERY_STATUS_PENDING and record["llm_call_count"] == config.LLM_CALLS_BEFORE_DECISION
    decided = service.post(f"/queries/{record['assessment_id']}/decision",
                           json={"decision": config.DECISION_CORRECT_AND_COMPENSATE,
                                 "decision_reason": "Traineeship ended on 09 Jan and PC1 was broken."}, headers=controller)
    assert decided.status_code == 200, decided.text
    done = decided.json()
    assert done["status"] == config.QUERY_STATUS_BY_DECISION[config.DECISION_CORRECT_AND_COMPENSATE]
    assert done["remediation_letter_text"] and done["pay_statement_text"]
    budget = service.get(f"/queries/{record['assessment_id']}/calls", headers=controller).json()
    assert budget["call_count"] == budget["expected_call_count"] == \
        config.LLM_CALLS_BY_DECISION[config.DECISION_CORRECT_AND_COMPENSATE]
    again = service.post(f"/queries/{record['assessment_id']}/decision",
                         json={"decision": config.DECISION_CORRECT_PAY, "decision_reason": "Trying to decide twice."},
                         headers=sign_in(service, second_user(config.ROLE_CONTROLLER)))
    assert again.status_code == 409


def test_service_desk_never_hears_a_figure(service):
    desk = sign_in(service, first_user(config.ROLE_SERVICE_DESK))
    reply = service.post("/chat/ask", json={"question": f"Where has {EXAMPLE} got to?"}, headers=desk).json()
    assert reply["question_type"] == config.CHAT_TYPE_QUERY_STATUS
    assert "AUD" not in reply["answer"] and config.CHAT_AMOUNTS_IN_WRITING_MESSAGE in reply["answer"]
