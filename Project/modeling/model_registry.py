"""Saves and loads the models, their feature schemas and their scores."""
import json
import os

import joblib


def _folder_for(file_path):
    folder = os.path.dirname(file_path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def save_model(model, file_path):
    _folder_for(file_path)
    joblib.dump(model, file_path, compress=3)


def save_feature_schema(feature_names, file_path):
    _folder_for(file_path)
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(list(feature_names), handle, indent=2)


def save_metrics(metrics, file_path):
    _folder_for(file_path)
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)


def load_model(file_path):
    return joblib.load(file_path)


def load_feature_schema(file_path):
    with open(file_path, encoding="utf-8") as handle:
        return list(json.load(handle))
