"""The language model client, the reply parser, the describing helpers and the seven prompts.

Every agent is handed facts the models, documents and pay tools already
established, and asked for prose in a fixed layout of labelled fields. No
agent calculates anything.
"""
import math
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import config

load_dotenv()

generation_settings = types.GenerateContentConfig(
    max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
    temperature=config.GEMINI_TEMPERATURE,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)

LAYOUT_CLOSE = "Reply in exactly this layout and nothing else."
OFFLINE_SWITCH = "FAIRPAY_OFFLINE_LLM"


# ================================================================= model call
def call_language_model(prompt_text, agent_name):
    """One call to Gemini; returns the stripped reply and what the call cost."""
    if os.getenv(OFFLINE_SWITCH) == "1":
        from agentic.offline_model import rehearse
        started = time.perf_counter()
        reply = rehearse(prompt_text, agent_name).strip()
        return {"response_text": reply, "call_record": {
            "agent_name": agent_name, "model_name": "offline-rehearsal", "prompt_characters": len(prompt_text),
            "response_characters": len(reply),
            "latency_milliseconds": int(round((time.perf_counter() - started) * 1000))}}

    api_key = os.getenv(config.GEMINI_API_KEY_VARIABLE)
    model_name = os.getenv(config.GEMINI_MODEL_VARIABLE)
    if not api_key or not model_name:
        raise ValueError(f"{config.GEMINI_API_KEY_VARIABLE} and {config.GEMINI_MODEL_VARIABLE} must both be set in .env")
    started = time.perf_counter()
    with genai.Client(api_key=api_key) as client:
        response = client.models.generate_content(model=model_name, contents=prompt_text, config=generation_settings)
    elapsed = int(round((time.perf_counter() - started) * 1000))
    text = response.text if response is not None else None
    if not text or not text.strip():
        raise ValueError(f"{agent_name} received an empty reply from {model_name}")
    finish_reason = response.candidates[0].finish_reason if response.candidates else None
    if finish_reason != types.FinishReason.STOP:
        raise ValueError(f"{agent_name} reply from {model_name} did not finish normally: {finish_reason}")
    reply = text.strip()
    return {"response_text": reply, "call_record": {
        "agent_name": agent_name, "model_name": model_name, "prompt_characters": len(prompt_text),
        "response_characters": len(reply), "latency_milliseconds": elapsed}}


# ================================================================= reply parser
def parse_labelled_response(response_text, field_labels, agent_name):
    """Read a labelled reply back into exactly the fields asked for, whatever decoration the model added."""
    decoration = config.RESPONSE_DECORATION_CHARACTERS
    wanted = [label.upper() for label in field_labels]
    fields, current = {}, None
    for raw_line in response_text.splitlines():
        line = raw_line.strip().replace("**", "")
        if not line:
            continue
        lead_stripped = line.lstrip(decoration)
        if ":" in lead_stripped:
            before, after = lead_stripped.split(":", 1)
            label = before.strip(decoration).upper()
            if label in wanted:
                value = after.strip(decoration)
                if fields.get(label):
                    if value:
                        fields[label] = fields[label] + "\n" + value
                else:
                    fields[label] = value
                current = label
                continue
        if current is not None:
            fields[current] = f"{fields[current]}\n{line}" if fields.get(current) else line
    missing = [label for label in wanted if not (fields.get(label) or "").strip()]
    if missing:
        raise ValueError(f"{agent_name} replied without {', '.join(missing)}")
    return {label: fields[label].strip() for label in wanted}


# ================================================================= describing helpers
def _missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        import pandas as pd
        return bool(pd.isna(value)) if not isinstance(value, (list, dict)) else False
    except (TypeError, ValueError):
        return False


def _yes_no(value):
    return config.BOOLEAN_LABELS.get(value, value)


