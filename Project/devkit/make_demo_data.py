"""Generate realistic demo extracts for FairPay AI.

Writes the five raw extracts (with every defect the SRS lists) and the two
clean live-queue files to data/. Use this only when the capstone's pre-loaded
data is not available. The generator is seeded, so it always writes the same
files.

    python devkit/make_demo_data.py            # full size, as in the SRS
    python devkit/make_demo_data.py --small    # a quarter of the rows, faster
"""
import argparse
import os
import random
import sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)
sys.path.insert(0, HERE)

from config import config  # noqa: E402
from company_truth import RATE_WINDOWS, MOVES_ONTO, WORKED_EXAMPLE_REFERENCE  # noqa: E402

DAY = config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE
DATE = config.FINANCIAL_YEAR_DATE_BY_DAY_NUMBER
MONTH_NUMBER = {name: number for number, name in config.MONTH_BY_NUMBER.items()}
FULL_MONTH = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June",
              "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"}

CENTRES = {"Sydney": "SYD", "Melbourne": "MEL", "Brisbane": "BNE", "Perth": "PER"}
CENTRE_SPELLINGS = {"Sydney": ["Sydney", "SYD", "sydney", "Sydney CBD", "syd"],
                    "Melbourne": ["Melbourne", "Melb", "MEL", "melbourne"],
                    "Brisbane": ["Brisbane", "BNE", "brisbane", "Brissy"],
                    "Perth": ["Perth", "PER", "perth", "Perth WA"]}
SYSTEM_SPELLINGS = {"Kestrel PayHub": ["Kestrel PayHub", "KESTREL PAYHUB", "PayHub"],
                    "Harbour Payroll": ["Harbour Payroll", "HARBOUR PAYROLL", "harbour"],
                    "Coastline Pay": ["Coastline Pay", "coastline", "COASTLINE PAY"],
                    "WestPay US": ["WestPay US", "westpay", "WESTPAY US"]}
CHANNEL_SPELLINGS = {"Email": ["Email", "email", "E-mail"], "Phone": ["Phone", "phone", "Call"],
                     "HR portal": ["HR portal", "Portal", "hr portal"], "In person": ["In person", "walk-in"]}
CLASS_SPELLINGS = {"Front of House": ["Front of House", "FOH", "front of house"],
                   "Front of House Trainee": ["Front of House Trainee", "FOH Trainee", "foh trainee"],
                   "Kitchen": ["Kitchen", "kitchen", "KIT"],
                   "Kitchen Trainee": ["Kitchen Trainee", "kit trainee", "KITCHEN TRAINEE"],
                   "Night Audit": ["Night Audit", "night auditor", "NIGHT AUDIT"]}
ROSTER_SPELLINGS = {"Standard": ["Standard", "STD", "standard"], "Day-night": ["Day-night", "day night", "DN"]}
SOURCE_SPELLINGS = {"Time clock": ["Time clock", "Clock", "time clock"], "Timesheet": ["Timesheet", "manual timesheet"],
                    "Rostered": ["Rostered", "roster", "ROSTERED"]}
PAYMENT_SPELLINGS = {"Bank transfer": ["Bank transfer", "Bank Transfer", "EFT"], "Pay card": ["Pay card", "paycard"],
                     "Cheque": ["Cheque", "chq"]}
FREQ_SPELLINGS = {"Fortnightly": ["Fortnightly", "fortnightly", "FN"], "Monthly": ["Monthly", "monthly", "mth"]}
YES = ["Yes", "Y", "TRUE", "1", "yes", "true"]
NO = ["No", "N", "FALSE", "0", "no", "false"]
NULLS = ["", "-", "N/A", "none", "?", "Not recorded", "n/a", "NONE"]
CLASSES = list(config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION)


# ----------------------------------------------------------------- helpers
def pick(rng, options):
    return options[rng.randrange(len(options))]


def window_on(classification, day):
    chosen = None
    for window in RATE_WINDOWS[classification]:
        if DAY[window[0]] <= day:
            chosen = window
    return chosen


def true_pay(entitled, last_day, start, end, ordinary, night):
    """The company's own reckoning, used only to write amount_paid in the demo queue."""
    hand_over = DAY[last_day] + 1 if last_day else 366
    pieces = []
    for day in range(start, end + 1):
        owed = MOVES_ONTO[entitled] if day >= hand_over else entitled
        window = window_on(owed, day)
        if pieces and pieces[-1][0] == owed and pieces[-1][1] == window:
            pieces[-1][2] += 1
        else:
            pieces.append([owed, window, 1])
    total_days = end - start + 1
    total = Fraction(0)
    for owed, window, days in pieces:
        share = Fraction(days, total_days)
        if len(window) == 4:
            total += days * Fraction(window[3]) + Fraction(ordinary) * share * Fraction(window[1]) \
                + Fraction(night) * share * Fraction(window[2])
        else:
            total += days * Fraction(window[2]) + (Fraction(ordinary) + Fraction(night)) * share * Fraction(window[1])
    cents = int(total * 100 + Fraction(1, 2))
    return Decimal(cents) / 100, len(pieces)


def flat_pay(classification, window_day, days, ordinary, night):
    window = window_on(classification, window_day)
    if len(window) == 4:
        value = days * Fraction(window[3]) + Fraction(ordinary) * Fraction(window[1]) + Fraction(night) * Fraction(window[2])
    else:
        value = days * Fraction(window[2]) + (Fraction(ordinary) + Fraction(night)) * Fraction(window[1])
    return Decimal(int(value * 100 + Fraction(1, 2))) / 100


