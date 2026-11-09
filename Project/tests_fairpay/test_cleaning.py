import numpy as np
import pandas as pd
import pytest

from config import config
from data_pipeline import common_cleaning as cc


def frame(**columns):
    return pd.DataFrame({k: pd.Series(v, dtype=object) for k, v in columns.items()})


def test_duplicates_keep_first_and_renumber():
    f = frame(a=["1", "1", "2"], b=["x", "x", "y"])
    out = cc.remove_duplicate_records(f)
    assert list(out.index) == [0, 1] and len(out) == 2


def test_categories_fold_and_refuse_unknown():
    f = frame(payroll_centre=["Melb", "SYD", np.nan])
    out = cc.normalize_category_values(f, {"payroll_centre": config.PAYROLL_CENTRE_MAPPING})
    assert list(out["payroll_centre"][:2]) == ["Melbourne", "Sydney"] and pd.isna(out["payroll_centre"][2])
    with pytest.raises(ValueError, match="no canonical spelling"):
        cc.normalize_category_values(frame(payroll_centre=["Atlantis"]), {"payroll_centre": config.PAYROLL_CENTRE_MAPPING})


def test_dates_by_system_order_and_impossible_days():
    f = frame(d=["4/8", "4/8", "20 Mar", "30 Feb", "1 february"])
    flags = pd.Series([True, False, False, False, True], dtype="boolean")
    out = cc.parse_financial_year_dates(f, ["d"], flags)
    days = config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE
    assert out["d"][0] == days["08 Apr"] and out["d"][1] == days["04 Aug"] and out["d"][2] == days["20 Mar"]
    assert pd.isna(out["d"][3]) and out["d"][4] == days["01 Feb"]
    back = cc.format_financial_year_dates(out, ["d"])
    assert back["d"][0] == "08 Apr"


def test_numeric_date_without_system_is_refused():
    with pytest.raises(ValueError, match="cannot be read"):
        cc.parse_financial_year_dates(frame(d=["3/4"]), ["d"], pd.Series([pd.NA], dtype="boolean"))


def test_money_notations_and_credits():
    f = frame(m=["$1,221.46", "aud 2,088.78", "0.00 AUD", "$450.00 CR", "(12.30)", "-5.00"])
    out = cc.convert_money_amounts(f, ["m"])["m"].tolist()
    assert out == [1221.46, 2088.78, 0.0, -450.0, -12.3, -5.0]
    with pytest.raises(ValueError, match="no known notation"):
        cc.convert_money_amounts(frame(m=["450.00 USD"]), ["m"])


def test_hours_units_and_quarter_rule():
    out = cc.convert_hours_worked(frame(h=["72.25 h", "2970 min", "5,220 min", "87"]), ["h"])["h"].tolist()
    assert out == [72.25, 49.5, 87.0, 87.0]
    with pytest.raises(ValueError, match="quarter hours"):
        cc.convert_hours_worked(frame(h=["125 min"]), ["h"])


def test_durations_counts_whole_numbers():
    assert cc.convert_durations_to_hours(frame(d=["2h 15m", "135 min", "2.25 h", "2.25"]), ["d"])["d"].tolist() == [2.25] * 4
    counts = cc.convert_counts_with_units(frame(letters_sent_count=["3 letters", "1 letter", "4"]),
                                          {"letters_sent_count": config.EFFORT_COUNT_WITH_UNIT_PATTERNS["letters_sent_count"]})
    assert counts["letters_sent_count"].tolist() == [3, 1, 4]
    with pytest.raises(ValueError):
        cc.convert_whole_numbers(frame(n=["3.5"]), ["n"])


def test_markup_becomes_plain_text():
    out = cc.convert_markup_to_plain_text(frame(t=["<b>Pay</b>&amp;&#39;hours\u00a0lost  "]), ["t"])
    assert out["t"][0] == "Pay &'hours lost"
