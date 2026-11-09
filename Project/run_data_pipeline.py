"""Step 2: clean the five raw extracts and write the data-quality report.

    python run_data_pipeline.py
"""
import os

from config import config
from data_pipeline import quality_profiler
from data_pipeline.dataset_loader import load_raw_dataset
from data_pipeline.effort_cleaning import clean_effort_dataset
from data_pipeline.query_cleaning import clean_query_dataset
from data_pipeline.query_note_cleaning import clean_query_note_dataset

DATASET_JOBS = [
    (config.RAW_QUERIES_TRAIN_FILE, config.CLEAN_QUERIES_TRAIN_FILE, clean_query_dataset,
     config.QUERY_TARGET_COLUMN, quality_profiler.profile_query_details),
    (config.RAW_QUERIES_EVAL_FILE, config.CLEAN_QUERIES_EVAL_FILE, clean_query_dataset,
     config.QUERY_TARGET_COLUMN, quality_profiler.profile_query_details),
    (config.RAW_EFFORT_TRAIN_FILE, config.CLEAN_EFFORT_TRAIN_FILE, clean_effort_dataset,
     config.EFFORT_TARGET_COLUMN, quality_profiler.profile_effort_details),
    (config.RAW_EFFORT_EVAL_FILE, config.CLEAN_EFFORT_EVAL_FILE, clean_effort_dataset,
     config.EFFORT_TARGET_COLUMN, quality_profiler.profile_effort_details),
    (config.RAW_QUERY_NOTES_FILE, config.CLEAN_QUERY_NOTES_FILE, clean_query_note_dataset,
     config.NOTE_TARGET_COLUMN, quality_profiler.profile_note_details),
]


def main():
    profiles = {}
    for raw_path, clean_path, clean_function, target_column, detail_profiler in DATASET_JOBS:
        raw = load_raw_dataset(raw_path, config.NULL_TOKENS)
        clean = clean_function(raw_path, clean_path)
        name = os.path.splitext(os.path.basename(raw_path))[0]
        profile = quality_profiler.profile_dataset(raw, clean, target_column)
        profile.update(detail_profiler(raw, clean))
        profiles[name] = profile
        print(f"{name:<30}{profile['rows_received']:>6} received -> {profile['rows_kept']:>6} kept  "
              f"({profile['rows_removed']} removed)")
    quality_profiler.write_quality_report(profiles, config.DATA_QUALITY_REPORT_FILE)
    print()
    print(f"quality report written to {config.DATA_QUALITY_REPORT_FILE}")


if __name__ == "__main__":
    main()