def describe_paid_hours(query_profile):
    if query_profile[config.ROSTER_TYPE_COLUMN] == config.DAY_NIGHT_ROSTER_TYPE:
        return (f"day {query_profile[config.ORDINARY_HOURS_COLUMN]} hours and night "
                f"{query_profile[config.NIGHT_HOURS_COLUMN]} hours, {query_profile[config.TOTAL_HOURS_COLUMN]} hours in all")
    return f"{query_profile[config.TOTAL_HOURS_COLUMN]} hours"


def describe_verified_hours(query_profile):
    if query_profile[config.ROSTER_TYPE_COLUMN] == config.DAY_NIGHT_ROSTER_TYPE:
        return (f"day {query_profile[config.VERIFIED_ORDINARY_HOURS_COLUMN]} hours and night "
                f"{query_profile[config.VERIFIED_NIGHT_HOURS_COLUMN]} hours")
    return f"{query_profile[config.VERIFIED_ORDINARY_HOURS_COLUMN]} hours"


def describe_traineeship_last_day(query_profile):
    value = query_profile.get(config.TRAINEESHIP_LAST_DAY_COLUMN)
    return "none inside this financial year" if _missing(value) else str(value)


def describe_hours_change(query_profile):
    value = query_profile.get("hours_change_vs_average_pct")
    return "not known, the employee has under six months' service" if _missing(value) else f"{value}%"


def describe_overrun(query_profile):
    value = query_profile.get("traineeship_days_overrun")
    if _missing(value):
        return "no traineeship ended inside the period"
    return f"{value} days paid at the trainee rate after the traineeship ended"


def describe_salary_packaging(query_profile):
    value = query_profile.get("salary_packaging_aud")
    return "none" if _missing(value) else f"AUD {value} a period"


def describe_recovery_balance(query_profile):
    value = query_profile.get("recovery_balance_aud")
    if _missing(value):
        return "none"
    text = str(value)
    if text.startswith("-"):
        return f"AUD {text[1:]} owed to the employee"
    return f"AUD {text} being recovered from the employee"


def describe_rate_window(rate_window):
    if "night_rate_aud" in rate_window:
        hourly = (f"day rate AUD {rate_window['day_rate_aud']} per hour and night rate AUD "
                  f"{rate_window['night_rate_aud']} per hour")
    else:
        hourly = f"ordinary rate AUD {rate_window['ordinary_rate_aud']} per hour"
    return f"from {rate_window['opens_on']}: {hourly}, site allowance AUD {rate_window['site_allowance_aud']} per day"


def describe_pay_piece(pay_piece):
    window = pay_piece["rate_window"]
    opening = f"{pay_piece['first_day']} to {pay_piece['last_day']}, {pay_piece['days']} days on " \
              f"{pay_piece['classification']} at the rates from {window['opens_on']}"
    if "night_rate_aud" in window:
        hours = (f"{pay_piece['day_hours']} day hours at AUD {window['day_rate_aud']} per hour and "
                 f"{pay_piece['night_hours']} night hours at AUD {window['night_rate_aud']} per hour")
    else:
        hours = f"{pay_piece['hours']} hours at AUD {window['ordinary_rate_aud']} per hour"
    return f"{opening}: {hours}, site allowance AUD {window['site_allowance_aud']} per day; piece pay AUD {pay_piece['pay_aud']}"


