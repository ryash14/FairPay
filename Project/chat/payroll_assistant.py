"""One question, one language model call, answered from the documents the chat may read and nothing else."""
import re

from agentic.agents import call_language_model, parse_labelled_response
from config import config
from knowledge.vector_index import read_document_chunks, search_documents

LABELS = ["QUESTION TYPE", "QUERY REFERENCE", "ANSWER"]


def _merge_nearest(result_lists):
    best = {}
    for results in result_lists:
        for passage in results:
            held = best.get(passage["chunk_id"])
            if held is None or passage["distance"] < held["distance"]:
                best[passage["chunk_id"]] = passage
    return sorted(best.values(), key=lambda passage: passage["distance"])


def answer_from_documents(collection, question_text, conversation):
    """Classify and answer in one call; refuse when the documents do not ground an answer."""
    searched = _merge_nearest(search_documents(collection, [question_text, conversation["search_text"]],
                                               config.CHAT_RETRIEVAL_RESULT_COUNT,
                                               {"$nin": list(config.CHAT_EXCLUDED_DOCUMENTS)}))
    schedules = {document: read_document_chunks(collection, document)
                 for document in config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION.values()}
    schedule_lines = []
    for document, chunks in schedules.items():
        for chunk in chunks:
            schedule_lines += [f"[Source: {document}]", chunk]
    passage_lines = []
    for passage in searched:
        passage_lines += [f"[Source: {passage['document_name']}]", passage["chunk_text"]]
    types_text = "\n".join([
        f"{config.CHAT_TYPE_PAY_RATES}: a published rate, a rate window, a site allowance, a traineeship or the "
        f"classification a trainee moves onto.",
        f"{config.CHAT_TYPE_PAYROLL_RULES}: how pay or a pay correction is worked out, how a query is handled, who "
        f"decides, what a statement or letter must show, what a payroll commitment promises.",
        f"{config.CHAT_TYPE_EMPLOYEE_ADVICE}: what an employee can do about hours, timesheets, payments or classifications.",
        f"{config.CHAT_TYPE_QUERY_STATUS}: where one named pay query has got to, or any figure of one query.",
        f"{config.CHAT_TYPE_OUT_OF_SCOPE}: anything the schedules and passages do not answer.",
    ])
    prompt = "\n".join([
        f"You are the payroll assistant at {config.ORGANISATION_NAME}, answering the payroll remediation desk and the HR "
        f"service desk from the organisation's own documents only.",
        "Answer only from the schedules and passages below. Choose OUT OF SCOPE rather than answer from general knowledge.",
        "Every rate belongs to the classification whose schedule states it: quote a rate only from that classification's "
        "own schedule and never give it for another.",
        "Write money as AUD followed by the figure, never with a currency symbol.",
        "You know nothing about any individual pay query: a question about one is QUERY STATUS and you do not answer it.",
        "", "QUESTION TYPES", types_text,
        "", "EARLIER IN THIS CONVERSATION", conversation["history_text"],
        "", "THE QUESTION", question_text,
        "", "THE PUBLISHED PAY SCHEDULES, EACH IN FULL", *schedule_lines,
        "", "PASSAGES FOUND IN THE DOCUMENTS", *passage_lines,
        "", "REPLY LAYOUT",
        f"QUESTION TYPE: one of {', '.join(config.CHAT_TYPE_OPTIONS)}",
        "QUERY REFERENCE: a reference such as PQR-SYD-0000000, or none",
        "ANSWER: two to five sentences from the schedules and passages for the three answerable types, otherwise none",
        "", "Reply in exactly this layout and nothing else.",
    ])
    reply = call_language_model(prompt, config.AGENT_NAME_PAYROLL_ASSISTANT)
    fields = parse_labelled_response(reply["response_text"], LABELS, config.AGENT_NAME_PAYROLL_ASSISTANT)

    first_line = fields["QUESTION TYPE"].splitlines()[0]
    question_type = first_line.strip(config.RESPONSE_DECORATION_CHARACTERS + ".").strip(
        config.RESPONSE_DECORATION_CHARACTERS + ".").upper()
    if question_type not in config.CHAT_TYPE_OPTIONS:
        raise ValueError(f"{config.AGENT_NAME_PAYROLL_ASSISTANT} classified the question as '{first_line}', which is "
                         f"not one of {', '.join(config.CHAT_TYPE_OPTIONS)}")
    match = re.search(config.QUERY_REFERENCE_PATTERN, fields["QUERY REFERENCE"].upper())
    query_reference = match.group(0) if match else None
    closest = float(searched[0]["distance"]) if searched else 1.0

    answered = question_type in config.CHAT_ANSWERED_TYPES and closest <= config.CHAT_MAX_RELEVANCE_DISTANCE
    if answered:
        sources = []
        if question_type == config.CHAT_TYPE_PAY_RATES:
            sources += list(config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION.values())
        for passage in searched:
            if passage["document_name"] not in sources:
                sources.append(passage["document_name"])
        return {"question_type": question_type, "query_reference": query_reference, "answer": fields["ANSWER"],
                "source_documents": sources, "closest_distance": closest, "was_refused": False}
    if question_type == config.CHAT_TYPE_QUERY_STATUS:
        return {"question_type": question_type, "query_reference": query_reference, "answer": "",
                "source_documents": [], "closest_distance": closest, "was_refused": False}
    return {"question_type": config.CHAT_TYPE_OUT_OF_SCOPE, "query_reference": query_reference,
            "answer": config.CHAT_REFUSAL_MESSAGE, "source_documents": [], "closest_distance": closest,
            "was_refused": True}
