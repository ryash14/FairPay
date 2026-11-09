"""Repairs shared by the cleaning runs and their profilers.

Every function takes a table and returns a repaired copy; the table it was
given is never changed, and no column is added or removed. A value in a
notation a function does not recognise is refused with a ValueError naming
the column and listing, sorted, the distinct values that could not be read.
"""
import html
import re

import numpy as np
import pandas as pd

from config import config


# ----------------------------------------------------------------- internals
def _is_missing(value):
    return value is None or value is pd.NA or (isinstance(value, float) and np.isnan(value)) or \
        (not isinstance(value, str) and pd.isna(value))


def _text(value):
    return value if isinstance(value, str) else str(value)


def _refuse(column, what, values):
    listed = sorted({_text(v) for v in values})
    raise ValueError(f"{column} holds {what}: {listed}")


def _groups(match):
    return [g for g in match.groups()]


# ----------------------------------------------------------------- rows
def remove_duplicate_records(dataframe):
    """Keep the first of every set of rows identical in every column."""
    return dataframe.drop_duplicates(keep="first").reset_index(drop=True)


def remove_rows_missing_target(dataframe, target_column):
    """Drop every row with no answer; nothing is ever invented in its place."""
    return dataframe[dataframe[target_column].notna()].reset_index(drop=True)


# ----------------------------------------------------------------- categories
def normalize_category_values(dataframe, value_mappings):
    """Fold every spelling of a business value onto its one canonical value."""
    frame = dataframe.copy()
    for column, mapping in value_mappings.items():
        if column not in frame.columns:
            continue
        values = frame[column]
        unknown = set()
        folded = []
        for value in values:
            if _is_missing(value):
                folded.append(np.nan)
                continue
            key = _text(value).strip().lower()
            if key in mapping:
                folded.append(mapping[key])
            else:
                unknown.add(_text(value))
                folded.append(np.nan)
        if unknown:
            _refuse(column, "values with no canonical spelling", unknown)
        frame[column] = pd.Series(folded, index=frame.index, dtype=object)
    return frame


# ----------------------------------------------------------------- dates
def _read_date(value, month_first):
    """Return a financial-year day number, pd.NA for a day the calendar lacks, or raise KeyError if unreadable."""
    text = _text(value).strip().lower()
    numeric = re.fullmatch(config.NUMERIC_DATE_PATTERN, text)
    if numeric:
        if month_first is None or month_first is pd.NA:
            raise KeyError(text)
        first, second = (int(g) for g in _groups(numeric)[:2])
        month_number, day = (first, second) if bool(month_first) else (second, first)
        if month_number not in config.MONTH_BY_NUMBER:
            raise KeyError(text)
        month = config.MONTH_BY_NUMBER[month_number]
    else:
        worded = re.fullmatch(config.WORDED_DATE_PATTERN, text)
        if not worded:
            raise KeyError(text)
        day_text, month_word = _groups(worded)[:2]
        if month_word not in config.MONTH_NAME_MAPPING:
            raise KeyError(text)
        day = int(day_text)
        month = config.MONTH_NAME_MAPPING[month_word]
    return config.DAY_NUMBER_BY_FINANCIAL_YEAR_DATE.get(f"{day:02d} {month}", pd.NA)


def parse_financial_year_dates(dataframe, date_columns, month_first_rows):
    """Turn every date notation into its day number in the financial year (01 Jul is day 1)."""
    frame = dataframe.copy()
    flags = month_first_rows.reindex(frame.index)
    for column in date_columns:
        unreadable = set()
        numbers = []
        for row_index, value in frame[column].items():
            if _is_missing(value):
                numbers.append(pd.NA)
                continue
            flag = flags.loc[row_index]
            try:
                numbers.append(_read_date(value, None if pd.isna(flag) else bool(flag)))
            except KeyError:
                unreadable.add(_text(value))
                numbers.append(pd.NA)
        if unreadable:
            _refuse(column, "dates that cannot be read", unreadable)
        frame[column] = pd.array(numbers, dtype="Int64")
    return frame


def format_financial_year_dates(dataframe, date_columns):
    """Write day numbers back as DD Mon."""
    frame = dataframe.copy()
    for column in date_columns:
        frame[column] = pd.Series(
            [np.nan if _is_missing(v) else config.FINANCIAL_YEAR_DATE_BY_DAY_NUMBER[int(v)] for v in frame[column]],
            index=frame.index, dtype=object)
    return frame


# ----------------------------------------------------------------- money
def convert_money_amounts(dataframe, money_columns):
    """Dollars as floats, credits negative."""
    frame = dataframe.copy()
    for column in money_columns:
        unreadable = set()
        amounts = []
        for value in frame[column]:
            if _is_missing(value):
                amounts.append(np.nan)
                continue
            text = _text(value).strip().lower()
            if not re.fullmatch(config.MONEY_NOTATION_PATTERN, text):
                unreadable.add(_text(value))
                amounts.append(np.nan)
                continue
            amount = float(re.sub(config.MONEY_SYMBOL_PATTERN, "", text))
            if re.search(config.CREDIT_NOTATION_PATTERN, text):
                amount = -abs(amount)
            amounts.append(amount)
        if unreadable:
            _refuse(column, "money in no known notation", unreadable)
        frame[column] = pd.Series(amounts, index=frame.index, dtype=float)
    return frame


