"""CI quality gate: fail the build when any saved model is below the minimum config sets for it.

    python -m ops.model_gate
"""
import json
import sys

from config import config

HEADLINE = {"correction": "held_out_roc_auc", "effort": "held_out_r2", "category": "held_out_macro_f1"}


def main():
    with open(config.MODEL_METRICS_FILE, encoding="utf-8") as handle:
        metrics = json.load(handle)
    failed = False
    for name, score_key in HEADLINE.items():
        entry = metrics[name]
        score, minimum = entry["scores"][score_key], entry["minimum_required"]
        gap = entry["scores"]["generalisation_gap"]
        verdict = "pass" if score >= minimum else "FAIL"
        failed |= score < minimum
        print(f"{name:<11} {score_key:<18} {score:.4f}  minimum {minimum:.4f}  gap {gap:+.4f}  {verdict}")
    effort = metrics["effort"]["scores"]
    if effort["mean_absolute_error"] >= effort["average_estimate_mean_absolute_error"]:
        print("effort      does not beat always guessing the mean  FAIL")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
