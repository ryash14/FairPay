"""The audit trail: assessed pay queries, the record behind each, its call budget, and the chat log."""
import pandas as pd
import streamlit as st

from config import config
from dashboard.api_client import call_service
from dashboard.ui import apply_style, aud, badges, key_values, labelled_text


def _when(stamp):
    return "—" if not stamp else str(stamp).replace("T", " ")[:19] + " UTC"


def render_audit_trail_page():
    apply_style()
    st.header(config.PAGE_AUDIT)
    queries_tab, chat_tab = st.tabs(["Assessed pay queries", "Payroll chat log"])

    with queries_tab:
        chosen = st.multiselect("Status", config.QUERY_STATUS_OPTIONS, default=list(config.DECIDED_QUERY_STATUSES))
        if not chosen:
            st.info("Choose at least one status.")
        else:
            records = call_service("GET", "/queries", {"status_value": chosen}, None, None)
            counts = st.columns(len(chosen))
            for column, status in zip(counts, chosen):
                column.metric(status, sum(1 for r in records if r["status"] == status))
            if not records:
                st.caption("No assessment has those statuses yet.")
            else:
                table = pd.DataFrame([{
                    "Reference": r["query_reference"], "Status": r["status"], "Recommended": r["recommended_decision"],
                    "Decision": r["decision"] or "—", "Decided by": r["decided_by"] or "—",
                    "Settled": aud(r["settled_amount_aud"]), "Model calls": r["llm_call_count"],
                } for r in records])
                picked = st.dataframe(table, hide_index=True, width="stretch", on_select="rerun",
                                      selection_mode="single-row", key="audit_table")
                rows = picked.selection.rows if picked and hasattr(picked, "selection") else []
                if rows:
                    record = records[rows[0]]
                    st.divider()
                    badges((record["status"], config.STATUS_BADGE_COLOURS),
                           (record["recommended_decision"], config.DECISION_BADGE_COLOURS))
                    key_values([
                        ("Assessment", record["assessment_id"]),
                        ("Opened", f"{_when(record['created_at'])} by {record['analyst_id']}"),
                        ("Decision", f"{record['decision']} by {record['decided_by']} ({record['decided_by_role']}), "
                                     f"{_when(record['decided_at'])}" if record["decision"] else "not yet decided"),
                        ("Reason", record["decision_reason"]),
                        ("Settled", f"{aud(record['settled_amount_aud'])}, {record['settlement_direction']}"
                                    if record["settled_amount_aud"] is not None else "nothing settled"),
                        ("Paid / owed", f"{aud(record['amount_paid_aud'])} / {aud(record['entitled_pay_aud'])}"),
                        ("Commitment payments due", aud(record["commitment_total_aud"])),
                    ])
                    with st.container(border=True):
                        st.markdown("**Assessment**")
                        st.markdown(record["assessment_text"])
                    if record["remediation_letter_text"]:
                        with st.expander("Remediation letter"):
                            labelled_text(record["remediation_letter_text"])
                    if record["pay_statement_text"]:
                        with st.expander("Pay correction statement"):
                            labelled_text(record["pay_statement_text"])
                    budget = call_service("GET", f"/queries/{record['assessment_id']}/calls", None, None, None)
                    st.subheader("Call budget")
                    columns = st.columns(2)
                    columns[0].metric("Calls made / expected", f"{budget['call_count']} / {budget['expected_call_count']}")
                    columns[1].metric("Total latency", f"{budget['total_latency_milliseconds'] / 1000:.1f} s")
                    st.dataframe(pd.DataFrame([{
                        "Agent": c["agent_name"], "Model": c["model_name"], "Prompt chars": c["prompt_characters"],
                        "Reply chars": c["response_characters"], "Latency ms": c["latency_milliseconds"],
                    } for c in budget["calls"]]), hide_index=True, width="stretch")

    with chat_tab:
        turns = call_service("GET", "/audit/chat-turns", {"turn_limit": config.CHAT_AUDIT_MAX_ROWS}, None, None)
        if not turns:
            st.caption("Nobody has asked the payroll chat anything yet.")
        else:
            st.dataframe(pd.DataFrame([{
                "Asked": _when(t["asked_at"]), "Who": t["username"], "Role": t["user_role"],
                "Question": t["question_text"], "Type": t["question_type"], "Pay query": t["query_reference"] or "—",
                "Refused": t["was_refused"], "Sources": t["source_documents"] or "—",
            } for t in turns]), hide_index=True, width="stretch", height=520)
