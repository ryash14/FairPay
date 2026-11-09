"""Evidence of how dirty each extract was and what cleaning did to it.

Every figure is measured from the tables themselves, never copied from the
cleaning code's counters. Counts are plain ints and shares plain floats so the
report can be written as JSON.
"""
import json
import os
import re

import pandas as pd

from config import config
from data_pipeline.common_cleaning import (convert_counts_with_units, convert_durations_to_hours, convert_hours_worked,
                                           convert_markup_to_plain_text, convert_whole_numbers,
                                           normalize_category_values, parse_financial_year_dates)


def _missing_by_column(frame):
    counts = frame.isna().sum()
    return {str(column): int(count) for column, count in counts.items() if int(count) > 0}


def _first_copies(frame):
    return frame[~frame.duplicated(keep="first")]


def _matches(series, pattern, lower=False):
    def test(value):
        if not isinstance(value, str):
            return False
        return re.fullmatch(pattern, value.lower() if lower else value) is not None
    return series.map(test)


def _shares(series):
    counts = series.value_counts(dropna=True)
    total = int(counts.sum())
    return {str(value): round(float(count) / total, 4) for value, count in counts.items()} if total else {}


def profile_dataset(raw_frame, clean_frame, target_column):
    """Account for every row received and every empty cell before and after cleaning."""
    first = _first_copies(raw_frame)
    return {
        "rows_received": int(len(raw_frame)),
        "rows_kept": int(len(clean_frame)),
        "rows_removed": int(len(raw_frame) - len(clean_frame)),
        "duplicate_rows": int(raw_frame.duplicated(keep="first").sum()),
        "rows_missing_target": int(first[target_column].isna().sum()),
        "columns": int(clean_frame.shape[1]),
        "missing_cells_as_received": _missing_by_column(raw_frame),
        "missing_cells_after_cleaning": _missing_by_column(clean_frame),
    }


def _period_counts(frame):
    start, end = frame[config.PERIOD_START_COLUMN], frame[config.PERIOD_END_COLUMN]
    days = frame[config.DAYS_IN_PERIOD_COLUMN]
    both = start.notna() & end.notna()
    reversed_rows = int((both & (end < start)).fillna(False).sum())
    all_known = both & days.notna()
    disagreeing = int((all_known & (days != (end - start + 1))).fillna(False).sum())
    day_night = (frame[config.ROSTER_TYPE_COLUMN] == config.DAY_NIGHT_ROSTER_TYPE).fillna(False).astype(bool)
    ordinary = frame[config.ORDINARY_HOURS_COLUMN].astype(float)
    night = frame[config.NIGHT_HOURS_COLUMN].astype(float)
    parts = ordinary.where(~day_night, ordinary + night)
    total = frame[config.TOTAL_HOURS_COLUMN].astype(float)
    equal = (parts.round(6) == total.round(6)) & parts.notna() & total.notna()
    return reversed_rows, disagreeing, int((~equal).sum())


def profile_query_details(raw_frame, clean_frame):
    """The defects peculiar to the pay query extracts, as received and after cleaning."""
    folded = normalize_category_values(raw_frame, {config.PAYROLL_SYSTEM_COLUMN: config.PAYROLL_SYSTEM_MAPPING,
                                                   config.ROSTER_TYPE_COLUMN: config.ROSTER_TYPE_MAPPING})
    month_first = folded[config.PAYROLL_SYSTEM_COLUMN].map(config.MONTH_FIRST_BY_PAYROLL_SYSTEM).astype("boolean")
    received = parse_financial_year_dates(folded, config.QUERY_DATE_COLUMNS, month_first)
    received = convert_hours_worked(received, config.QUERY_HOURS_COLUMNS)
    received = convert_whole_numbers(received, config.QUERY_WHOLE_NUMBER_COLUMNS)

    cleaned = parse_financial_year_dates(clean_frame, config.QUERY_DATE_COLUMNS,
                                         pd.Series(False, index=clean_frame.index, dtype="boolean"))

    not_standard = month_first_count = impossible = 0
    for column in config.QUERY_DATE_COLUMNS:
        raw = raw_frame[column]
        present = raw.notna()
        not_standard += int((present & ~_matches(raw, config.STANDARD_DATE_PATTERN)).sum())
        numeric = _matches(raw, config.NUMERIC_DATE_PATTERN, lower=True)
        month_first_count += int((numeric & month_first.fillna(False).astype(bool)).sum())
        impossible += int((present & received[column].isna()).sum())

    plain_columns = list(config.QUERY_MONEY_COLUMNS) + list(config.QUERY_HOURS_COLUMNS)
    not_plain = {column: int((raw_frame[column].notna() & ~_matches(raw_frame[column], config.PLAIN_NUMBER_PATTERN)).sum())
                 for column in plain_columns}
    credits = {column: int(raw_frame[column].map(
        lambda v: isinstance(v, str) and re.search(config.CREDIT_NOTATION_PATTERN, v.lower()) is not None).sum())
        for column in config.QUERY_MONEY_COLUMNS}
    out_of_range = {}
    for column, (lowest, highest) in config.QUERY_RANGE_LIMITS.items():
        values = received[column]
        out_of_range[column] = int((values.notna() & ((values < lowest) | (values > highest))).fillna(False).sum())

    reversed_raw, days_raw, hours_raw = _period_counts(received)
    reversed_clean, days_clean, hours_clean = _period_counts(cleaned)
    return {
        "dates_not_in_standard_form": int(not_standard),
        "dates_written_month_first": int(month_first_count),
        "dates_impossible_in_the_calendar": int(impossible),
        "values_not_written_as_plain_numbers": not_plain,
        "money_written_as_credits": credits,
        "out_of_range_by_column": out_of_range,
        "target_shares": _shares(clean_frame[config.QUERY_TARGET_COLUMN]),
        "periods_ending_before_they_start_as_received": reversed_raw,
        "periods_ending_before_they_start_after_cleaning": reversed_clean,
        "days_in_period_disagreeing_with_dates_as_received": days_raw,
        "days_in_period_disagreeing_with_dates_after_cleaning": days_clean,
        "total_hours_disagreeing_with_parts_as_received": hours_raw,
        "total_hours_disagreeing_with_parts_after_cleaning": hours_clean,
    }


