"""Rebuilds the pay: verified hours, pay pieces, entitled pay, the comparison, commitments, settlement, ranking.

Every figure here is exact. Hours and amounts are Decimal, every intermediate
step is a Fraction, and nothing passes through a float. Rounding happens in
two places only: each piece's displayed figures, and the total, once.
"""
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
import math

import pandas as pd

from config import config


# ----------------------------------------------------------------- internals
def _is_missing(value):
    if value is None or value is pd.NA:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and value.strip() == ""


def _day(date_text):
    return config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE[date_text]


def _display(fraction_value):
    exact = Decimal(fraction_value.numerator) / Decimal(fraction_value.denominator)
    return exact.quantize(config.PIECE_DISPLAY_QUANTUM, rounding=ROUND_HALF_UP)


def _window_in_force(windows, day):
    chosen = None
    for window in windows:
        if _day(window["opens_on"]) <= day:
            chosen = window
    return chosen


# ----------------------------------------------------------------- hours
def measure_hours(query_profile):
    """The verified hours in the shape the roster needs, refusing any that could not have been worked."""
    roster = query_profile[config.ROSTER_TYPE_COLUMN]
    if roster not in (config.STANDARD_ROSTER_TYPE, config.DAY_NIGHT_ROSTER_TYPE):
        raise ValueError(f"{config.ROSTER_TYPE_COLUMN} must be {config.STANDARD_ROSTER_TYPE} or "
                         f"{config.DAY_NIGHT_ROSTER_TYPE}, not {roster}")
    days = int(query_profile[config.DAYS_IN_PERIOD_COLUMN])
    available = Decimal(config.HOURS_IN_A_DAY * days)
    columns = [config.VERIFIED_ORDINARY_HOURS_COLUMN]
    if roster == config.DAY_NIGHT_ROSTER_TYPE:
        columns.append(config.VERIFIED_NIGHT_HOURS_COLUMN)
    hours = {column: Decimal(str(query_profile[column])) for column in columns}
    for value in hours.values():
        if not value.is_finite() or (value * config.QUARTER_HOURS_PER_HOUR) % 1 != 0:
            raise ValueError(f"Verified hours must be whole quarter hours: {hours}")
    total = sum(hours.values(), Decimal(0))
    if total < 0 or total > available:
        raise ValueError(f"Verified hours do not fit a period of {days} days: {hours}")
    if roster == config.STANDARD_ROSTER_TYPE:
        return {"total_hours": hours[config.VERIFIED_ORDINARY_HOURS_COLUMN]}
    day_hours = hours[config.VERIFIED_ORDINARY_HOURS_COLUMN]
    night_hours = hours[config.VERIFIED_NIGHT_HOURS_COLUMN]
    return {"day_hours": day_hours, "night_hours": night_hours, "total_hours": day_hours + night_hours}


# ----------------------------------------------------------------- pieces
def build_pay_pieces(query_profile, pay_schedules):
    """Split the period wherever the classification owed or its rate window changes, and nowhere else."""
    start_text = query_profile[config.PERIOD_START_COLUMN]
    end_text = query_profile[config.PERIOD_END_COLUMN]
    start, end = _day(start_text), _day(end_text)
    if end < start:
        raise ValueError(f"The pay period ends on {end_text}, before it starts on {start_text} in the financial year")
    entitled = query_profile[config.ENTITLED_CLASSIFICATION_COLUMN]
    moves_onto = pay_schedules[entitled]["moves_onto"]
    last_day = query_profile.get(config.TRAINEESHIP_LAST_DAY_COLUMN)
    recorded = not _is_missing(last_day)
    if recorded and moves_onto is None:
        raise ValueError(f"The employee records a traineeship's last day, but the {entitled} schedule says the "
                         f"classification has no traineeship")
    hand_over = _day(last_day) + 1 if recorded else len(config.FINANCIAL_YEAR_DATES) + 1
    if hand_over <= start:
        raise ValueError(f"The {entitled} traineeship ended on {last_day}, before the period starts on {start_text}, "
                         f"so it is not the classification owed on the period's first day")
    pieces = []
    for day in range(start, end + 1):
        owed = moves_onto if day >= hand_over else entitled
        window = _window_in_force(pay_schedules[owed]["rate_windows"], day)
        last = pieces[-1] if pieces else None
        if last is not None and last["classification"] == owed and last["rate_window"] is window:
            last["last_day"] = config.FINANCIAL_YEAR_DATE_BY_DAY_NUMBER[day]
            last["days"] += 1
        else:
            pieces.append({"classification": owed, "first_day": config.FINANCIAL_YEAR_DATE_BY_DAY_NUMBER[day],
                           "last_day": config.FINANCIAL_YEAR_DATE_BY_DAY_NUMBER[day], "days": 1,
                           "rate_window": window})
    return pieces