# ================================================================= shared prompt parts
def _employee_facts(query_profile, with_system=False):
    p = query_profile
    lines = [
        f"Reference: {p[config.QUERY_REFERENCE_COLUMN]}",
        f"Employee: {p['employee_number']}, {p[config.PAYROLL_CENTRE_COLUMN]} payroll centre, raised by "
        f"{p.get('contact_channel', 'unknown channel')}",
    ]
    if with_system:
        lines.append(f"Payroll system: {p[config.PAYROLL_SYSTEM_COLUMN]}")
    lines += [
        f"Period: {p[config.PERIOD_START_COLUMN]} to {p[config.PERIOD_END_COLUMN]}, {p[config.DAYS_IN_PERIOD_COLUMN]} days, "
        f"paid {p['pay_frequency']}",
        f"Amount paid: AUD {p[config.AMOUNT_PAID_COLUMN]}; hours paid: {describe_paid_hours(p)}",
        f"Classification paid: {p[config.PAID_CLASSIFICATION_COLUMN]}; classification owed on the first day: "
        f"{p[config.ENTITLED_CLASSIFICATION_COLUMN]}; traineeship's last day: {describe_traineeship_last_day(p)}",
        f"Roster: {p[config.ROSTER_TYPE_COLUMN]}; electronic timesheet: {_yes_no(p['electronic_timesheet_flag'])}; "
        f"hours paid came from: {p['hours_source_type']}",
        f"Verified hours: {describe_verified_hours(p)}, from {p[config.VERIFIED_HOURS_SOURCE_COLUMN]}",
        f"Rostered periods in a row: {p['consecutive_rostered_periods']}; days since the last clock match: "
        f"{p['days_since_last_clock_match']}",
        f"Contracted hours a week: {p[config.CONTRACTED_HOURS_COLUMN]}; hours against the employee's average: "
        f"{describe_hours_change(p)}",
        f"Classification changes in the period: {p['classification_changes_in_period']}; rate changes in the period: "
        f"{p['rate_changes_in_period']}; overrun: {describe_overrun(p)}",
        f"Prior queries in twelve months: {p['prior_queries_12m']}; service: {p['tenure_months']} months",
        f"Payment method: {p['payment_method']}; salary packaging: {describe_salary_packaging(p)}; recovery balance: "
        f"{describe_recovery_balance(p)}",
        f"Venue transfer: {_yes_no(p['venue_transfer_flag'])}; interpreter needed: {_yes_no(p[config.INTERPRETER_COLUMN])}",
    ]
    return lines


def _commitment_flags(query_profile):
    return [f"{code} ({config.COMMITMENT_BREACH_PHRASES[code]}): {_yes_no(query_profile.get(column))}"
            for code, column in config.COMMITMENT_BREACH_COLUMNS.items()]


def _layout(*fields):
    return "\n".join(["", "REPLY LAYOUT", *[f"{label}: {guide}" for label, guide in fields], "", LAYOUT_CLOSE])


def _call(prompt, agent_name, labels):
    reply = call_language_model(prompt, agent_name)
    return parse_labelled_response(reply["response_text"], labels, agent_name), reply["call_record"]


def _comparison_lines(comparison):
    return [
        f"Pay owed: AUD {comparison['entitled_pay_aud']} (the pieces added together and rounded once to the cent)",
        f"Amount paid: AUD {comparison['amount_paid_aud']}",
        f"Difference: AUD {comparison['difference_aud']}, {comparison['direction']}",
        f"A correction is warranted: {'yes' if comparison['correction_warranted'] else 'no'} (the line is AUD "
        f"{config.CORRECTION_THRESHOLD_AUD} either way)",
    ]


def _commitment_lines(commitments):
    if not commitments["breached_commitments"]:
        return ["Commitments broken: None"]
    lines = [f"{entry['commitment_code']} ({config.COMMITMENT_BREACH_PHRASES[entry['commitment_code']]}): payment AUD "
             f"{entry['payment_aud']}, read from {config.COMMITMENTS_DOCUMENT}" for entry in commitments["breached_commitments"]]
    return lines + [f"Commitment payments in total: AUD {commitments['commitment_total_aud']}"]


# ================================================================= the seven agents
def plan_assessment(query_profile, analyst_request):
    prompt = "\n".join([
        f"You are a Payroll Analyst at {config.ORGANISATION_NAME}, planning the assessment of one pay query.",
        "Decide what has to be established before anyone can decide anything. You plan; you settle nothing.",
        "", "THE QUERY", *_employee_facts(query_profile),
        "", "PAYROLL COMMITMENTS THE RECORD FLAGS", *_commitment_flags(query_profile),
        "", "WHAT THE ANALYST ASKED", analyst_request,
        _layout(("PRIORITY", "one short phrase"),
                ("CHECKS", "three to five numbered things to establish, most important first"),
                ("RATIONALE", "two sentences on why those checks")),
    ])
    plan, record = _call(prompt, config.AGENT_NAME_PLANNER, ["PRIORITY", "CHECKS", "RATIONALE"])
    return {"assessment_plan": plan, "call_record": record}


