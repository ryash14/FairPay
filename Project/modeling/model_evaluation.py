"""Scores a fitted model on rows it learned from and rows it never saw. Nothing here fits anything."""
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error, precision_score, r2_score, recall_score,
                             roc_auc_score)
import numpy as np


def _r(value):
    return round(float(value), 4)


def evaluate_classifier(model, train_features, train_target, held_out_features, held_out_target):
    """ROC AUC on both sets and the gap, then held-out accuracy, precision, recall, F1 and calibration."""
    train_probability = model.predict_proba(train_features)[:, 1]
    held_out_probability = model.predict_proba(held_out_features)[:, 1]
    held_out_prediction = model.predict(held_out_features)
    train_auc = roc_auc_score(train_target, train_probability)
    held_out_auc = roc_auc_score(held_out_target, held_out_probability)
    return {
        "train_roc_auc": _r(train_auc),
        "held_out_roc_auc": _r(held_out_auc),
        "generalisation_gap": _r(train_auc - held_out_auc),
        "accuracy": _r(accuracy_score(held_out_target, held_out_prediction)),
        "precision": _r(precision_score(held_out_target, held_out_prediction, pos_label=1, zero_division=0)),
        "recall": _r(recall_score(held_out_target, held_out_prediction, pos_label=1, zero_division=0)),
        "f1": _r(f1_score(held_out_target, held_out_prediction, pos_label=1, zero_division=0)),
        "mean_predicted_probability": _r(np.mean(held_out_probability)),
        "positive_share": _r(np.mean(np.asarray(held_out_target) == 1)),
    }


def evaluate_regressor(model, train_features, train_target, held_out_features, held_out_target):
    """R squared on both sets and the gap, held-out MAE against always guessing the training mean."""
    train_prediction = model.predict(train_features)
    held_out_prediction = model.predict(held_out_features)
    train_r2 = r2_score(train_target, train_prediction)
    held_out_r2 = r2_score(held_out_target, held_out_prediction)
    baseline = np.full(len(held_out_target), float(np.mean(train_target)))
    return {
        "train_r2": _r(train_r2),
        "held_out_r2": _r(held_out_r2),
        "generalisation_gap": _r(train_r2 - held_out_r2),
        "mean_absolute_error": _r(mean_absolute_error(held_out_target, held_out_prediction)),
        "average_estimate_mean_absolute_error": _r(mean_absolute_error(held_out_target, baseline)),
        "lowest_prediction": _r(np.min(held_out_prediction)),
    }


def evaluate_text_classifier(model, train_text, train_target, held_out_text, held_out_target):
    """Macro F1 on both sets and the gap, held-out accuracy, weighted F1 and each category's own F1."""
    train_prediction = model.predict(train_text)
    held_out_prediction = model.predict(held_out_text)
    train_f1 = f1_score(train_target, train_prediction, average="macro")
    held_out_f1 = f1_score(held_out_target, held_out_prediction, average="macro")
    categories = sorted(set(held_out_target))
    per_class = f1_score(held_out_target, held_out_prediction, labels=categories, average=None, zero_division=0)
    return {
        "train_macro_f1": _r(train_f1),
        "held_out_macro_f1": _r(held_out_f1),
        "generalisation_gap": _r(train_f1 - held_out_f1),
        "accuracy": _r(accuracy_score(held_out_target, held_out_prediction)),
        "weighted_f1": _r(f1_score(held_out_target, held_out_prediction, average="weighted")),
        "per_class_f1": {str(category): _r(score) for category, score in zip(categories, per_class)},
    }
