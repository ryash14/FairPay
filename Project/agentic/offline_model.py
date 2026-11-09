"""A deterministic stand-in for Gemini, for rehearsals and demos without a key.

Switched on only by FAIRPAY_OFFLINE_LLM=1 in the environment; with it unset the
project calls Gemini exactly as the SRS requires. The rehearsal model follows
the same rule as the real agents: it only quotes facts that are already in the
prompt and never works out a figure.
"""
import re

from config import config


def _line(prompt, prefix):
    for line in prompt.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def _section(prompt, heading):
    lines, inside = [], False
    for line in prompt.splitlines():
        if line.strip() == heading:
            inside = True
            continue
        if inside:
            if not line.strip() or (line.isupper() and len(line) > 3 and ":" not in line):
                break
            lines.append(line)
    return lines


def _reference(prompt):
    match = re.search(config.QUERY_REFERENCE_PATTERN, prompt)
    return match.group(0) if match else "the query"


def _planner(prompt):
    rostered = "came from: Rostered" in prompt
    trainee = "none inside this financial year" not in prompt
    checks = ["Confirm the verified hours against the hours paid for every day of the period"]
    if trainee:
        checks.insert(0, "Confirm the traineeship's last day and the classification owed from the next day")
    if rostered:
        checks.insert(0, "Establish why the period was paid from the roster rather than the time clock")
    checks += ["Check every rate window that opens inside the period", "Check which payroll commitments the record shows broken"]
    checks = checks[:4]
    return "\n".join([
        "PRIORITY: " + ("High, money may be owed on hours" if rostered else "Standard review of the period"),
        "CHECKS:", *[f"{n}. {c}" for n, c in enumerate(checks, 1)],
        "RATIONALE: These checks settle what the employee was owed on each day. The pay owed, not the score, decides the outcome.",
    ])


def _correction(prompt):
    band = _line(prompt, "Correction probability:")
    source = re.search(r"hours paid came from: (\w[\w ]*)", prompt)
    source_text = source.group(1) if source else "the payslip"
    return "\n".join([
        "DRIVERS:",
        f"1. The hours paid came from {source_text.lower()}.",
        "2. " + _line(prompt, "Rostered periods in a row:").split(";")[0] + " rostered periods in a row.",
        "3. Classification and rate changes inside the period: " + _line(prompt, "Classification changes in the period:")[:60] + ".",
        f"HOURS: The pay was worked from {source_text.lower()} records. The verified hours are what the pay owed is built from.",
        f"CORRECTION SUMMARY: The model gives {band}. This is a prediction from the period's facts. "
        "The pay owed decides whether the pay was wrong.",
    ])


def _category(prompt):
    named = re.search(r"Category named: (.+?), with agreement ([\d.]+)", prompt)
    category, agreement = (named.group(1), float(named.group(2))) if named else ("Not established", 0.0)
    strength = "Strong" if agreement >= 0.75 else "Moderate" if agreement >= 0.5 else "Weak"
    if agreement < 0.5:
        category = "Not established"
    return "\n".join([
        f"QUERY CATEGORY: {category}",
        f"CONFIDENCE: {strength}. The notes agree at {agreement}.",
        "EVIDENCE: The category model read the notes in the order they were written. "
        + ("Most of them describe the same problem." if agreement >= 0.5 else "They disagree, so the category is not settled."),
    ])


def _pay_rate(prompt):
    pieces = [line for line in prompt.splitlines() if line.startswith("Piece ")]
    paid = re.search(r"Classification paid: ([^;]+);", prompt)
    commitments = [line for line in _section(prompt, "PAYROLL COMMITMENTS") if line.startswith("PC")]
    return "\n".join([
        "CLASSIFICATIONS OWED:", *pieces, f"Classification paid: {paid.group(1) if paid else 'as recorded'}",
        f"PAY CHECK: The pay owed is AUD {_line(prompt, 'Pay owed: AUD').split(' ')[0]} against AUD "
        f"{_line(prompt, 'Amount paid: AUD')} paid. The difference is AUD {_line(prompt, 'Difference: AUD')}.",
        "COMMITMENTS:", *(commitments or ["None"]),
    ])


def _writer(prompt):
    warranted = "A correction is warranted: yes" in prompt
    broken = "Commitment payments in total:" in prompt
    decision = (config.DECISION_CORRECT_AND_COMPENSATE if warranted and broken else
                config.DECISION_CORRECT_PAY if warranted else config.DECISION_UPHOLD_PAY)
    difference = _line(prompt, "Difference: AUD")
    owed = _line(prompt, "Pay owed: AUD").split(" ")[0]
    paid = _line(prompt, "Amount paid: AUD")
    reason = {
        config.DECISION_UPHOLD_PAY: "the difference is under the AUD 1.00 line, so correcting and compensating do not apply",
        config.DECISION_CORRECT_PAY: "the difference reaches the line but no commitment was broken, so upholding and "
                                     "compensating do not fit",
        config.DECISION_CORRECT_AND_COMPENSATE: "the difference reaches the line and a commitment was broken, so upholding "
                                                "and a correction alone fall short",
    }[decision]
    return "\n".join([
        f"ASSESSMENT: {_reference(prompt)} was rebuilt from the verified hours on the classification owed. "
        f"The pay owed is AUD {owed} against AUD {paid} paid, a difference of AUD {difference}. "
        "Every rate came from the classification's own schedule. "
        f"{decision} fits because {reason}.",
        f"RECOMMENDED DECISION: {decision}",
    ])