def assess_correction_risk(correction_facts, query_profile, assessment_plan):
    prompt = "\n".join([
        f"You are the correction risk analyst at {config.ORGANISATION_NAME}'s payroll remediation desk.",
        "Explain what is driving this query's correction score so a Remediation Controller can act on it.",
        "Do not recalculate or invent any figure. The score is a prediction from the period's facts; it does not say "
        "whether the pay was wrong. The pay owed settles that.",
        "", "THE SCORE",
        f"Correction probability: {correction_facts['correction_probability']}; band: {correction_facts['correction_band']}",
        f"Bands: High at or above {config.CORRECTION_BAND_HIGH_THRESHOLD:.2f}, Medium at or above "
        f"{config.CORRECTION_BAND_MEDIUM_THRESHOLD:.2f}, otherwise Low",
        "", "THE QUERY", *_employee_facts(query_profile, with_system=True),
        "", "THE PLAN'S CHECKS", assessment_plan["CHECKS"],
        _layout(("DRIVERS", "the three facts most responsible for the score, numbered"),
                ("HOURS", "two sentences on whether the hours behind the pay were clocked, written on a timesheet or "
                          "taken from the roster"),
                ("CORRECTION SUMMARY", "three sentences a Remediation Controller could read on their own")),
    ])
    fields, record = _call(prompt, config.AGENT_NAME_CORRECTION, ["DRIVERS", "HOURS", "CORRECTION SUMMARY"])
    return {"correction_assessment": fields, "call_record": record}


def identify_category(category_facts, query_profile, assessment_plan, correction_assessment):
    p = query_profile
    note_lines = [f"Note {number}: {category}" for number, category in enumerate(category_facts["note_categories"], 1)]
    prompt = "\n".join([
        f"You are the category analyst at {config.ORGANISATION_NAME}'s payroll remediation desk.",
        "Say how much weight the category the employee notes name deserves.",
        "Agreement below about half means the notes disagree; if so, say so rather than present the category as settled.",
        "", "WHAT THE CATEGORY MODEL READ",
        f"Notes read: {category_facts['notes_read']}; set aside as too short: {category_facts['notes_too_short_to_read']}",
        *note_lines,
        f"Category named: {category_facts['query_category']}, with agreement {category_facts['agreement']} "
        f"(the share of the notes read that name it)",
        f"Other categories named: {', '.join(category_facts['other_categories']) or 'none'}",
        "", "THE QUERY",
        f"Classification paid: {p[config.PAID_CLASSIFICATION_COLUMN]}; owed: {p[config.ENTITLED_CLASSIFICATION_COLUMN]}; "
        f"traineeship's last day: {describe_traineeship_last_day(p)}",
        f"Hours source: {p['hours_source_type']}; verified hours source: {p[config.VERIFIED_HOURS_SOURCE_COLUMN]}; roster: "
        f"{p[config.ROSTER_TYPE_COLUMN]}; electronic timesheet: {_yes_no(p['electronic_timesheet_flag'])}",
        f"Venue transfer: {_yes_no(p['venue_transfer_flag'])}; payment method: {p['payment_method']}",
        "", "THE PLAN'S CHECKS", assessment_plan["CHECKS"],
        "", "CORRECTION SUMMARY", correction_assessment["CORRECTION SUMMARY"],
        "", "THE CATEGORIES", ", ".join(config.QUERY_CATEGORIES),
        _layout(("QUERY CATEGORY", "one listed category, or Not established"),
                ("CONFIDENCE", "Strong, Moderate or Weak, with one sentence why"),
                ("EVIDENCE", "two to four sentences")),
    ])
    fields, record = _call(prompt, config.AGENT_NAME_CATEGORY, ["QUERY CATEGORY", "CONFIDENCE", "EVIDENCE"])
    return {"category_analysis": fields, "call_record": record}