def quarter(rng, low, high):
    return Decimal(rng.randint(int(low * 4), int(high * 4))) / 4


def money_text(rng, value, credit_ok=False):
    value = Decimal(value).quantize(Decimal("0.01"))
    if value < 0 and credit_ok:
        magnitude = -value
        return pick(rng, [f"-{magnitude}", f"${magnitude:,} CR", f"({magnitude})", f"(${magnitude:,})", f"{magnitude} cr"])
    style = rng.randrange(6)
    if style == 0:
        return f"${value:,}"
    if style == 1:
        return f"aud {value:,}"
    if style == 2:
        return f"{value} AUD"
    if style == 3:
        return f"AUD {value:,}"
    return f"{value}"


def hours_text(rng, hours):
    hours = Decimal(hours)
    style = rng.randrange(6)
    if style == 0:
        return f"{hours} h"
    if style == 1:
        return f"{hours} hrs"
    if style == 2:
        minutes = int(hours * 60)
        return f"{minutes:,} min" if minutes >= 1000 and rng.random() < 0.5 else f"{minutes} min"
    text = f"{hours}"
    return text[:-3] if text.endswith(".00") else text


def date_text(rng, day_number, month_first, allow_impossible=False):
    if allow_impossible and rng.random() < 0.08:
        if month_first:
            return pick(rng, ["30 Feb", "6/31", "29-feb", "31 September"])
        return pick(rng, ["30 Feb", "31/6", "29-feb", "31 September", "0/3"])
    day, month = DATE[day_number].split()
    day_int = int(day)
    style = rng.randrange(5)
    if style == 0:
        return DATE[day_number]
    if style == 1:
        return f"{day_int} {FULL_MONTH[month]}" if rng.random() < 0.5 else f"{day_int}-{month.lower()}"
    number = MONTH_NUMBER[month]
    first, second = (number, day_int) if month_first else (day_int, number)
    if rng.random() < 0.5:
        return f"{first:02d}/{second:02d}"
    return f"{first}/{second}"


def maybe_null(rng, value, share):
    return pick(rng, NULLS) if rng.random() < share else value


def flag(rng, yes):
    return pick(rng, YES) if yes else pick(rng, NO)


def period_for(rng, frequency):
    if frequency == "Monthly":
        month = rng.randrange(12)
        start = 1 + sum(config.FINANCIAL_YEAR_MONTH_LENGTHS[m] for m in config.FINANCIAL_YEAR_MONTHS[:month])
        end = start + config.FINANCIAL_YEAR_MONTH_LENGTHS[config.FINANCIAL_YEAR_MONTHS[month]] - 1
        return start, end
    start = rng.randint(1, 352)
    return start, start + 13


# ----------------------------------------------------------------- pay query extracts
def make_query_rows(rng, count, id_base):
    rows = []
    for index in range(count):
        centre = pick(rng, list(CENTRES))
        system = {"Sydney": "Kestrel PayHub", "Melbourne": "Harbour Payroll", "Brisbane": "Coastline Pay"}.get(centre)
        if centre == "Perth":
            system = "Kestrel PayHub" if rng.random() < 0.2 else "WestPay US"
        month_first = config.MONTH_FIRST_BY_PAYROLL_SYSTEM[system]
        frequency = "Monthly" if rng.random() < 0.3 else "Fortnightly"
        start, end = period_for(rng, frequency)
        days = end - start + 1
        entitled = pick(rng, CLASSES)
        wrong_class = rng.random() < 0.14
        paid = entitled
        if wrong_class:
            paid = pick(rng, [c for c in CLASSES if c != entitled and (c == "Night Audit") == (entitled == "Night Audit")]
                        or [entitled])
            wrong_class = paid != entitled
        roster = "Day-night" if entitled == "Night Audit" else "Standard"
        last_day = None
        overrun = None
        if entitled in MOVES_ONTO and rng.random() < 0.55:
            last = rng.randint(max(1, start - 20), min(365, end + 40))
            if last >= start:
                last_day = last
                if last < end:
                    overrun = 0 if rng.random() < 0.55 else rng.randint(1, end - last)
        source = pick(rng, ["Time clock"] * 5 + ["Timesheet"] * 3 + ["Rostered"] * 2)
        electronic = rng.random() < 0.7
        consecutive = rng.randint(1, 6) if source == "Rostered" else (0 if rng.random() < 0.8 else rng.randint(1, 2))
        since_clock = rng.randint(0, 9) if source == "Time clock" else rng.randint(5, 90)
        contracted = pick(rng, [20, 25, 30, 35, 38])
        ordinary = quarter(rng, contracted * days / 7 * 0.7, contracted * days / 7 * 1.25)
        night = quarter(rng, 8, 40) if roster == "Day-night" else None
        total = ordinary + (night or 0)
        tenure = rng.randint(1, 180)
        hours_change = None if tenure < 6 else rng.randint(-35, 45)
        rate_changes = sum(1 for w in RATE_WINDOWS[paid] if start < DAY[w[0]] <= end)
        class_changes = 1 if overrun is not None and rng.random() < 0.5 else 0
        transfer = rng.random() < 0.08
        prior = min(6, int(rng.expovariate(1.2)))
        logit = (-2.6 + 1.25 * (source == "Rostered") + 0.32 * consecutive + 0.018 * since_clock + 1.7 * wrong_class
                 + 0.16 * (overrun or 0) + 0.9 * rate_changes + 0.018 * abs(hours_change or 0) + 0.55 * (not electronic)
                 + 0.9 * transfer + 0.15 * prior + rng.gauss(0, 0.3))
        corrected = rng.random() < 1 / (1 + np.exp(-(1.45 * logit + 0.9)))
        paid_amount = flat_pay(paid, start, days, ordinary, night or 0) + Decimal(rng.randint(-900, 900)) / 100
        packaging = Decimal(rng.randint(3000, 25000)) / 100 if rng.random() < 0.25 else None
        recovery = Decimal(0)
        if rng.random() < 0.2:
            recovery = Decimal(rng.randint(-40000, 60000)) / 100
        rows.append({
            "query_id": f"PQ{id_base + index}",
            "query_reference": f"PQR-{CENTRES[centre]}-{rng.randint(0, 9999999):07d}",
            "employee_number": f"EMP-{rng.randint(10000000, 99999999)}",
            "payroll_centre": centre, "payroll_system": system,
            "contact_channel": pick(rng, list(CHANNEL_SPELLINGS)),
            "_start": start, "_end": end, "_days": days, "_month_first": month_first,
            "pay_frequency": frequency, "paid_classification": paid, "entitled_classification": entitled,
            "_last_day": last_day, "roster_type": roster, "electronic_timesheet_flag": electronic,
            "hours_source_type": source, "_ordinary": ordinary, "_night": night, "_total": total,
            "_amount": paid_amount, "consecutive_rostered_periods": consecutive,
            "days_since_last_clock_match": since_clock, "hours_change_vs_average_pct": hours_change,
            "classification_changes_in_period": class_changes, "traineeship_days_overrun": overrun,
            "rate_changes_in_period": rate_changes, "prior_queries_12m": prior, "tenure_months": tenure,
            "contracted_hours_per_week": contracted, "payment_method": pick(rng, ["Bank transfer"] * 6 + ["Pay card", "Cheque"]),
            "_packaging": packaging, "_recovery": recovery, "venue_transfer_flag": transfer,
            "interpreter_required_flag": rng.random() < 0.06,
            "pay_run_code": f"PR-{rng.randint(100, 999)}", "weekday_raised": pick(rng, ["Monday", "Tuesday", "Wednesday",
                                                                                        "Thursday", "Friday", "Saturday", "Sunday"]),
            "desk_code": pick(rng, ["HRD-A1", "HRD-A2", "HRD-B1", "HRD-C3"]), "_target": corrected,
        })
    return rows