# ----------------------------------------------------------------- hours
def convert_hours_worked(dataframe, hours_columns):
    """Decimal hours, every figure a whole number of quarter hours."""
    frame = dataframe.copy()
    for column in hours_columns:
        unreadable, not_quarters = set(), set()
        converted = []
        for value in frame[column]:
            if _is_missing(value):
                converted.append(np.nan)
                continue
            text = _text(value).strip().lower()
            match = re.fullmatch(config.HOURS_WORKED_PATTERN, text)
            if not match:
                unreadable.add(_text(value))
                converted.append(np.nan)
                continue
            groups = _groups(match)
            amount = groups[0]
            unit = groups[-1] if len(groups) > 1 else None
            hours = float(amount.replace(config.DIGIT_GROUPING_SEPARATOR, ""))
            if unit:
                hours *= config.HOURS_UNIT_FACTORS[unit]
            hours = round(hours, config.UNIT_CONVERSION_DECIMALS)
            if not round(hours * config.QUARTER_HOURS_PER_HOUR, 6).is_integer():
                not_quarters.add(_text(value))
            converted.append(hours)
        if unreadable:
            _refuse(column, "hours in no known notation", unreadable)
        if not_quarters:
            _refuse(column, "hours that are not whole quarter hours", not_quarters)
        frame[column] = pd.Series(converted, index=frame.index, dtype=float)
    return frame


def convert_durations_to_hours(dataframe, duration_columns):
    """'2h 15m', '135 min', '2.25 h' and '2.25' all become 2.25."""
    frame = dataframe.copy()
    for column in duration_columns:
        unreadable = set()
        converted = []
        for value in frame[column]:
            if _is_missing(value):
                converted.append(np.nan)
                continue
            text = _text(value).strip().lower()
            both = re.fullmatch(config.HOURS_AND_MINUTES_PATTERN, text)
            minutes = re.fullmatch(config.MINUTES_UNIT_PATTERN, text)
            hours = re.fullmatch(config.HOURS_UNIT_PATTERN, text)
            plain = re.fullmatch(config.PLAIN_NUMBER_PATTERN, text)
            if both:
                hour_part, minute_part = _groups(both)[:2]
                converted.append(float(hour_part) + float(minute_part) / config.MINUTES_PER_HOUR)
            elif minutes:
                converted.append(float(_groups(minutes)[0]) / config.MINUTES_PER_HOUR)
            elif hours:
                converted.append(float(_groups(hours)[0]))
            elif plain:
                converted.append(float(text))
            else:
                unreadable.add(_text(value))
                converted.append(np.nan)
        if unreadable:
            _refuse(column, "durations in no known notation", unreadable)
        frame[column] = pd.Series(converted, index=frame.index, dtype=float)
    return frame


# ----------------------------------------------------------------- counts
def convert_counts_with_units(dataframe, count_patterns):
    """'3 letters' becomes 3; another column's unit is refused."""
    frame = dataframe.copy()
    for column, pattern in count_patterns.items():
        unreadable = set()
        counts = []
        for value in frame[column]:
            if _is_missing(value):
                counts.append(pd.NA)
                continue
            match = re.fullmatch(pattern, _text(value).strip().lower())
            if not match:
                unreadable.add(_text(value))
                counts.append(pd.NA)
                continue
            counts.append(int(_groups(match)[0]))
        if unreadable:
            _refuse(column, "counts in no known notation", unreadable)
        frame[column] = pd.array(counts, dtype="Int64")
    return frame


def convert_whole_numbers(dataframe, whole_number_columns):
    """Counts, day figures and percentages as whole numbers that can still hold a gap."""
    frame = dataframe.copy()
    for column in whole_number_columns:
        unreadable = set()
        numbers = []
        for value in frame[column]:
            if _is_missing(value):
                numbers.append(pd.NA)
                continue
            text = _text(value).strip()
            if not re.fullmatch(config.PLAIN_NUMBER_PATTERN, text) or not float(text).is_integer():
                unreadable.add(_text(value))
                numbers.append(pd.NA)
                continue
            numbers.append(int(float(text)))
        if unreadable:
            _refuse(column, "values that are not whole numbers", unreadable)
        frame[column] = pd.array(numbers, dtype="Int64")
    return frame


# ----------------------------------------------------------------- text
def convert_markup_to_plain_text(dataframe, text_columns):
    """Plain words, whatever markup or escaping the storing tool added."""
    frame = dataframe.copy()
    for column in text_columns:
        plain = []
        for value in frame[column]:
            if _is_missing(value):
                plain.append(np.nan)
                continue
            text = re.sub(config.MARKUP_PATTERN, " ", _text(value))
            text = html.unescape(text).replace(config.NO_BREAK_SPACE, " ")
            text = re.sub(config.WHITESPACE_RUN_PATTERN, " ", text).strip()
            plain.append(text)
        frame[column] = pd.Series(plain, index=frame.index, dtype=object)
    return frame


# ----------------------------------------------------------------- ranges
def treat_out_of_range_as_missing(dataframe, range_limits):
    """Empty any figure nothing real could produce; keep the row."""
    frame = dataframe.copy()
    for column, (lowest, highest) in range_limits.items():
        values = frame[column]
        outside = values.notna() & ((values < lowest) | (values > highest))
        frame[column] = values.mask(outside.fillna(False).astype(bool))
    return frame