def profile_effort_details(raw_frame, clean_frame):
    """The defects peculiar to the effort extracts, impossible remediation hours above all."""
    received = convert_durations_to_hours(raw_frame, config.EFFORT_DURATION_COLUMNS)
    received = convert_counts_with_units(received, config.EFFORT_COUNT_WITH_UNIT_PATTERNS)
    received = convert_whole_numbers(received, config.EFFORT_WHOLE_NUMBER_COLUMNS)
    not_standard = 0
    for column in config.EFFORT_DATE_COLUMNS:
        raw = raw_frame[column]
        not_standard += int((raw.notna() & ~_matches(raw, config.STANDARD_DATE_PATTERN)).sum())
    plain_columns = list(config.EFFORT_DURATION_COLUMNS) + list(config.EFFORT_COUNT_WITH_UNIT_PATTERNS)
    not_plain = {column: int((raw_frame[column].notna() & ~_matches(raw_frame[column], config.PLAIN_NUMBER_PATTERN)).sum())
                 for column in plain_columns}
    out_of_range = {}
    for column, (lowest, highest) in config.EFFORT_RANGE_LIMITS.items():
        values = received[column]
        out_of_range[column] = int((values.notna() & ((values < lowest) | (values > highest))).fillna(False).sum())
    first = ~raw_frame.duplicated(keep="first")
    target = received[config.EFFORT_TARGET_COLUMN]
    lowest, highest = config.EFFORT_RANGE_LIMITS[config.EFFORT_TARGET_COLUMN]
    impossible = int((first & target.notna() & ((target < lowest) | (target > highest))).sum())
    return {
        "dates_not_in_standard_form": int(not_standard),
        "values_not_written_as_plain_numbers": not_plain,
        "out_of_range_by_column": out_of_range,
        "rows_with_impossible_target": impossible,
        "median_remediation_hours": float(clean_frame[config.EFFORT_TARGET_COLUMN].median()),
    }


def profile_note_details(raw_frame, clean_frame):
    """The defects peculiar to free-text notes, as received and after cleaning."""
    text = config.NOTE_TEXT_COLUMN
    plain = convert_markup_to_plain_text(raw_frame, [text])[text]
    raw_text = raw_frame[text]

    def found(pattern):
        return int(raw_text.map(lambda v: isinstance(v, str) and re.search(pattern, v) is not None).sum())

    capitals = int(plain.map(lambda v: isinstance(v, str) and v == v.upper() and v != v.lower()).sum())
    recorded = pd.to_numeric(raw_frame[config.NOTE_LENGTH_COLUMN], errors="coerce")
    lengths = plain.map(lambda v: len(v) if isinstance(v, str) else 0)
    disagree_raw = int((recorded != lengths).sum())
    disagree_clean = int((clean_frame[config.NOTE_LENGTH_COLUMN] != clean_frame[text].map(len)).sum())
    words = plain.map(lambda v: len(v.split()) if isinstance(v, str) else 0)
    first = ~raw_frame.duplicated(keep="first")
    too_few = int((first & raw_frame[config.NOTE_TARGET_COLUMN].notna() & (words < config.MINIMUM_NOTE_WORDS)).sum())
    stamps = raw_frame[config.NOTE_TIMESTAMP_COLUMN]
    not_standard = int((stamps.notna() & ~_matches(stamps, config.STANDARD_TIMESTAMP_PATTERN)).sum())
    return {
        "timestamps_not_in_standard_form": not_standard,
        "notes_with_markup": found(config.MARKUP_PATTERN),
        "notes_with_encoding_artifacts": found(config.ENCODING_ARTIFACT_PATTERN),
        "notes_in_capitals": capitals,
        "note_lengths_disagreeing_with_plain_text_as_received": disagree_raw,
        "note_lengths_disagreeing_with_plain_text_after_cleaning": disagree_clean,
        "rows_with_too_few_words": too_few,
        "shortest_note_words": int(clean_frame[text].map(lambda v: len(v.split())).min()),
        "target_shares": _shares(clean_frame[config.NOTE_TARGET_COLUMN]),
    }


def write_quality_report(profiles, file_path):
    """Two-space indented JSON with sorted keys, so the same profiles always give the same file."""
    folder = os.path.dirname(file_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(profiles, handle, indent=2, sort_keys=True)
