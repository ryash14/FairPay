"""Reads rate windows, traineeship moves and commitment payments out of the documents that state them.

This is the only module that knows how a rate or a payment is written, and it
reads each classification from its own pay schedule alone. Every amount is a
Decimal built from the text exactly as the document writes it.
"""
import re
from decimal import Decimal

from config import config
from knowledge.vector_index import read_document_chunks


def _opens_on(day_text, month_text):
    month = config.MONTH_NAME_MAPPING[month_text.lower()]
    opens_on = f"{int(day_text):02d} {month}"
    config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE[opens_on]  # KeyError for a day the financial year lacks
    return opens_on


def read_pay_schedule(collection, classification_name):
    """rate_windows in financial-year order, and moves_onto (None when there is no traineeship)."""
    document = config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION[classification_name]
    text = " ".join(read_document_chunks(collection, document))

    single = set(re.findall(config.SINGLE_RATE_PATTERN, text))
    day_night = set(re.findall(config.DAY_NIGHT_RATE_PATTERN, text))
    if bool(single) == bool(day_night):
        raise ValueError(f"{document} must give its rates in one form only, single-rate or day-and-night")

    windows = []
    for groups in single:
        day, month, ordinary, allowance = groups
        windows.append({"opens_on": _opens_on(day, month), "ordinary_rate_aud": Decimal(ordinary),
                        "site_allowance_aud": Decimal(allowance)})
    for groups in day_night:
        day, month, day_rate, night_rate, allowance = groups
        windows.append({"opens_on": _opens_on(day, month), "day_rate_aud": Decimal(day_rate),
                        "night_rate_aud": Decimal(night_rate), "site_allowance_aud": Decimal(allowance)})

    by_day = {}
    for window in windows:
        by_day.setdefault(config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE[window["opens_on"]], []).append(window)
    conflicts = [config.FINANCIAL_YEAR_DATE_BY_DAY_NUMBER[day] for day, found in sorted(by_day.items()) if len(found) > 1]
    if conflicts:
        raise ValueError(f"{document} gives more than one rate from {', '.join(conflicts)}")
    rate_windows = [by_day[day][0] for day in sorted(by_day)]
    if rate_windows[0]["opens_on"] != config.FINANCIAL_YEAR_DATES[0]:
        raise ValueError(f"{document} does not give a rate for the first day of the financial year")

    moves = {re.sub(r"\s+", " ", m).strip() for m in re.findall(config.MOVES_ONTO_PATTERN, text)}
    none_said = bool(re.search(config.NO_TRAINEESHIP_PATTERN, text))
    if bool(moves) == none_said or len(moves) > 1 or \
            (moves and next(iter(moves)) not in config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION):
        raise ValueError(f"{document} must either say the classification has no traineeship or name the one "
                         f"classification the employee moves to when the traineeship ends")
    return {"rate_windows": rate_windows, "moves_onto": next(iter(moves)) if moves else None}


def read_commitment_payments(collection):
    """Each commitment code against the one payment the commitments document gives for it."""
    text = " ".join(read_document_chunks(collection, config.COMMITMENTS_DOCUMENT))
    pairs = set(re.findall(config.COMMITMENT_PAYMENT_PATTERN, text))
    payments = {}
    for code, phrase in config.COMMITMENT_BREACH_PHRASES.items():
        amounts = {amount for found_phrase, amount in pairs if found_phrase == phrase}
        if len(amounts) != 1:
            raise ValueError(f"{config.COMMITMENTS_DOCUMENT} must give exactly one payment for {code}")
        payments[code] = Decimal(next(iter(amounts)))
    return payments