def dirty_query_frame(rng, rows):
    out = []
    for row in rows:
        mf = row["_month_first"]
        start_text = date_text(rng, row["_start"], mf)
        end_text = date_text(rng, row["_end"], mf)
        if rng.random() < 0.03:
            start_text, end_text = end_text, start_text
        days = row["_days"]
        if rng.random() < 0.04:
            days += pick(rng, [-2, -1, 1, 3])
        total = row["_total"]
        if rng.random() < 0.04:
            total = total + pick(rng, [Decimal("0.25"), Decimal("1.5"), Decimal("-2"), Decimal("4.75")])
        contracted = row["contracted_hours_per_week"]
        tenure = row["tenure_months"]
        since = row["days_since_last_clock_match"]
        if rng.random() < 0.01:
            contracted = pick(rng, [0, 380, 99])
        if rng.random() < 0.01:
            tenure = pick(rng, [9999, 1200])
        if rng.random() < 0.01:
            since = pick(rng, [999, 4000])
        target = flag(rng, row["_target"])
        if rng.random() < 0.012:
            target = pick(rng, NULLS)
        record = {
            "query_id": row["query_id"], "query_reference": row["query_reference"],
            "employee_number": row["employee_number"],
            "payroll_centre": pick(rng, CENTRE_SPELLINGS[row["payroll_centre"]]),
            "payroll_system": maybe_null(rng, pick(rng, SYSTEM_SPELLINGS[row["payroll_system"]]), 0.0),
            "contact_channel": maybe_null(rng, pick(rng, CHANNEL_SPELLINGS[row["contact_channel"]]), 0.03),
            "period_start_date": start_text, "period_end_date": end_text,
            "days_in_period": str(days) if rng.random() > 0.02 else f"{days}.0",
            "pay_frequency": pick(rng, FREQ_SPELLINGS[row["pay_frequency"]]),
            "paid_classification": pick(rng, CLASS_SPELLINGS[row["paid_classification"]]),
            "entitled_classification": pick(rng, CLASS_SPELLINGS[row["entitled_classification"]]),
            "traineeship_last_day": (date_text(rng, row["_last_day"], mf, allow_impossible=True)
                                     if row["_last_day"] else pick(rng, NULLS)),
            "roster_type": pick(rng, ROSTER_SPELLINGS[row["roster_type"]]),
            "electronic_timesheet_flag": flag(rng, row["electronic_timesheet_flag"]),
            "hours_source_type": pick(rng, SOURCE_SPELLINGS[row["hours_source_type"]]),
            "ordinary_hours_paid": hours_text(rng, row["_ordinary"]),
            "night_hours_paid": hours_text(rng, row["_night"]) if row["_night"] is not None else pick(rng, NULLS),
            "total_hours_paid": hours_text(rng, total),
            "amount_paid_aud": money_text(rng, row["_amount"]),
            "consecutive_rostered_periods": str(row["consecutive_rostered_periods"]),
            "days_since_last_clock_match": maybe_null(rng, str(since), 0.02),
            "hours_change_vs_average_pct": (str(row["hours_change_vs_average_pct"])
                                            if row["hours_change_vs_average_pct"] is not None else pick(rng, NULLS)),
            "classification_changes_in_period": str(row["classification_changes_in_period"]),
            "traineeship_days_overrun": (str(row["traineeship_days_overrun"])
                                         if row["traineeship_days_overrun"] is not None else pick(rng, NULLS)),
            "rate_changes_in_period": str(row["rate_changes_in_period"]),
            "prior_queries_12m": str(row["prior_queries_12m"]),
            "tenure_months": str(tenure),
            "contracted_hours_per_week": maybe_null(rng, str(contracted), 0.02),
            "payment_method": pick(rng, PAYMENT_SPELLINGS[row["payment_method"]]),
            "salary_packaging_aud": money_text(rng, row["_packaging"]) if row["_packaging"] else pick(rng, NULLS),
            "recovery_balance_aud": money_text(rng, row["_recovery"], credit_ok=True),
            "venue_transfer_flag": flag(rng, row["venue_transfer_flag"]),
            "interpreter_required_flag": flag(rng, row["interpreter_required_flag"]),
            "pay_run_code": row["pay_run_code"], "weekday_raised": row["weekday_raised"],
            "desk_code": row["desk_code"], "pay_corrected": target,
        }
        out.append(record)
    frame = pd.DataFrame(out)
    duplicates = frame.sample(frac=0.025, random_state=rng.randint(0, 10**6))
    frame = pd.concat([frame, duplicates]).sample(frac=1, random_state=rng.randint(0, 10**6)).reset_index(drop=True)
    return frame