def advise_on_pay_rates(pay_facts, query_profile, assessment_plan):
    p = query_profile
    schedule_lines = []
    for classification, schedule in pay_facts["pay_schedules"].items():
        schedule_lines.append(f"{classification} ({config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION[classification]}):")
        schedule_lines += [f"  {describe_rate_window(window)}" for window in schedule["rate_windows"]]
        schedule_lines.append("  no traineeship" if schedule["moves_onto"] is None else
                              f"  when the traineeship ends the employee moves onto {schedule['moves_onto']}")
    hours = pay_facts["hours"]
    hours_text = ", ".join(f"{key.replace('_', ' ')} {value}" for key, value in hours.items())
    prompt = "\n".join([
        f"You are the pay rate advisor at {config.ORGANISATION_NAME}'s payroll remediation desk.",
        "State which classification was owed on which days, at which rates, and whether the pay was right.",
        "Quote every figure exactly as given. Never recalculate or derive a figure, and never apply one classification's "
        "rates to another classification's days.",
        "", "THE QUERY",
        f"Reference: {p[config.QUERY_REFERENCE_COLUMN]}",
        f"Classification paid: {p[config.PAID_CLASSIFICATION_COLUMN]}; owed on the first day: "
        f"{p[config.ENTITLED_CLASSIFICATION_COLUMN]}; traineeship's last day: {describe_traineeship_last_day(p)}",
        f"Period: {p[config.PERIOD_START_COLUMN]} to {p[config.PERIOD_END_COLUMN]}; amount paid AUD {p[config.AMOUNT_PAID_COLUMN]}",
        "", "THE PAY SCHEDULES READ", *schedule_lines,
        "", "THE HOURS", f"Measured: {hours_text}, verified from {p[config.VERIFIED_HOURS_SOURCE_COLUMN]}",
        "", "THE PIECES", *[f"Piece {n}: {describe_pay_piece(piece)}" for n, piece in enumerate(pay_facts["pieces"], 1)],
        "", "THE COMPARISON", *_comparison_lines(pay_facts["comparison"]),
        "", "PAYROLL COMMITMENTS", *_commitment_lines(pay_facts["commitments"]),
        "", "THE PLAN'S CHECKS", assessment_plan["CHECKS"],
        _layout(("CLASSIFICATIONS OWED", "each piece on its own line with its dates, classification and rates, then a "
                                         "line naming the classification paid"),
                ("PAY CHECK", "two sentences quoting the pay owed, the amount paid and the difference"),
                ("COMMITMENTS", "one broken commitment and its payment per line, or None")),
    ])
    fields, record = _call(prompt, config.AGENT_NAME_PAY_RATE, ["CLASSIFICATIONS OWED", "PAY CHECK", "COMMITMENTS"])
    return {"pay_rate_advice": fields, "call_record": record}


