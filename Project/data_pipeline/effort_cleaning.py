"""The whole cleaning run for one remediation effort extract."""
import pandas as pd

from config import config
from data_pipeline.common_cleaning import (convert_counts_with_units, convert_durations_to_hours, convert_money_amounts,
                                           convert_whole_numbers, format_financial_year_dates, normalize_category_values,
                                           parse_financial_year_dates, remove_duplicate_records,
                                           remove_rows_missing_target, treat_out_of_range_as_missing)
from data_pipeline.dataset_loader import load_raw_dataset, save_processed_dataset


def clean_effort_dataset(input_file_path, output_file_path):
    """Produce an effort table the effort model can be fitted on and scored against."""
    frame = load_raw_dataset(input_file_path, config.NULL_TOKENS)
    frame = remove_duplicate_records(frame)
    frame = normalize_category_values(frame, config.EFFORT_VALUE_MAPPINGS)
    day_first = pd.Series(False, index=frame.index, dtype="boolean")
    frame = parse_financial_year_dates(frame, config.EFFORT_DATE_COLUMNS, day_first)
    frame = convert_money_amounts(frame, config.EFFORT_MONEY_COLUMNS)
    frame = convert_durations_to_hours(frame, config.EFFORT_DURATION_COLUMNS)
    frame = convert_counts_with_units(frame, config.EFFORT_COUNT_WITH_UNIT_PATTERNS)
    frame = convert_whole_numbers(frame, config.EFFORT_WHOLE_NUMBER_COLUMNS)
    frame = treat_out_of_range_as_missing(frame, config.EFFORT_RANGE_LIMITS)
    frame = remove_rows_missing_target(frame, config.EFFORT_TARGET_COLUMN)
    frame = format_financial_year_dates(frame, config.EFFORT_DATE_COLUMNS)
    save_processed_dataset(frame, output_file_path)
    return frame