# ----------------------------------------------------------------- effort extracts
CATEGORY_EFFORT = {"Crossed timesheets": 1.6, "Deductions and tax": -0.6, "Faulty timesheet": 0.6,
                   "Rate change date": 0.3, "Rostered hours paid": 0.9, "Traineeship overrun": 0.7,
                   "Venue transfer hours": 1.1, "Wrong classification applied": 0.8}
GRADE_EFFORT = {"Associate Payroll Officer": 0.9, "Payroll Officer": 0.3, "Senior Payroll Officer": -0.2, "Team Leader": -0.4}
GRADE_SPELLINGS = {"Associate Payroll Officer": ["Associate Payroll Officer", "Assoc. Payroll Officer"],
                   "Payroll Officer": ["Payroll Officer", "payroll officer", "PO"],
                   "Senior Payroll Officer": ["Senior Payroll Officer", "Snr Payroll Officer"],
                   "Team Leader": ["Team Leader", "TL"]}


def duration_text(rng, hours):
    hours = Decimal(hours)
    whole = int(hours)
    minutes = int((hours - whole) * 60)
    style = rng.randrange(5)
    if style == 0 and minutes:
        return f"{whole}h {minutes}m" if rng.random() < 0.6 else f"{whole}h{minutes}m"
    if style == 1:
        return f"{int(hours * 60)} min"
    if style == 2:
        return f"{hours} h"
    text = f"{hours}"
    return text[:-3] if text.endswith(".00") else text