def _letter(prompt):
    reference = _reference(prompt)
    payments = [line for line in prompt.splitlines() if line.startswith("Commitment not kept:")]
    total = _line(prompt, "Total commitment payment:")
    sentences = [f"We have finished looking at your pay query {reference}.", "We are sorry that your pay was not right.",
                 "We have worked out your pay again for the period."]
    if payments:
        sentences.append(f"Because we did not keep one of our payroll commitments, we will pay you AUD {total.split(',')[0].replace('AUD ', '')}.")
        sentences.append("This is paid with your next pay run.")
    sentences += ["A pay correction statement will follow separately with the details.",
                  "If anything still looks wrong, contact us through the HR portal or speak to your venue manager.",
                  "Thank you for raising this with us."]
    return f"SUBJECT: Your pay query {reference}\nLETTER: " + " ".join(sentences)


def _statement(prompt):
    pieces = [line for line in _section(prompt, "THE PIECES") if line.startswith("Piece ")]
    totals = _section(prompt, "THE TOTALS")
    commitments = _section(prompt, "COMMITMENT PAYMENTS")
    settlement = _section(prompt, "THE SETTLEMENT")
    return "\n".join(["PIECES:", *pieces, "TOTALS:", *totals, "COMMITMENTS:",
                      *([c for c in commitments if "remediation letter" not in c] or ["None"]),
                      "SETTLEMENT: " + (settlement[0] if settlement else "None")])


RATE_WORDS = ("rate", "per hour", "an hour", "allowance", "traineeship", "trainee", "moves")
RULE_WORDS = ("who decides", "approve", "decide", "worked out", "commitment", "statement", "letter", "policy",
              "outcome", "correct", "service desk", "financial year", "rounded", "threshold")
ADVICE_WORDS = ("what should", "what can", "employee do", "steps", "badge", "timesheet", "clock", "payslip", "venue")


def _assistant(prompt):
    question = _section(prompt, "THE QUESTION")
    question_text = " ".join(question).lower()
    reference = re.search(config.QUERY_REFERENCE_PATTERN, " ".join(question).upper())
    passages = [line for line in _section(prompt, "PASSAGES FOUND IN THE DOCUMENTS") if not line.startswith("[Source:")]
    if reference:
        kind = config.CHAT_TYPE_QUERY_STATUS
    elif any(word in question_text for word in RATE_WORDS):
        kind = config.CHAT_TYPE_PAY_RATES
    elif any(word in question_text for word in RULE_WORDS):
        kind = config.CHAT_TYPE_PAYROLL_RULES
    elif any(word in question_text for word in ADVICE_WORDS):
        kind = config.CHAT_TYPE_EMPLOYEE_ADVICE
    else:
        kind = config.CHAT_TYPE_OUT_OF_SCOPE
    answer = "none"
    if kind in config.CHAT_ANSWERED_TYPES:
        schedules = [line for line in _section(prompt, "THE PUBLISHED PAY SCHEDULES, EACH IN FULL")]
        source = passages
        if kind == config.CHAT_TYPE_PAY_RATES:
            classification = next((c for c in sorted(config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION, key=len, reverse=True)
                                   if c.lower() in question_text), None)
            if classification:
                document = config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION[classification]
                own, keep = [], False
                for line in schedules:
                    if line.startswith("[Source:"):
                        keep = document in line
                        continue
                    if keep:
                        own.append(line)
                source = own or passages
        sentences = re.split(r"(?<=[.])\s+", " ".join(source))
        picked = [s for s in sentences if re.search(r"\$\d|rate|decide|commitment|portal|clock|traineeship|pay", s)][:3]
        answer = " ".join(picked or sentences[:2]).replace("$", "AUD ")
    return "\n".join([f"QUESTION TYPE: {kind}", f"QUERY REFERENCE: {reference.group(0) if reference else 'none'}",
                      f"ANSWER: {answer}"])


HANDLERS = {
    config.AGENT_NAME_PLANNER: _planner, config.AGENT_NAME_CORRECTION: _correction,
    config.AGENT_NAME_CATEGORY: _category, config.AGENT_NAME_PAY_RATE: _pay_rate,
    config.AGENT_NAME_WRITER: _writer, config.AGENT_NAME_REMEDIATION_LETTER: _letter,
    config.AGENT_NAME_PAY_STATEMENT: _statement, config.AGENT_NAME_PAYROLL_ASSISTANT: _assistant,
}


def rehearse(prompt_text, agent_name):
    return HANDLERS[agent_name](prompt_text)
