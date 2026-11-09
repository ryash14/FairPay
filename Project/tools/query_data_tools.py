"""Serves single records out of the live queue."""
import pandas as pd

from config import config
from tools.messages import fill_template


def fetch_query_profile(open_queries, query_reference):
    """The query's one row as a dict, values the text the queue holds or NaN."""
    rows = open_queries[open_queries[config.QUERY_REFERENCE_COLUMN] == query_reference]
    if len(rows) == 0:
        raise ValueError(fill_template(config.QUERY_NOT_IN_QUEUE_MESSAGE, query_reference,
                                       query_reference=query_reference))
    if len(rows) > 1:
        raise ValueError(f"Query {query_reference} appears {len(rows)} times in the open queue")
    return rows.iloc[0].to_dict()


def fetch_query_notes(open_query_notes, query_reference):
    """The query's note texts in the order they were written, lowest sequence first."""
    rows = open_query_notes[open_query_notes[config.QUERY_REFERENCE_COLUMN] == query_reference]
    if len(rows) == 0:
        raise ValueError(fill_template(config.QUERY_WITHOUT_NOTES_MESSAGE, query_reference,
                                       query_reference=query_reference))
    sequence = pd.to_numeric(rows[config.NOTE_SEQUENCE_COLUMN], errors="raise")
    if sequence.isna().any() or sequence.duplicated().any():
        raise ValueError(f"The notes of query {query_reference} do not each carry their own sequence number")
    ordered = rows.assign(_order=sequence.astype(float)).sort_values("_order", kind="stable")
    return [str(text) for text in ordered[config.NOTE_TEXT_COLUMN]]