def make_effort_frame(rng, count, id_base):
    out = []
    for index in range(count):
        centre = pick(rng, list(CENTRES))
        category = pick(rng, config.QUERY_CATEGORIES)
        grade = pick(rng, ["Associate Payroll Officer", "Payroll Officer", "Payroll Officer", "Senior Payroll Officer", "Team Leader"])
        band = pick(rng, ["High", "Medium", "Low"])
        roster = "Day-night" if rng.random() < 0.15 else "Standard"
        pieces = pick(rng, [1, 1, 2, 2, 3, 4])
        classes = min(pieces, pick(rng, [1, 1, 2, 3]))
        stake = Decimal(0) if rng.random() < 0.3 else Decimal(rng.randint(100, 120000)) / 100
        clock = rng.random() < 0.6
        interview = rng.random() < 0.25
        vendor = rng.random() < 0.12
        venue = rng.random() < 0.3
        letters = rng.randint(0, 7)
        calls = rng.randint(0, 8)
        interpreter = rng.random() < 0.07
        escalated = rng.random() < 0.1
        open_queries = rng.randint(3, 40)
        hours = (0.8 + 0.55 * pieces + 0.35 * classes + 0.0016 * float(stake) + 0.22 * letters + 0.16 * calls
                 + GRADE_EFFORT[grade] + 1.1 * interview + 1.7 * vendor + 0.45 * venue + 0.35 * clock + 0.9 * interpreter
                 + 1.4 * escalated + CATEGORY_EFFORT[category] + 0.25 * (band == "High") + 0.012 * open_queries
                 + 0.3 * (roster == "Day-night") + rng.gauss(0, 0.55))
        hours = max(0.25, round(hours * 4) / 4)
        hours_text_value = duration_text(rng, f"{hours:.2f}")
        if rng.random() < 0.012:
            hours_text_value = pick(rng, ["0", "95", "120 h", "0 min"])
        if rng.random() < 0.012:
            hours_text_value = pick(rng, NULLS)
        letters_text = str(letters) if rng.random() < 0.6 else f"{letters} letter{'s' if letters != 1 else ''}"
        calls_text = str(calls) if rng.random() < 0.6 else f"{calls} call{'s' if calls != 1 else ''}"
        if rng.random() < 0.006:
            letters_text = "64"
        if rng.random() < 0.006:
            calls_text = "75 calls"
        start_day = rng.randint(1, 365)
        day, month = DATE[start_day].split()
        started = pick(rng, [DATE[start_day], f"{int(day)}/{MONTH_NUMBER[month]}", f"{int(day)} {FULL_MONTH[month]}",
                             f"{int(day)}-{month.lower()}"])
        out.append({
            "effort_record_id": f"ER{id_base + index}",
            "query_reference": f"PQR-{CENTRES[centre]}-{rng.randint(0, 9999999):07d}",
            "analyst_id": f"PA{rng.randint(100, 399)}",
            "analyst_grade": pick(rng, GRADE_SPELLINGS[grade]),
            "payroll_centre": pick(rng, CENTRE_SPELLINGS[centre]),
            "contact_channel": maybe_null(rng, pick(rng, CHANNEL_SPELLINGS[pick(rng, list(CHANNEL_SPELLINGS))]), 0.03),
            "query_category": pick(rng, [category, category.lower(), category.upper()]),
            "correction_band": pick(rng, [band, band.lower(), band.upper()]),
            "roster_type": pick(rng, ROSTER_SPELLINGS[roster]),
            "electronic_timesheet_flag": flag(rng, rng.random() < 0.7),
            "period_pieces_count": str(pieces), "classifications_involved_count": str(classes),
            "amount_at_stake_aud": money_text(rng, stake),
            "clock_records_obtained_flag": flag(rng, clock), "manager_interview_required_flag": flag(rng, interview),
            "vendor_audit_required_flag": flag(rng, vendor), "venue_manager_involved_flag": flag(rng, venue),
            "letters_sent_count": letters_text, "calls_made_count": calls_text,
            "interpreter_required_flag": flag(rng, interpreter), "complaint_escalated_flag": flag(rng, escalated),
            "analyst_open_queries_count": maybe_null(rng, str(open_queries if rng.random() > 0.006 else 400), 0.02),
            "remediation_started_date": started,
            "weekday_started": pick(rng, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
            "queue_code": f"Q-{rng.randint(10, 60)}", "remediation_hours": hours_text_value,
        })
    frame = pd.DataFrame(out)
    duplicates = frame.sample(frac=0.03, random_state=rng.randint(0, 10**6))
    return pd.concat([frame, duplicates]).sample(frac=1, random_state=rng.randint(0, 10**6)).reset_index(drop=True)


# ----------------------------------------------------------------- notes
PHRASES = {
    "Rostered hours paid": ["venue paying off the roster since the clock was replaced", "paid rostered hrs not actual clock hrs",
                            "roster shows 38 but clocked more", "clock out times ignored, roster used for pay",
                            "worked extra shifts not on the roster", "pay matches roster not swipe data",
                            "rostered hours paid, clock shows longer shifts"],
    "Wrong classification applied": ["promoted to kitchen but still paid as trainee classification", "paid wrong classification since promo",
                                     "new role agreed but payroll never applied it", "classification on payslip is wrong",
                                     "should be FOH not trainee per contract", "agreed classification not applied after review",
                                     "doing night audit work but paid FOH classification"],
    "Rate change date": ["pay rise paid from the wrong date", "new rate started late, should be from the first",
                         "rate increase not backdated", "old rate used after the rate change", "rate went up mid period but payslip shows old rate",
                         "rate change date wrong on system"],
    "Traineeship overrun": ["traineeship finished but still on trainee rate", "trainee rate kept after traineeship ended",
                            "completed traineeship last month still paid as trainee", "trainee end date passed, rate not moved",
                            "certificate done, still trainee pay"],
    "Crossed timesheets": ["badges swapped at the time clock", "two staff clocking on each others card", "hours belong to another attendant",
                           "crossed timesheets with a colleague same surname", "swiped wrong badge all fortnight",
                           "another employees hours on my payslip"],
    "Faulty timesheet": ["manual timesheet entry looks wrong for the long weekend", "timesheet keyed incorrectly",
                         "supervisor entered wrong hours on timesheet", "timesheet missing a day", "typo in timesheet hours",
                         "faulty timesheet entry, hours doubled"],
    "Venue transfer hours": ["moved from melbourne to sydney hotel, hours lost in transfer", "hours lost when transferred venues",
                             "new venue didnt pick up first week hours", "transfer between hotels mid period, shifts missing",
                             "changed venue and pay dropped"],
    "Deductions and tax": ["tax went up, employee surprised", "salary packaging deduction forgotten", "asking why net pay lower, tax bracket",
                           "super and tax deductions query", "deduction for uniform queried", "packaging amount changed on payslip"],
}
OPENERS = ["Employee emailed -", "Follow up call -", "Called employee,", "EE rang -", "Portal msg:", "Spoke w/ employee -",
           "Officer update:", "Closure note -", "Callback -", "Walk in -"]
CLOSERS = ["...", "will check w/ venue mgr", "awaiting clock export", "pls review", "escalate if needed", "", "",
           "checking payslip", "sent to payroll", "employee upset"]
GENERIC = ["pay looks short", "payslip query", "wants explanation", "net pay different to expected"]


def typo(rng, text):
    if rng.random() < 0.3 and len(text) > 10:
        position = rng.randrange(1, len(text) - 1)
        return text[:position] + text[position + 1] + text[position] + text[position + 2:]
    return text


def note_text(rng, category):
    phrase = pick(rng, PHRASES[category])
    if rng.random() < 0.06:
        phrase = pick(rng, PHRASES[pick(rng, config.QUERY_CATEGORIES)])
    parts = [pick(rng, OPENERS), typo(rng, phrase)]
    if rng.random() < 0.3:
        parts.append(pick(rng, GENERIC))
    parts.append(pick(rng, CLOSERS))
    return " ".join(p for p in parts if p).strip()


def dirty_note(rng, text):
    roll = rng.random()
    if roll < 0.05:
        text = text.upper()
    elif roll < 0.10:
        text = text.replace(" - ", " <br> ", 1) if " - " in text else f"<p>{text}</p>"
    elif roll < 0.13:
        text = text.replace("'", "&#39;").replace(" and ", " &amp; ").replace(" w/ ", "\u00a0w/\u00a0")
    elif roll < 0.15:
        text = f"<b>{text}</b>&nbsp;"
    return text


def timestamp_text(rng, day_number):
    day, month = DATE[day_number].split()
    hour, minute = rng.randint(7, 19), rng.randint(0, 59)
    style = rng.randrange(4)
    if style == 0:
        return f"{DATE[day_number]} {hour:02d}:{minute:02d}"
    if style == 1:
        return f"{int(day):02d}/{MONTH_NUMBER[month]:02d} {hour:02d}:{minute:02d}"
    if style == 2:
        return f"{int(day)} {FULL_MONTH[month]} {hour}:{minute:02d}"
    return f"{int(day)}-{month.lower()} {hour:02d}:{minute:02d}"


def make_notes_frame(rng, count, id_base):
    out = []
    index = 0
    while index < count:
        category = pick(rng, config.QUERY_CATEGORIES)
        centre = pick(rng, list(CENTRES))
        reference = f"PQR-{CENTRES[centre]}-{rng.randint(0, 9999999):07d}"
        channel = pick(rng, list(CHANNEL_SPELLINGS))
        for sequence in range(1, rng.randint(1, 4) + 1):
            text = note_text(rng, category)
            if rng.random() < 0.04:
                text = pick(rng, ["call back pls", "see above", "no answer", "left vm", "chased"])
            raw = dirty_note(rng, text)
            length = len(text) if rng.random() > 0.06 else len(text) + rng.randint(3, 40)
            stamp = timestamp_text(rng, rng.randint(1, 365))
            if rng.random() < 0.004:
                stamp = "30/02 10:15"
            target = pick(rng, [category, category, category.lower(), category.upper()])
            if rng.random() < 0.01:
                target = pick(rng, NULLS)
            out.append({"note_id": f"NT{id_base + index}", "query_reference": reference,
                        "payroll_centre": pick(rng, CENTRE_SPELLINGS[centre]),
                        "contact_channel": maybe_null(rng, pick(rng, CHANNEL_SPELLINGS[channel]), 0.04),
                        "note_source": pick(rng, ["First contact", "Follow-up", "follow up", "Officer update", "Callback",
                                                  "Closure note"]),
                        "note_sequence": str(sequence), "note_written_at": stamp, "note_text": raw,
                        "note_length_chars": str(length), "query_category": target})
            index += 1
            if index >= count:
                break
    frame = pd.DataFrame(out)
    duplicates = frame.sample(frac=0.03, random_state=rng.randint(0, 10**6))
    return pd.concat([frame, duplicates]).sample(frac=1, random_state=rng.randint(0, 10**6)).reset_index(drop=True)


# ----------------------------------------------------------------- live queue
SCENARIOS = ["Paid correctly", "Rostered hours paid", "Wrong classification applied", "Rate change date",
             "Traineeship overrun", "Crossed timesheets", "Faulty timesheet", "Venue transfer hours", "Deductions and tax",
             "Small difference"]


def make_open_queue(rng, count):
    rows, notes, used = [], [], set()
    example = {
        "query_id": "PQ900001", "query_reference": WORKED_EXAMPLE_REFERENCE, "employee_number": "EMP-41927003",
        "payroll_centre": "Sydney", "payroll_system": "Kestrel PayHub", "contact_channel": "Phone",
        "period_start_date": "01 Jan", "period_end_date": "31 Jan", "days_in_period": "31", "pay_frequency": "Monthly",
        "paid_classification": "Front of House Trainee", "entitled_classification": "Front of House Trainee",
        "traineeship_last_day": "09 Jan", "roster_type": "Standard", "electronic_timesheet_flag": "Yes",
        "hours_source_type": "Time clock", "ordinary_hours_paid": "152.50", "night_hours_paid": "",
        "total_hours_paid": "152.50", "amount_paid_aud": "3688.40", "consecutive_rostered_periods": "0",
        "days_since_last_clock_match": "4", "hours_change_vs_average_pct": "6", "classification_changes_in_period": "0",
        "traineeship_days_overrun": "22", "rate_changes_in_period": "0", "prior_queries_12m": "1", "tenure_months": "14",
        "contracted_hours_per_week": "35", "payment_method": "Bank transfer", "salary_packaging_aud": "",
        "recovery_balance_aud": "0.00", "venue_transfer_flag": "No", "interpreter_required_flag": "No",
        "pay_run_code": "PR-311", "weekday_raised": "Tuesday", "desk_code": "HRD-A1",
        "verified_hours_source": "Time clock export", "verified_ordinary_hours": "152.50", "verified_night_hours": "",
        "agreed_classification_not_applied_flag": "Yes", "rostered_without_clock_check_flag": "No",
        "timesheet_error_not_investigated_flag": "No", "_category": "Traineeship overrun",
    }
    rows.append(example)
    used.add(WORKED_EXAMPLE_REFERENCE)
    while len(rows) < count:
        scenario = pick(rng, SCENARIOS)
        centre = pick(rng, list(CENTRES))
        reference = f"PQR-{CENTRES[centre]}-{rng.randint(0, 9999999):07d}"
        if reference in used:
            continue
        used.add(reference)
        system = {"Sydney": "Kestrel PayHub", "Melbourne": "Harbour Payroll", "Brisbane": "Coastline Pay"}.get(centre) \
            or ("Kestrel PayHub" if rng.random() < 0.2 else "WestPay US")
        frequency = "Monthly" if rng.random() < 0.3 else "Fortnightly"
        start, end = period_for(rng, frequency)
        days = end - start + 1
        if scenario == "Traineeship overrun":
            entitled = pick(rng, list(MOVES_ONTO))
        elif scenario == "Rate change date":
            entitled = pick(rng, CLASSES)
        else:
            entitled = pick(rng, CLASSES)
        roster = "Day-night" if entitled == "Night Audit" else "Standard"
        last_day = None
        if entitled in MOVES_ONTO:
            if scenario == "Traineeship overrun":
                last_day = rng.randint(start, end - 1)
            elif rng.random() < 0.5:
                last_day = rng.randint(end, min(365, end + 120))
        if scenario == "Rate change date":
            # put the period across a window opening so the rate changes inside it
            openings = [DAY[w[0]] for w in RATE_WINDOWS[entitled] if DAY[w[0]] > 1]
            opening = pick(rng, openings)
            start = max(1, opening - rng.randint(1, days - 1))
            end = start + days - 1
            if end > 365:
                start, end = 365 - days + 1, 365
            if last_day is not None and last_day < start:
                last_day = None
        contracted = pick(rng, [20, 25, 30, 35, 38])
        verified = quarter(rng, contracted * days / 7 * 0.75, contracted * days / 7 * 1.2)
        verified_night = quarter(rng, 8, 40) if roster == "Day-night" else None
        owed, _pieces = true_pay(entitled, DATE[last_day] if last_day else None, start, end, verified, verified_night or 0)
        paid_class, paid_hours, paid_night = entitled, verified, verified_night
        flags = {"PC1": False, "PC2": False, "PC3": False}
        source, hours_source = "Time clock", pick(rng, ["Time clock export"] * 4 + ["Venue manager confirmation", "Payroll vendor audit"])
        amount = owed
        if scenario == "Rostered hours paid":
            source = "Rostered"
            paid_hours = max(Decimal(0), verified - quarter(rng, 3, 20) * (1 if rng.random() < 0.8 else -1))
            amount = owed - (verified - paid_hours) * Decimal("27.00")
            flags["PC2"] = rng.random() < 0.7
        elif scenario == "Wrong classification applied":
            choices = {"Front of House": "Front of House Trainee", "Kitchen": "Kitchen Trainee",
                       "Front of House Trainee": "Kitchen Trainee", "Kitchen Trainee": "Front of House Trainee"}
            if entitled in choices:
                paid_class = choices[entitled]
                amount = flat_pay(paid_class, start, days, verified, 0)
            else:
                amount = owed - Decimal(rng.randint(2000, 15000)) / 100
            flags["PC1"] = rng.random() < 0.75
        elif scenario == "Rate change date":
            amount = flat_pay(entitled, start, days, verified, verified_night or 0) if entitled not in MOVES_ONTO or last_day is None \
                else owed - Decimal(rng.randint(500, 6000)) / 100
        elif scenario == "Traineeship overrun":
            amount = flat_pay(entitled, start, days, verified, 0)
            flags["PC1"] = rng.random() < 0.6
        elif scenario == "Crossed timesheets":
            delta = quarter(rng, 4, 24) * pick(rng, [1, -1])
            paid_hours = max(Decimal(0), verified + delta)
            amount = owed + delta * Decimal("26.50")
            source = "Time clock"
        elif scenario == "Faulty timesheet":
            source = "Timesheet"
            delta = quarter(rng, 2, 16) * pick(rng, [1, -1, -1])
            paid_hours = max(Decimal(0), verified + delta)
            amount = owed + delta * Decimal("25.80")
            flags["PC3"] = rng.random() < 0.5
        elif scenario == "Venue transfer hours":
            delta = quarter(rng, 4, 22)
            paid_hours = max(Decimal(0), verified - delta)
            amount = owed - delta * Decimal("26.90")
        elif scenario == "Small difference":
            amount = owed + Decimal(pick(rng, [-87, -40, -3, 2, 15, 64, 99])) / 100
        amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount < 0:
            amount = Decimal("0.00")
        category = scenario if scenario in config.QUERY_CATEGORIES else pick(rng, ["Deductions and tax", "Rostered hours paid",
                                                                                     "Faulty timesheet"])
        overrun = ""
        if last_day is not None and last_day < end:
            overrun = str(end - last_day) if paid_class in MOVES_ONTO and scenario == "Traineeship overrun" else "0"
        rate_changes = sum(1 for w in RATE_WINDOWS[paid_class] if start < DAY[w[0]] <= end)
        tenure = rng.randint(2, 160)
        rows.append({
            "query_id": f"PQ{900002 + len(rows)}", "query_reference": reference,
            "employee_number": f"EMP-{rng.randint(10000000, 99999999)}", "payroll_centre": centre,
            "payroll_system": system, "contact_channel": pick(rng, list(CHANNEL_SPELLINGS)),
            "period_start_date": DATE[start], "period_end_date": DATE[end], "days_in_period": str(days),
            "pay_frequency": frequency, "paid_classification": paid_class, "entitled_classification": entitled,
            "traineeship_last_day": DATE[last_day] if last_day else "", "roster_type": roster,
            "electronic_timesheet_flag": "Yes" if source != "Timesheet" or rng.random() < 0.3 else "No",
            "hours_source_type": source, "ordinary_hours_paid": f"{paid_hours:.2f}",
            "night_hours_paid": f"{paid_night:.2f}" if paid_night is not None else "",
            "total_hours_paid": f"{paid_hours + (paid_night or 0):.2f}", "amount_paid_aud": f"{amount:.2f}",
            "consecutive_rostered_periods": str(rng.randint(1, 6) if source == "Rostered" else 0),
            "days_since_last_clock_match": str(rng.randint(0, 8) if source == "Time clock" else rng.randint(10, 80)),
            "hours_change_vs_average_pct": "" if tenure < 6 else str(rng.randint(-30, 40)),
            "classification_changes_in_period": "1" if scenario == "Traineeship overrun" and rng.random() < 0.4 else "0",
            "traineeship_days_overrun": overrun, "rate_changes_in_period": str(rate_changes),
            "prior_queries_12m": str(min(5, int(rng.expovariate(1.2)))), "tenure_months": str(tenure),
            "contracted_hours_per_week": str(contracted),
            "payment_method": pick(rng, ["Bank transfer"] * 6 + ["Pay card", "Cheque"]),
            "salary_packaging_aud": f"{Decimal(rng.randint(3000, 20000)) / 100:.2f}" if rng.random() < 0.25 else "",
            "recovery_balance_aud": f"{Decimal(rng.randint(-30000, 40000)) / 100:.2f}" if rng.random() < 0.2 else "0.00",
            "venue_transfer_flag": "Yes" if scenario == "Venue transfer hours" else "No",
            "interpreter_required_flag": "Yes" if rng.random() < 0.08 else "No",
            "pay_run_code": f"PR-{rng.randint(100, 999)}", "weekday_raised": pick(rng, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
            "desk_code": pick(rng, ["HRD-A1", "HRD-A2", "HRD-B1"]),
            "verified_hours_source": hours_source, "verified_ordinary_hours": f"{verified:.2f}",
            "verified_night_hours": f"{verified_night:.2f}" if verified_night is not None else "",
            "agreed_classification_not_applied_flag": "Yes" if flags["PC1"] else "No",
            "rostered_without_clock_check_flag": "Yes" if flags["PC2"] else "No",
            "timesheet_error_not_investigated_flag": "Yes" if flags["PC3"] else "No",
            "_category": category,
        })
    note_index = 0
    for row in rows:
        category = row.pop("_category")
        count_notes = 3 if row["query_reference"] == WORKED_EXAMPLE_REFERENCE else rng.randint(1, 4)
        for sequence in range(1, count_notes + 1):
            named = category if rng.random() > 0.12 else pick(rng, config.QUERY_CATEGORIES)
            text = note_text(rng, named).replace("...", "").strip()
            if rng.random() < 0.05 and count_notes > 1:
                text = pick(rng, ["left voicemail", "no answer", "chased"])
            day = min(365, config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE[row["period_end_date"]] + sequence)
            notes.append({"note_id": f"NO{700000 + note_index}", "query_reference": row["query_reference"],
                          "payroll_centre": row["payroll_centre"], "contact_channel": row["contact_channel"],
                          "note_source": ["First contact", "Follow-up", "Officer update", "Callback"][min(sequence - 1, 3)],
                          "note_sequence": str(sequence),
                          "note_written_at": f"{DATE[day]} {rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}",
                          "note_text": text})
            note_index += 1
    queue = pd.DataFrame(rows)
    notes_frame = pd.DataFrame(notes).sample(frac=1, random_state=7).reset_index(drop=True)
    return queue, notes_frame


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--small", action="store_true", help="a quarter of the rows")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    arguments = parser.parse_args()
    os.chdir(PROJECT)
    targets = [config.RAW_QUERIES_TRAIN_FILE, config.RAW_QUERIES_EVAL_FILE, config.RAW_EFFORT_TRAIN_FILE,
               config.RAW_EFFORT_EVAL_FILE, config.RAW_QUERY_NOTES_FILE, config.OPEN_QUERIES_FILE, config.OPEN_QUERY_NOTES_FILE]
    if all(os.path.exists(t) for t in targets) and not arguments.force:
        print("demo data already present; use --force to rebuild")
        return
    scale = 0.25 if arguments.small else 1.0
    rng = random.Random(config.RANDOM_SEED)
    os.makedirs(os.path.join("data", "input"), exist_ok=True)
    jobs = [
        (config.RAW_QUERIES_TRAIN_FILE, lambda n: dirty_query_frame(rng, make_query_rows(rng, n, 200000)), 23880),
        (config.RAW_QUERIES_EVAL_FILE, lambda n: dirty_query_frame(rng, make_query_rows(rng, n, 300000)), 5970),
        (config.RAW_EFFORT_TRAIN_FILE, lambda n: make_effort_frame(rng, n, 300000), 21790),
        (config.RAW_EFFORT_EVAL_FILE, lambda n: make_effort_frame(rng, n, 400000), 5447),
        (config.RAW_QUERY_NOTES_FILE, lambda n: make_notes_frame(rng, n, 500000), 27730),
    ]
    for path, build, rows in jobs:
        frame = build(int(rows * scale))
        frame.to_csv(path, index=False)
        print(f"wrote {path:45s} {len(frame):6d} rows")
    queue, notes = make_open_queue(rng, 350)
    queue.to_csv(config.OPEN_QUERIES_FILE, index=False)
    notes.to_csv(config.OPEN_QUERY_NOTES_FILE, index=False)
    print(f"wrote {config.OPEN_QUERIES_FILE:45s} {len(queue):6d} rows")
    print(f"wrote {config.OPEN_QUERY_NOTES_FILE:45s} {len(notes):6d} rows")


if __name__ == "__main__":
    main()
