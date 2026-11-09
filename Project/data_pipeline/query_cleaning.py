"""The whole cleaning run for one pay query extract.

Besides the shared repairs it fixes what only this extract gets wrong: periods
written last day first, day counts that disagree with their dates, and totals
of hours that disagree with the hours they are made of.
"""

from config import config
from data_pipeline.common_cleaning import (convert_hours_worked, convert_money_amounts, convert_whole_numbers,
                                           format_financial_year_dates, normalize_category_values,
                                           parse_financial_year_dates, remove_duplicate_records,
                                           remove_rows_missing_target, treat_out_of_range_as_missing)
from data_pipeline.dataset_loader import load_raw_dataset, save_processed_dataset


def build_month_first_flags(frame):
    """True where a row's payroll system writes the month first, empty where the system is unknown."""
    return frame[config.PAYROLL_SYSTEM_COLUMN].map(config.MONTH_FIRST_BY_PAYROLL_SYSTEM).astype("boolean")


def repair_reversed_periods(frame):
    start, end = config.PERIOD_START_COLUMN, config.PERIOD_END_COLUMN
    frame = frame.copy()
    reversed_rows = (frame[start].notna() & frame[end].notna() & (frame[end] < frame[start])).fillna(False).astype(bool)
    swapped_start = frame.loc[reversed_rows, end].copy()
    frame.loc[reversed_rows, end] = frame.loc[reversed_rows, start]
    frame.loc[reversed_rows, start] = swapped_start
    return frame


def recount_days(frame):
    start, end, days = config.PERIOD_START_COLUMN, config.PERIOD_END_COLUMN, config.DAYS_IN_PERIOD_COLUMN
    frame = frame.copy()
    known = (frame[start].notna() & frame[end].notna()).fillna(False).astype(bool)
    frame.loc[known, days] = frame.loc[known, end] - frame.loc[known, start] + 1
    frame[days] = frame[days].astype("Int64")
    return frame


def hours_from_parts(frame):
    """Ordinary hours, plus night hours on a day-and-night roster; empty where a part is missing."""
    day_night = frame[config.ROSTER_TYPE_COLUMN] == config.DAY_NIGHT_ROSTER_TYPE
    ordinary = frame[config.ORDINARY_HOURS_COLUMN]
    night = frame[config.NIGHT_HOURS_COLUMN]
    return ordinary.where(~day_night.fillna(False).astype(bool), ordinary + night)


def recompute_total_hours(frame):
    frame = frame.copy()
    parts = hours_from_parts(frame)
    frame[config.TOTAL_HOURS_COLUMN] = parts.where(parts.notna(), frame[config.TOTAL_HOURS_COLUMN])
    return frame


def clean_query_dataset(input_file_path, output_file_path):
    """Produce a pay query table the correction model can be fitted on and scored against."""
    frame = load_raw_dataset(input_file_path, config.NULL_TOKENS)
    frame = remove_duplicate_records(frame)
    frame = normalize_category_values(frame, config.QUERY_VALUE_MAPPINGS)
    frame = remove_rows_missing_target(frame, config.QUERY_TARGET_COLUMN)
    month_first = build_month_first_flags(frame)
    frame = parse_financial_year_dates(frame, config.QUERY_DATE_COLUMNS, month_first)
    frame = convert_money_amounts(frame, config.QUERY_MONEY_COLUMNS)
    frame = convert_hours_worked(frame, config.QUERY_HOURS_COLUMNS)
    frame = convert_whole_numbers(frame, config.QUERY_WHOLE_NUMBER_COLUMNS)
    frame = treat_out_of_range_as_missing(frame, config.QUERY_RANGE_LIMITS)
    frame = repair_reversed_periods(frame)
    frame = recount_days(frame)
    frame = recompute_total_hours(frame)
    frame = format_financial_year_dates(frame, config.QUERY_DATE_COLUMNS)
    save_processed_dataset(frame, output_file_path)
    return frame
