"""The query detail page and the form that opens an assessment."""
import pandas as pd
import streamlit as st

from config import config
from dashboard.api_client import call_service
from dashboard.ui import apply_style, aud, badges, caption, key_values


def describe_rates(rate_window):
    if rate_window.get("night_rate_aud") is not None:
        return f"day AUD {rate_window['day_rate_aud']}, night AUD {rate_window['night_rate_aud']} an hour"
    return f"AUD {rate_window['ordinary_rate_aud']} an hour"


def _yes_no(flag):
    return config.BOOLEAN_LABELS.get(config.BOOLEAN_YES if flag else config.BOOLEAN_NO, "yes" if flag else "no")


def render_query_detail_page():
    apply_style()
    st.header(config.PAGE_QUERY)
    queue = call_service("GET", "/queue", {"direction": config.QUEUE_DIRECTION_ALL}, None, None)
    references = [row["query_reference"] for row in queue]
    if not references:
        st.info("The open queue is empty.")
        return
    focus = st.session_state.get("focus_query")
    reference = st.selectbox("Pay query", references, index=references.index(focus) if focus in references else 0)
    st.session_state["focus_query"] = reference
    detail = call_service("GET", f"/queue/{reference}", None, None, None)
    profile, pay, effort = detail["profile"], detail["pay"], detail["effort"]
    comparison, commitments = pay["comparison"], pay["commitments"]
    correction, category = detail["correction"], detail["category"]

    badges((comparison["direction"], config.DIRECTION_BADGE_COLOURS),
           (f"score {correction['correction_probability']:.2f}", None),
           (correction["correction_band"], config.CORRECTION_BAND_BADGE_COLOURS),
           (category["query_category"], None), (profile[config.PAYROLL_CENTRE_COLUMN], None),
           (profile["employee_number"], None))

    pieces = pay["pieces"]
    columns = st.columns(5)
    columns[0].metric("Amount paid", aud(comparison["amount_paid_aud"]))
    columns[1].metric("Pay owed", aud(comparison["entitled_pay_aud"]),
                      help=f"{len(pieces)} piece{'s' if len(pieces) != 1 else ''}, rounded once, at the total")
    columns[2].metric("Difference", aud(comparison["difference_aud"]), help=comparison["direction"])
    broken = ", ".join(entry["commitment_code"] for entry in commitments["breached_commitments"]) or "none broken"
    columns[3].metric("Commitment payments", aud(commitments["commitment_total_aud"]), help=broken)
    columns[4].metric("Effort", f"{effort['effort_needed_hours']} h",
                      help="worked by a senior payroll officer" if effort["senior_review_required"] else
                      f"under {config.SENIOR_REVIEW_THRESHOLD_HOURS} hours")

    pay_tab, employee_tab, notes_tab, assess_tab = st.tabs(["Pay owed", "Employee and hours", "Notes and models", "Assess"])

    with pay_tab:
        caption("The period is split wherever the classification owed or its rate changes. Each piece is paid at its own "
                "rates; the pieces are added exactly and rounded once.")
        st.dataframe(pd.DataFrame([{
            "From": piece["first_day"], "To": piece["last_day"], "Days": piece["days"],
            "Classification owed": piece["classification"],
            "Hours": piece.get("hours") if piece.get("hours") is not None else
            f"day {piece.get('day_hours')} / night {piece.get('night_hours')}",
            "Hourly rate": describe_rates(piece["rate_window"]),
            "Site allowance": f"AUD {piece['rate_window']['site_allowance_aud']} a day",
            "Pay": f"AUD {piece['pay_aud']}",
        } for piece in pieces]), hide_index=True, width="stretch")
        if comparison["correction_warranted"]:
            st.warning(f"A correction is warranted: the pay is out by AUD {comparison['money_at_stake_aud']} "
                       f"({comparison['direction'].lower()}), at or over the AUD {config.CORRECTION_THRESHOLD_AUD} line.")
        else:
            st.info(f"No correction is warranted: the difference is under AUD {config.CORRECTION_THRESHOLD_AUD}.")
        st.subheader("Pay schedules read")
        for classification, schedule in pay["pay_schedules"].items():
            with st.container(border=True):
                st.markdown(f"**{classification}** · {config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION[classification]}")
                for window in schedule["rate_windows"]:
                    st.markdown(f"- from {window['opens_on']}: {describe_rates(window)}, site allowance "
                                f"AUD {window['site_allowance_aud']} a day")
                st.caption("No traineeship." if schedule["moves_onto"] is None else
                           f"When the traineeship ends the employee moves to {schedule['moves_onto']}.")
        st.subheader("Payroll commitments")
        if commitments["breached_commitments"]:
            for entry in commitments["breached_commitments"]:
                st.markdown(f"- **{entry['commitment_code']}** broken: AUD {entry['payment_aud']}, as read from "
                            f"{config.COMMITMENTS_DOCUMENT}")
        else:
            st.caption("The record shows no commitment broken.")

    with employee_tab:
        hours = pay["hours"]
        measured = ", ".join(f"{key.replace('_', ' ')} {value}" for key, value in hours.items())
        key_values([
            ("Classification paid", profile[config.PAID_CLASSIFICATION_COLUMN]),
            ("Classification entitled to", profile[config.ENTITLED_CLASSIFICATION_COLUMN]),
            ("Traineeship's last day", profile.get(config.TRAINEESHIP_LAST_DAY_COLUMN) or "none this financial year"),
            ("Paid", f"{profile['pay_frequency']} by {profile['payment_method']}"),
            ("Period", f"{profile[config.PERIOD_START_COLUMN]} to {profile[config.PERIOD_END_COLUMN]}, "
                       f"{profile[config.DAYS_IN_PERIOD_COLUMN]} days"),
            ("Interpreter needed", profile[config.INTERPRETER_COLUMN]),
            ("Venue transfer", profile["venue_transfer_flag"]),
            ("Contact channel", profile["contact_channel"]),
            ("Hours paid", f"{profile[config.TOTAL_HOURS_COLUMN]} from {profile['hours_source_type']}"),
            ("Verified hours", f"{profile[config.VERIFIED_ORDINARY_HOURS_COLUMN]}"
                               + (f" day, {profile[config.VERIFIED_NIGHT_HOURS_COLUMN]} night"
                                  if profile.get(config.VERIFIED_NIGHT_HOURS_COLUMN) else "")
                               + f" from {profile[config.VERIFIED_HOURS_SOURCE_COLUMN]}"),
            ("Measured", measured),
        ])

    with notes_tab:
        left, right = st.columns([3, 2])
        with left:
            st.markdown(f"**Category:** {category['query_category']}  ·  agreement {category['agreement']:.0%}  ·  "
                        f"{category['notes_read']} read, {category['notes_too_short_to_read']} too short")
            if category["other_categories"]:
                st.caption("Other categories named: " + ", ".join(category["other_categories"]))
            for number, text in enumerate(detail["note_texts"], 1):
                st.markdown(f'<div class="fp-card"><b>Note {number}</b><br>{text}</div>', unsafe_allow_html=True)
        with right:
            st.markdown("**Correction score**")
            st.progress(float(correction["correction_probability"]),
                        text=f"{correction['correction_probability']:.2f} · {correction['correction_band']}")
            st.markdown("**Effort**")
            basis = (f"{effort['base_hours']} h × {config.INTERPRETER_EFFORT_MULTIPLIER} for an interpreter"
                     if effort["multiplier_applied"] else f"{effort['base_hours']} h, no interpreter multiplier")
            st.markdown(f"{effort['effort_needed_hours']} hours ({basis}). Senior payroll officer: "
                        f"{_yes_no(effort['senior_review_required'])}.")
            with st.expander("Planning assumptions"):
                st.json(effort["planning_assumptions"])

    with assess_tab:
        caption("Five agents read the facts above and write an assessment. Nothing is paid and no one is written to: "
                f"the run stops for a {config.ROLE_CONTROLLER} other than you.")
        with st.form("assess_form"):
            request_text = st.text_area("What do you want looked at?", height=110,
                                        placeholder="For example: check the traineeship hand-over and the rate rise.")
            submitted = st.form_submit_button("Start the assessment", type="primary")
        if submitted:
            trimmed = request_text.strip()
            if len(trimmed) < config.ANALYST_REQUEST_MINIMUM_CHARACTERS:
                st.error(f"Say what you want looked at in at least {config.ANALYST_REQUEST_MINIMUM_CHARACTERS} characters.")
            else:
                record = call_service("POST", "/assessments", None,
                                      {"query_reference": reference, "analyst_request": trimmed},
                                      "Five agents are assessing the pay query.")
                st.success(f"Assessment {record['assessment_id']} is waiting for the {config.ROLE_CONTROLLER}. "
                           f"Recommended: {record['recommended_decision']}.")
                st.markdown(record["assessment_text"])
