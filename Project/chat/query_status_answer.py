"""Answers a question about one named pay query from its stored record, as the asker's role allows."""
from config import config
from persistence import repository
from persistence.models import PayQuery
from tools.messages import fill_template


def _yes_no(flag):
    return config.BOOLEAN_LABELS[config.BOOLEAN_YES if flag else config.BOOLEAN_NO]


def answer_query_status(session, open_queries, role_name, query_reference):
    """Status and when it last changed for the service desk; every figure for the roles that may hear them."""
    nothing = {"source_documents": [], "was_refused": False}
    known = set(open_queries[config.QUERY_REFERENCE_COLUMN])
    if query_reference is None or query_reference not in known:
        return {"answer": config.CHAT_UNKNOWN_QUERY_MESSAGE, **nothing}
    figures = role_name in config.CHAT_FIGURE_ROLES
    records = repository.fetch_query_records(session, PayQuery.query_reference == query_reference)
    if not records:
        answer = fill_template(config.CHAT_NOT_ASSESSED_TEMPLATE, query_reference, query_reference=query_reference)
        if not figures:
            answer = f"{answer} {config.CHAT_AMOUNTS_IN_WRITING_MESSAGE}"
        return {"answer": answer, **nothing}
    record = records[0]
    if not figures:
        changed = record["decided_at"] if record["decided_at"] is not None else record["created_at"]
        changed_on = changed.strftime(config.STATUS_CHANGE_TIME_FORMAT)
        phrase = config.CHAT_STATUS_PHRASES[record["status"]]
        status = fill_template(config.CHAT_STATUS_TEMPLATE, query_reference, phrase, changed_on,
                               query_reference=query_reference, status_phrase=phrase, changed_on=changed_on)
        return {"answer": f"{status} {config.CHAT_AMOUNTS_IN_WRITING_MESSAGE}", **nothing}
    sentences = [
        f"{record['query_reference']}, {record['payroll_centre']} payroll centre: assessment {record['assessment_id']}, "
        f"status {record['status']}.",
        f"Paid AUD {record['amount_paid_aud']} as {record['paid_classification']}; pay owed AUD "
        f"{record['entitled_pay_aud']} on {record['classifications_owed']}; difference AUD {record['difference_aud']}, "
        f"{record['direction']}; a pay correction is warranted: {_yes_no(record['correction_warranted'])}.",
        f"Payroll commitments broken: {record['breached_commitments'] or 'none'}; commitment payments due AUD "
        f"{record['commitment_total_aud']}.",
        f"Correction probability {record['correction_probability']:.2f}, band {record['correction_band']}; category "
        f"{record['query_category']}, named by {round(record['category_agreement'] * 100)}% of the notes read.",
        f"Effort {record['effort_needed_hours']:.2f} hours; a senior payroll officer is needed: "
        f"{_yes_no(record['senior_review_required'])}.",
        f"The assessment recommended {record['recommended_decision']}.",
    ]
    if record["decision"] is not None:
        sentences.append(f"{record['decided_by']} ({record['decided_by_role']}) decided {record['decision']}: "
                         f"{record['decision_reason']}")
    if record["settled_amount_aud"] is not None:
        sentences.append(f"Settled amount AUD {record['settled_amount_aud']}, {record['settlement_direction']}.")
    return {"answer": " ".join(sentences), **nothing}
