"""Experiment tracking without a server: every training run is appended to a JSON-lines ledger.

run_model_training.py calls log_training_run after it saves the models, so the
ledger shows how each model's scores moved from one run to the next. Read it
with `python -m experiments.compare_baselines --history`.
"""
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, UTC

from config import config

LEDGER_FILE = os.path.join("output", "experiments", "training_runs.jsonl")


def _file_fingerprint(path):
    if not os.path.exists(path):
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def _git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              timeout=5).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def log_training_run(metrics):
    os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
    entry = {
        "logged_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "data_fingerprints": {name: _file_fingerprint(path) for name, path in {
            "queries_train": config.CLEAN_QUERIES_TRAIN_FILE, "effort_train": config.CLEAN_EFFORT_TRAIN_FILE,
            "notes": config.CLEAN_QUERY_NOTES_FILE}.items()},
        "headline": {
            "correction_held_out_roc_auc": metrics["correction"]["scores"]["held_out_roc_auc"],
            "effort_held_out_r2": metrics["effort"]["scores"]["held_out_r2"],
            "effort_mae_hours": metrics["effort"]["scores"]["mean_absolute_error"],
            "category_held_out_macro_f1": metrics["category"]["scores"]["held_out_macro_f1"],
        },
        "meets_minimum": {name: entry["meets_minimum"] for name, entry in metrics.items()},
        "metrics": metrics,
    }
    with open(LEDGER_FILE, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def read_ledger():
    if not os.path.exists(LEDGER_FILE):
        return []
    with open(LEDGER_FILE, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