def compute_entitled_pay(pay_pieces, hours):
    """Price each piece at its own rates; add the exact pieces and round once, to the cent, half up."""
    period_days = sum(piece["days"] for piece in pay_pieces)
    priced, total = [], Fraction(0)
    for piece in pay_pieces:
        window = piece["rate_window"]
        share = Fraction(piece["days"], period_days)
        allowance = piece["days"] * Fraction(window["site_allowance_aud"])
        figures = dict(piece)
        if "night_rate_aud" in window:
            day_hours = Fraction(hours["day_hours"]) * share
            night_hours = Fraction(hours["night_hours"]) * share
            pay = allowance + day_hours * Fraction(window["day_rate_aud"]) + night_hours * Fraction(window["night_rate_aud"])
            figures.update(day_hours=_display(day_hours), night_hours=_display(night_hours), pay_aud=_display(pay))
        else:
            piece_hours = Fraction(hours["total_hours"]) * share
            pay = allowance + piece_hours * Fraction(window["ordinary_rate_aud"])
            figures.update(hours=_display(piece_hours), pay_aud=_display(pay))
        priced.append(figures)
        total += pay
    cents = math.floor(total * config.CENTS_PER_DOLLAR + Fraction(1, 2))
    entitled = (Decimal(cents) / Decimal(config.CENTS_PER_DOLLAR)).quantize(config.CENT)
    return {"pieces": priced, "entitled_pay_aud": entitled}


# ----------------------------------------------------------------- comparison
def compare_with_paid(query_profile, entitled_pay_aud):
    """Which way the pay was wrong, by how much, and whether it reaches the AUD 1.00 line."""
    raw = query_profile[config.AMOUNT_PAID_COLUMN]
    if isinstance(raw, float):
        raise ValueError(f"{config.AMOUNT_PAID_COLUMN} must be dollars and cents, not {raw}")
    paid = raw if isinstance(raw, Decimal) else Decimal(str(raw).strip())
    if not paid.is_finite() or paid.as_tuple().exponent != config.CENT.as_tuple().exponent:
        raise ValueError(f"{config.AMOUNT_PAID_COLUMN} must be dollars and cents, not {raw}")
    difference = entitled_pay_aud - paid
    if difference > 0:
        direction = config.UNDERPAID
    elif difference < 0:
        direction = config.OVERPAID
    else:
        direction = config.PAID_CORRECTLY
    at_stake = abs(difference)
    return {"amount_paid_aud": paid, "entitled_pay_aud": entitled_pay_aud, "difference_aud": difference,
            "money_at_stake_aud": at_stake, "direction": direction,
            "correction_warranted": bool(at_stake >= config.CORRECTION_THRESHOLD_AUD)}


def compute_commitment_payments(query_profile, commitment_payments):
    """Every payment due for a commitment the record shows broken, and their total."""
    breached = []
    for code, column in config.COMMITMENT_BREACH_COLUMNS.items():
        value = query_profile.get(column)
        if value not in (config.BOOLEAN_YES, config.BOOLEAN_NO):
            raise ValueError(f"{column} must be Yes or No, not {value}")
        if value == config.BOOLEAN_YES:
            breached.append({"commitment_code": code, "payment_aud": commitment_payments[code]})
    total = sum((entry["payment_aud"] for entry in breached), Decimal(0)).quantize(config.CENT)
    return {"breached_commitments": breached, "commitment_total_aud": total}


def compute_settled_amount(decision, difference_aud, commitment_total_aud):
    """What a decision settles: None when upheld, otherwise the signed amount and its direction."""
    if decision not in config.DECISION_OPTIONS:
        raise ValueError(f"The decision must be one of {', '.join(config.DECISION_OPTIONS)}, not {decision}")
    if not isinstance(difference_aud, Decimal) or not isinstance(commitment_total_aud, Decimal):
        raise ValueError(f"The difference and the commitment payments must be Decimal dollars and cents, not "
                         f"{difference_aud} and {commitment_total_aud}")
    if decision == config.DECISION_UPHOLD_PAY:
        return None
    settled = difference_aud
    if decision == config.DECISION_CORRECT_AND_COMPENSATE:
        settled = difference_aud + commitment_total_aud
    if settled > 0:
        direction = config.SETTLEMENT_PAID_TO_EMPLOYEE
    elif settled < 0:
        direction = config.SETTLEMENT_RECOVERED
    else:
        direction = config.SETTLEMENT_NOTHING_DUE
    return {"settled_amount_aud": settled, "amount_to_settle_aud": abs(settled), "direction": direction}


# ----------------------------------------------------------------- queue
def rank_query_queue(open_queries, pay_schedules):
    """Every open query priced exactly as an assessment would price it, most money at stake first."""
    ranked = []
    for query_profile in open_queries.to_dict(orient="records"):
        hours = measure_hours(query_profile)
        pieces = build_pay_pieces(query_profile, pay_schedules)
        entitled = compute_entitled_pay(pieces, hours)
        comparison = compare_with_paid(query_profile, entitled["entitled_pay_aud"])
        ranked.append({config.QUERY_REFERENCE_COLUMN: query_profile[config.QUERY_REFERENCE_COLUMN],
                       config.PAYROLL_CENTRE_COLUMN: query_profile[config.PAYROLL_CENTRE_COLUMN],
                       config.PAID_CLASSIFICATION_COLUMN: query_profile[config.PAID_CLASSIFICATION_COLUMN],
                       config.ENTITLED_CLASSIFICATION_COLUMN: query_profile[config.ENTITLED_CLASSIFICATION_COLUMN],
                       **comparison})
    ranked.sort(key=lambda row: row[config.QUERY_REFERENCE_COLUMN])
    ranked.sort(key=lambda row: row["money_at_stake_aud"], reverse=True)
    return ranked
