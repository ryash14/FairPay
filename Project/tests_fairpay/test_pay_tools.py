from decimal import Decimal

import pytest

from config import config
from tools import pay_tools
from tools.query_data_tools import fetch_query_profile

EXAMPLE = "PQR-SYD-0041927"


def test_schedules_are_read_from_their_own_documents(schedules):
    assert set(schedules) == set(config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION)
    for schedule in schedules.values():
        assert schedule["rate_windows"][0]["opens_on"] == config.FINANCIAL_YEAR_DATES[0]
    assert "night_rate_aud" in schedules["Night Audit"]["rate_windows"][0]


def test_worked_example_splits_into_three_pieces_and_rounds_once(open_queries, schedules):
    profile = fetch_query_profile(open_queries, EXAMPLE)
    pieces = pay_tools.build_pay_pieces(profile, schedules)
    assert [(p["first_day"], p["last_day"], p["days"]) for p in pieces] == \
        [("01 Jan", "09 Jan", 9), ("10 Jan", "17 Jan", 8), ("18 Jan", "31 Jan", 14)]
    priced = pay_tools.compute_entitled_pay(pieces, pay_tools.measure_hours(profile))
    assert [p["hours"] for p in priced["pieces"]] == [Decimal("44.27"), Decimal("39.35"), Decimal("68.87")]
    comparison = pay_tools.compare_with_paid(profile, priced["entitled_pay_aud"])
    assert comparison["difference_aud"] == comparison["entitled_pay_aud"] - Decimal("3688.40")
    assert comparison["direction"] == config.UNDERPAID and comparison["correction_warranted"]


def test_illustrative_rates_give_the_published_figure():
    illustrative = {
        "Front of House Trainee": {"rate_windows": [{"opens_on": "01 Jul", "ordinary_rate_aud": Decimal("22.10"),
                                                     "site_allowance_aud": Decimal("1.80")}], "moves_onto": "Front of House"},
        "Front of House": {"rate_windows": [
            {"opens_on": "01 Jul", "ordinary_rate_aud": Decimal("26.05"), "site_allowance_aud": Decimal("2.20")},
            {"opens_on": "18 Jan", "ordinary_rate_aud": Decimal("26.73"), "site_allowance_aud": Decimal("2.37")}],
            "moves_onto": None},
    }
    profile = {config.PERIOD_START_COLUMN: "01 Jan", config.PERIOD_END_COLUMN: "31 Jan",
               config.ENTITLED_CLASSIFICATION_COLUMN: "Front of House Trainee", config.TRAINEESHIP_LAST_DAY_COLUMN: "09 Jan"}
    pieces = pay_tools.build_pay_pieces(profile, illustrative)
    priced = pay_tools.compute_entitled_pay(pieces, {"total_hours": Decimal("152.50")})
    assert [p["pay_aud"] for p in priced["pieces"]] == [Decimal("994.66"), Decimal("1042.79"), Decimal("1874.10")]
    assert priced["entitled_pay_aud"] == Decimal("3911.55")


def test_hours_must_be_quarters_and_fit():
    base = {config.ROSTER_TYPE_COLUMN: "Standard", config.DAYS_IN_PERIOD_COLUMN: "14"}
    with pytest.raises(ValueError, match="quarter"):
        pay_tools.measure_hours({**base, config.VERIFIED_ORDINARY_HOURS_COLUMN: "10.1"})
    with pytest.raises(ValueError, match="do not fit"):
        pay_tools.measure_hours({**base, config.VERIFIED_ORDINARY_HOURS_COLUMN: "400"})


def test_overpayment_corrected_like_underpayment():
    profile = {config.AMOUNT_PAID_COLUMN: "1001.00"}
    result = pay_tools.compare_with_paid(profile, Decimal("1000.00"))
    assert result["direction"] == config.OVERPAID and result["correction_warranted"]
    small = pay_tools.compare_with_paid({config.AMOUNT_PAID_COLUMN: "1000.99"}, Decimal("1000.00"))
    assert not small["correction_warranted"]
    with pytest.raises(ValueError, match="dollars and cents"):
        pay_tools.compare_with_paid({config.AMOUNT_PAID_COLUMN: "1000"}, Decimal("1000.00"))


def test_settlement_by_decision():
    assert pay_tools.compute_settled_amount(config.DECISION_UPHOLD_PAY, Decimal("5.00"), Decimal("0.00")) is None
    paid = pay_tools.compute_settled_amount(config.DECISION_CORRECT_AND_COMPENSATE, Decimal("515.07"), Decimal("150.00"))
    assert paid["settled_amount_aud"] == Decimal("665.07") and paid["direction"] == config.SETTLEMENT_PAID_TO_EMPLOYEE
    recovered = pay_tools.compute_settled_amount(config.DECISION_CORRECT_PAY, Decimal("-20.00"), Decimal("150.00"))
    assert recovered["direction"] == config.SETTLEMENT_RECOVERED and recovered["amount_to_settle_aud"] == Decimal("20.00")


def test_queue_ranked_by_money_at_stake(open_queries, schedules):
    ranked = pay_tools.rank_query_queue(open_queries, schedules)
    stakes = [row["money_at_stake_aud"] for row in ranked]
    assert stakes == sorted(stakes, reverse=True) and len(ranked) == len(open_queries)