def write_query_assessment(query_profile, analyst_request, correction_facts, pay_facts, effort_facts,
                           correction_assessment, category_analysis, pay_rate_advice):
    p = query_profile
    effort_basis = (f"base {effort_facts['base_hours']} hours times {config.INTERPRETER_EFFORT_MULTIPLIER} because an "
                    f"interpreter is needed" if effort_facts["multiplier_applied"] else
                    f"base {effort_facts['base_hours']} hours, no interpreter")
    prompt = "\n".join([
        f"You write the assessment a Remediation Controller at {config.ORGANISATION_NAME} decides a pay query from.",
        "You recommend; you do not decide. Say what went wrong only from the facts given, quote every figure exactly, "
        "and answer what the analyst asked.",
        "", "THE QUERY",
        f"Reference {p[config.QUERY_REFERENCE_COLUMN]}, {p[config.PAYROLL_CENTRE_COLUMN]} payroll centre, period "
        f"{p[config.PERIOD_START_COLUMN]} to {p[config.PERIOD_END_COLUMN]}",
        f"Hours paid: {describe_paid_hours(p)}; verified hours: {describe_verified_hours(p)}",
        "", "WHAT THE ANALYST ASKED", analyst_request,
        "", "CORRECTION RISK ANALYST", *[f"{label}: {text}" for label, text in correction_assessment.items()],
        "", "CATEGORY ANALYST", *[f"{label}: {text}" for label, text in category_analysis.items()],
        "", "PAY RATE ADVISOR", *[f"{label}: {text}" for label, text in pay_rate_advice.items()],
        "", "THE NUMBERS",
        f"Correction probability {correction_facts['correction_probability']}, band {correction_facts['correction_band']}",
        *_comparison_lines(pay_facts["comparison"]),
        *_commitment_lines(pay_facts["commitments"]),
        f"Effort: {effort_facts['effort_needed_hours']} hours ({effort_basis}); a senior payroll officer is needed: "
        f"{'yes' if effort_facts['senior_review_required'] else 'no'} (the line is "
        f"{config.SENIOR_REVIEW_THRESHOLD_HOURS} hours)",
        "", "THE THREE OUTCOMES (PAY QUERY POLICY)",
        f"{config.DECISION_UPHOLD_PAY}: the pay stands and nothing is paid.",
        f"{config.DECISION_CORRECT_PAY}: a pay correction statement is issued for the difference.",
        f"{config.DECISION_CORRECT_AND_COMPENSATE}: the pay is corrected and the employee is also written to with an "
        f"apology and the Payroll Commitments payment, which is due only where a commitment was broken, whether "
        f"underpaid or overpaid, and is paid only with a correction.",
        f"Pay is corrected only when the difference reaches AUD {config.CORRECTION_THRESHOLD_AUD} either way.",
        _layout(("ASSESSMENT", "four to six sentences of prose, the last saying which outcome fits and why the other "
                               "two do not"),
                ("RECOMMENDED DECISION", f"exactly one of {', '.join(config.DECISION_OPTIONS)}")),
    ])
    fields, record = _call(prompt, config.AGENT_NAME_WRITER, ["ASSESSMENT", "RECOMMENDED DECISION"])
    first_line = fields["RECOMMENDED DECISION"].splitlines()[0]
    recommendation = first_line.strip(config.RESPONSE_DECORATION_CHARACTERS + ".").strip(
        config.RESPONSE_DECORATION_CHARACTERS + ".").upper()
    options = {option.upper(): option for option in config.DECISION_OPTIONS}
    if recommendation not in options:
        raise ValueError(f"{config.AGENT_NAME_WRITER} recommended '{first_line}', which is not one of "
                         f"{', '.join(config.DECISION_OPTIONS)}")
    fields["RECOMMENDED DECISION"] = options[recommendation]
    return {"query_assessment": fields, "call_record": record}


def draft_remediation_letter(query_profile, commitments, employee_steps):
    p = query_profile
    if commitments["breached_commitments"]:
        payment_lines = [f"Commitment not kept: {config.COMMITMENT_BREACH_PHRASES[entry['commitment_code']]}; payment "
                         f"AUD {entry['payment_aud']}" for entry in commitments["breached_commitments"]]
        payment_lines.append(f"Total commitment payment: AUD {commitments['commitment_total_aud']}, paid with the next pay "
                             f"run and shown on the pay correction statement")
    else:
        payment_lines = ["No payroll commitment was broken, so no payment is due under the Payroll Commitments."]
    prompt = "\n".join([
        f"You write to an employee of {config.ORGANISATION_NAME} about their pay query, a letter they will read at home.",
        "Follow the Pay Query Policy: plain words, short sentences, one apology. Say a pay correction statement follows "
        "separately and quote no amount from it. Where a commitment was broken the only figures are its payments; where "
        "none was, the letter contains no figures and never suggests a payment.",
        "Name no payroll system, member of staff, internal detail or identifier except the reference. Direct the employee "
        "to the HR portal or their venue manager. Invent no contact details.",
        "", "THE LETTER IS ABOUT",
        f"Reference to quote: {p[config.QUERY_REFERENCE_COLUMN]}",
        f"Period: {p[config.PERIOD_START_COLUMN]} to {p[config.PERIOD_END_COLUMN]}",
        f"Classification owed: {p[config.ENTITLED_CLASSIFICATION_COLUMN]}",
        *payment_lines,
        "", "STEPS FROM THE RESOLUTION GUIDE", *employee_steps,
        _layout(("SUBJECT", "one plain line"), ("LETTER", "six to ten short sentences")),
    ])
    fields, record = _call(prompt, config.AGENT_NAME_REMEDIATION_LETTER, ["SUBJECT", "LETTER"])
    return {"remediation_letter": fields, "call_record": record}


