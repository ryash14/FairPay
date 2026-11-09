"""The decision queue: assessments waiting at the gate, and the decision form."""
import streamlit as st

from config import config
from dashboard.api_client import call_service
from dashboard.ui import apply_style, aud, badges, caption, key_values, labelled_text


def render_decision_queue_page():
    apply_style()
    st.header(config.PAGE_DECISION)
    outcome = st.session_state.pop("decision_outcome", None)
    if outcome:
        st.success(outcome)

    waiting = call_service("GET", "/queries", {"status_value": [config.QUERY_STATUS_PENDING]}, None, None)
    if not waiting:
        st.info(f"Nothing is waiting. An assessment started from the {config.PAGE_QUERY} page stops here for the "
                f"{config.ROLE_CONTROLLER}.")
        return
    caption(f"{len(waiting)} assessment{'s' if len(waiting) != 1 else ''} waiting for a decision.")
    labels = {f"{r['query_reference']} · {r['assessment_id']} · {r['recommended_decision']}": r for r in waiting}
    record = labels[st.selectbox("Assessment", list(labels))]

    badges((record["recommended_decision"], config.DECISION_BADGE_COLOURS),
           (record["direction"], config.DIRECTION_BADGE_COLOURS),
           (f"score {record['correction_probability']:.2f}", None),
           (record["correction_band"], config.CORRECTION_BAND_BADGE_COLOURS), (record["query_category"], None))
    columns = st.columns(4)
    columns[0].metric("Amount paid", aud(record["amount_paid_aud"]))
    columns[1].metric("Pay owed", aud(record["entitled_pay_aud"]))
    columns[2].metric("Difference", aud(record["difference_aud"]))
    columns[3].metric("Commitment payments", aud(record["commitment_total_aud"]),
                      help=record["breached_commitments"] or "none broken")
    with st.container(border=True):
        st.markdown("**Assessment**")
        st.markdown(record["assessment_text"])
    key_values([
        ("Correction warranted", "yes" if record["correction_warranted"] else "no"),
        ("Effort", f"{record['effort_needed_hours']} hours"),
        ("Senior payroll officer", "needed" if record["senior_review_required"] else "not needed"),
        ("Assessed by", record["analyst_id"]),
    ])
    with st.expander("What the analyst asked, and the plan"):
        st.markdown(f"> {record['analyst_request']}")
        labelled_text(record["assessment_plan_text"])

    st.divider()
    if record["analyst_id"] == st.session_state.get("username"):
        st.warning(config.OWN_ASSESSMENT_REFUSED_MESSAGE)
        return
    costs = {option: config.LLM_CALLS_BY_DECISION[option] - config.LLM_CALLS_BEFORE_DECISION
             for option in config.DECISION_OPTIONS}
    with st.form("decision_form", clear_on_submit=False):
        decision = st.radio("Decision", config.DECISION_OPTIONS, index=None,
                            captions=[f"{costs[o]} further language model call{'s' if costs[o] != 1 else ''}"
                                      for o in config.DECISION_OPTIONS])
        reason = st.text_area("Reason", height=100)
        submitted = st.form_submit_button("Record the decision", type="primary")
    if submitted:
        trimmed = reason.strip()
        if decision is None:
            st.error("Choose a decision.")
        elif len(trimmed) < config.DECISION_REASON_MINIMUM_CHARACTERS:
            st.error(f"Give a reason of at least {config.DECISION_REASON_MINIMUM_CHARACTERS} characters.")
        else:
            result = call_service("POST", f"/queries/{record['assessment_id']}/decision", None,
                                  {"decision": decision, "decision_reason": trimmed},
                                  "Recording the decision and finishing the run.")
            message = f"{result['query_reference']} is now {result['status']}."
            if result["settled_amount_aud"] is not None:
                message += f" Settled amount AUD {result['settled_amount_aud']}, {result['settlement_direction']}."
            st.session_state["decision_outcome"] = message
            st.rerun()
