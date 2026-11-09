"""The whole cleaning run for the employee query notes extract."""
import re

import numpy as np
import pandas as pd

from config import config
from data_pipeline.common_cleaning import (convert_markup_to_plain_text, convert_whole_numbers,
                                           format_financial_year_dates, normalize_category_values,
                                           parse_financial_year_dates, remove_duplicate_records,
                                           remove_rows_missing_target)
from data_pipeline.dataset_loader import load_raw_dataset, save_processed_dataset


def is_written_in_capitals(text):
    """True when the text equals its upper-case form and differs from its lower-case form."""
    return isinstance(text, str) and text == text.upper() and text != text.lower()


def word_count(text):
    return len(text.split()) if isinstance(text, str) else 0


def split_timestamp(value):
    """(date part, HH:MM) or None when the value carries no readable time."""
    match = re.fullmatch(config.TIMESTAMP_PARTS_PATTERN, value.strip())
    if not match:
        return None
    groups = [g for g in match.groups() if g is not None]
    date_part = groups[0].strip()
    time_text = ":".join(groups[1:]) if len(groups) > 2 else groups[1]
    hour, minute = time_text.split(":")[:2]
    if int(hour) > 23 or int(minute) > 59:
        return None
    return date_part, f"{int(hour):02d}:{int(minute):02d}"


def clean_query_note_dataset(input_file_path, output_file_path):
    """Notes whose words do not depend on the tool that stored them, each long enough to read."""
    frame = load_raw_dataset(input_file_path, config.NULL_TOKENS)
    frame = remove_duplicate_records(frame)
    frame = normalize_category_values(frame, config.NOTE_VALUE_MAPPINGS)
    frame = remove_rows_missing_target(frame, config.NOTE_TARGET_COLUMN)
    frame = convert_whole_numbers(frame, [config.NOTE_SEQUENCE_COLUMN])
    frame = convert_markup_to_plain_text(frame, [config.NOTE_TEXT_COLUMN])

    text = config.NOTE_TEXT_COLUMN
    frame[text] = frame[text].map(lambda t: t.lower() if is_written_in_capitals(t) else t)
    keep = frame[text].map(lambda t: isinstance(t, str) and t != "" and word_count(t) >= config.MINIMUM_NOTE_WORDS)
    frame = frame[keep.astype(bool)].reset_index(drop=True)
    frame[config.NOTE_LENGTH_COLUMN] = frame[text].map(len).astype("Int64")

    unreadable, dates, times = set(), [], []
    for value in frame[config.NOTE_TIMESTAMP_COLUMN]:
        if not isinstance(value, str):
            dates.append(np.nan)
            times.append(np.nan)
            continue
        parts = split_timestamp(value)
        if parts is None:
            unreadable.add(value)
            dates.append(np.nan)
            times.append(np.nan)
            continue
        dates.append(parts[0])
        times.append(parts[1])
    if unreadable:
        raise ValueError(f"{config.NOTE_TIMESTAMP_COLUMN} holds timestamps that cannot be read: {sorted(unreadable)}")

    parts = pd.DataFrame({config.NOTE_DATE_PART: pd.Series(dates, index=frame.index, dtype=object),
                          config.NOTE_TIME_PART: pd.Series(times, index=frame.index, dtype=object)})
    day_first = pd.Series(False, index=parts.index, dtype="boolean")
    parts = parse_financial_year_dates(parts, [config.NOTE_DATE_PART], day_first)
    parts = format_financial_year_dates(parts, [config.NOTE_DATE_PART])
    frame[config.NOTE_TIMESTAMP_COLUMN] = [
        f"{d} {t}" if isinstance(d, str) and isinstance(t, str) else np.nan
        for d, t in zip(parts[config.NOTE_DATE_PART], parts[config.NOTE_TIME_PART])]
    frame[config.NOTE_TIMESTAMP_COLUMN] = frame[config.NOTE_TIMESTAMP_COLUMN].astype(object)
    save_processed_dataset(frame, output_file_path)
    return frame