def _amount_pattern(amount_text):
    return r"(?<![\d.,])" + re.escape(amount_text) + r"(?!\d)(?!\.\d)"


def draft_pay_statement(query_profile, pay_facts, remediation_letter, settlement):
    p = query_profile
    comparison = pay_facts["comparison"]
    explained = ("paid to the employee" if comparison["direction"] == config.UNDERPAID else
                 "recovered from the employee" if comparison["direction"] == config.OVERPAID else "nothing to correct")
    if remediation_letter:
        commitments = pay_facts["commitments"]
        commitment_lines = _commitment_lines(commitments) if commitments["breached_commitments"] else \
            ["No commitment payment is due."]
        commitment_lines.append(f"A remediation letter was sent: {remediation_letter['SUBJECT']}")
    else:
        commitment_lines = ["No remediation letter was sent and no commitment payment is made."]
    prompt = "\n".join([
        f"You write the pay correction statement for an employee of {config.ORGANISATION_NAME}: the one place they are "
        f"given the corrected pay's figures.",
        "Show every piece once and in date order. Write every figure exactly as given, as AUD and the figure, with no "
        "dollar sign and no commas. Never recalculate, round or add a figure. Write each label once.",
        "", "THE STATEMENT",
        f"Reference: {p[config.QUERY_REFERENCE_COLUMN]}; employee: {p['employee_number']}",
        f"Period: {p[config.PERIOD_START_COLUMN]} to {p[config.PERIOD_END_COLUMN]}",
        f"Amount originally paid: AUD {comparison['amount_paid_aud']} as {p[config.PAID_CLASSIFICATION_COLUMN]}",
        "", "THE PIECES", *[f"Piece {n}: {describe_pay_piece(piece)}" for n, piece in enumerate(pay_facts["pieces"], 1)],
        "", "THE TOTALS",
        f"Pay owed: AUD {comparison['entitled_pay_aud']}; amount paid: AUD {comparison['amount_paid_aud']}",
        f"Correction: AUD {comparison['money_at_stake_aud']}, {comparison['direction']}, {explained}",
        "", "COMMITMENT PAYMENTS", *commitment_lines,
        "", "THE SETTLEMENT", f"AUD {settlement['amount_to_settle_aud']}, {settlement['direction']}",
        _layout(("PIECES", "one line per numbered piece"), ("TOTALS", "pay owed, amount paid and the correction"),
                ("COMMITMENTS", "each payment made and the total, or None"), ("SETTLEMENT", "the amount and its direction")),
    ])
    fields, record = _call(prompt, config.AGENT_NAME_PAY_STATEMENT, ["PIECES", "TOTALS", "COMMITMENTS", "SETTLEMENT"])
    expected = {}
    for piece in pay_facts["pieces"]:
        expected[str(piece["pay_aud"])] = expected.get(str(piece["pay_aud"]), 0) + 1
    miscounted = sorted(amount for amount, count in expected.items()
                        if len(re.findall(_amount_pattern(amount), fields["PIECES"])) != count)
    if miscounted:
        raise ValueError(f"{config.AGENT_NAME_PAY_STATEMENT} miscounted the piece amounts {', '.join(miscounted)}; the "
                         f"calculation has every piece once")
    return {"pay_statement": fields, "call_record": record}
