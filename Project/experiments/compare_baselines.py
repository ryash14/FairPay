"""Day 2 experiment: compare each production model with simple baselines on the same held-out rows.

    python -m experiments.compare_baselines            # baselines vs the chosen models
    python -m experiments.compare_baselines --history  # the training-run ledger

Writes output/experiments/baseline_comparison.json and .md. The production
models stay exactly as the SRS specifies; this only shows they earn their place.
"""
import argparse
import json
import os
import warnings

import numpy as np
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import f1_score, mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from config import config
from data_pipeline.dataset_loader import load_processed_dataset
from data_pipeline.feature_builder import build_feature_frame, build_model_pipeline
from experiments.tracking import read_ledger

OUT_DIR = os.path.join("output", "experiments")


def _correction():
    train = load_processed_dataset(config.CLEAN_QUERIES_TRAIN_FILE)
    held = load_processed_dataset(config.CLEAN_QUERIES_EVAL_FILE)
    num, cat = config.CORRECTION_NUMERIC_FEATURES, config.CORRECTION_CATEGORICAL_FEATURES
    x_train, x_held = build_feature_frame(train, num, cat), build_feature_frame(held, num, cat)
    y_train = train[config.QUERY_TARGET_COLUMN].map(config.QUERY_TARGET_ENCODING).astype(int)
    y_held = held[config.QUERY_TARGET_COLUMN].map(config.QUERY_TARGET_ENCODING).astype(int)
    candidates = {
        "Majority class (baseline)": DummyClassifier(strategy="prior"),
        "Logistic regression (baseline)": LogisticRegression(max_iter=2000),
        "Gradient boosting (chosen)": GradientBoostingClassifier(n_estimators=200, min_samples_leaf=50,
                                                                 random_state=config.RANDOM_SEED),
    }
    rows = []
    for name, estimator in candidates.items():
        model = build_model_pipeline(estimator, num, cat).fit(x_train, y_train)
        rows.append({"model": name, "held_out_roc_auc": round(roc_auc_score(y_held, model.predict_proba(x_held)[:, 1]), 4)})
    return rows


def _effort():
    train = load_processed_dataset(config.CLEAN_EFFORT_TRAIN_FILE)
    held = load_processed_dataset(config.CLEAN_EFFORT_EVAL_FILE)
    num, cat = config.EFFORT_NUMERIC_FEATURES, config.EFFORT_CATEGORICAL_FEATURES
    x_train, x_held = build_feature_frame(train, num, cat), build_feature_frame(held, num, cat)
    y_train, y_held = train[config.EFFORT_TARGET_COLUMN].astype(float), held[config.EFFORT_TARGET_COLUMN].astype(float)
    candidates = {
        "Always the training mean (baseline)": DummyRegressor(strategy="mean"),
        "Ridge (alternative)": Ridge(alpha=1.0),
        "Random forest (alternative)": RandomForestRegressor(n_estimators=150, min_samples_leaf=20, n_jobs=-1,
                                                             random_state=config.RANDOM_SEED),
        "Linear regression (chosen)": LinearRegression(),
    }
    rows = []
    for name, estimator in candidates.items():
        prediction = build_model_pipeline(estimator, num, cat).fit(x_train, y_train).predict(x_held)
        rows.append({"model": name, "held_out_r2": round(r2_score(y_held, prediction), 4),
                     "mae_hours": round(mean_absolute_error(y_held, prediction), 3)})
    return rows


def _category():
    notes = load_processed_dataset(config.CLEAN_QUERY_NOTES_FILE)
    x_train, x_held, y_train, y_held = train_test_split(
        notes[config.NOTE_TEXT_COLUMN], notes[config.NOTE_TARGET_COLUMN], test_size=config.NOTE_HELD_OUT_SHARE,
        stratify=notes[config.NOTE_TARGET_COLUMN], random_state=config.RANDOM_SEED)
    candidates = {
        "Majority class (baseline)": Pipeline([("v", CountVectorizer()), ("m", DummyClassifier(strategy="most_frequent"))]),
        "Word counts + naive Bayes (baseline)": Pipeline([("v", CountVectorizer()), ("m", MultinomialNB())]),
        "TF-IDF + logistic regression (chosen)": Pipeline([("v", TfidfVectorizer()), ("m", LogisticRegression())]),
    }
    rows = []
    for name, model in candidates.items():
        prediction = model.fit(x_train, y_train).predict(x_held)
        rows.append({"model": name, "held_out_macro_f1": round(f1_score(y_held, prediction, average="macro"), 4)})
    return rows


def _markdown(results):
    lines = ["# Baseline comparison", ""]
    for section, rows in results.items():
        lines += [f"## {section}", "", "| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
        lines += ["| " + " | ".join(str(v) for v in row.values()) + " |" for row in rows]
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    arguments = parser.parse_args()
    if arguments.history:
        for entry in read_ledger():
            print(entry["logged_at"], entry.get("git_commit") or "-", json.dumps(entry["headline"]))
        return
    warnings.filterwarnings("ignore")
    np.random.seed(config.RANDOM_SEED)
    results = {"Correction model (ROC AUC, higher is better)": _correction(),
               "Effort model (R2 higher, MAE lower)": _effort(),
               "Category model (macro F1, higher is better)": _category()}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "baseline_comparison.json"), "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    report = _markdown(results)
    with open(os.path.join(OUT_DIR, "baseline_comparison.md"), "w", encoding="utf-8") as handle:
        handle.write(report)
    print(report)


if __name__ == "__main__":
    main()
