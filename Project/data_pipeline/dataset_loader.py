"""Reads tables from disk and writes them back.

This is the only module in data preparation that touches a CSV file. Raw files
are read as text with nothing guessed; cleaned files are read with pandas'
normal type inference.
"""
import os

import numpy as np
import pandas as pd


def load_raw_dataset(file_path, null_tokens):
    """Read one raw extract exactly as written: every column text, gaps only where a null token stands."""
    frame = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    tokens = {token.lower() for token in null_tokens}

    def tidy(value):
        if not isinstance(value, str):
            return np.nan
        trimmed = value.strip()
        return np.nan if trimmed.lower() in tokens else trimmed

    cleaned = {column: frame[column].map(tidy).astype(object) for column in frame.columns}
    return pd.DataFrame(cleaned, columns=frame.columns, index=frame.index)


def load_processed_dataset(file_path):
    """Read a cleaned table with pandas' default type inference."""
    return pd.read_csv(file_path)


def save_processed_dataset(dataframe, file_path):
    """Write a cleaned table, creating its folder first, without an index column."""
    folder = os.path.dirname(file_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    dataframe.to_csv(file_path, index=False)
