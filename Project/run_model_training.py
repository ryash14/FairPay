"""Step 3: train, score and save the three models.

    python run_model_training.py
"""
import sklearn
from sklearn.model_selection import train_test_split

from config import config


def main():
    from data_pipeline.dataset_loader import load_processed_dataset
    from data_pipeline.feature_builder import build_feature_frame
    from modeling import model_registry
    from modeling.category_model import train_category_model
    from modeling.correction_model import train_correction_model
    from modeling.effort_model import train_effort_model

    print("training three models")
    query_train = load_processed_dataset(config.CLEAN_QUERIES_TRAIN_FILE)
    query_eval = load_processed_dataset(config.CLEAN_QUERIES_EVAL_FILE)
    correction_train = build_feature_frame(query_train, config.CORRECTION_NUMERIC_FEATURES,
                                           config.CORRECTION_CATEGORICAL_FEATURES)
    correction_eval = build_feature_frame(query_eval, config.CORRECTION_NUMERIC_FEATURES,
                                          config.CORRECTION_CATEGORICAL_FEATURES)
    correction_train_target = query_train[config.QUERY_TARGET_COLUMN].map(config.QUERY_TARGET_ENCODING).astype(int)
    correction_eval_target = query_eval[config.QUERY_TARGET_COLUMN].map(config.QUERY_TARGET_ENCODING).astype(int)
    correction_model, correction_scores = train_correction_model(correction_train, correction_train_target,
                                                                 correction_eval, correction_eval_target)
    print(f"correction held-out ROC AUC {correction_scores['held_out_roc_auc']:.4f} "
          f"(train {correction_scores['train_roc_auc']:.4f}, gap {correction_scores['generalisation_gap']:+.4f})")

    effort_train_frame = load_processed_dataset(config.CLEAN_EFFORT_TRAIN_FILE)
    effort_eval_frame = load_processed_dataset(config.CLEAN_EFFORT_EVAL_FILE)
    effort_train = build_feature_frame(effort_train_frame, config.EFFORT_NUMERIC_FEATURES,
                                       config.EFFORT_CATEGORICAL_FEATURES)
    effort_eval = build_feature_frame(effort_eval_frame, config.EFFORT_NUMERIC_FEATURES,
                                      config.EFFORT_CATEGORICAL_FEATURES)
    effort_train_target = effort_train_frame[config.EFFORT_TARGET_COLUMN].astype(float)
    effort_eval_target = effort_eval_frame[config.EFFORT_TARGET_COLUMN].astype(float)
    effort_model, effort_scores = train_effort_model(effort_train, effort_train_target, effort_eval, effort_eval_target)
    print(f"effort held-out R2 {effort_scores['held_out_r2']:.4f} MAE {effort_scores['mean_absolute_error']:.2f} h "
          f"(train {effort_scores['train_r2']:.4f}, gap {effort_scores['generalisation_gap']:+.4f})")

    notes = load_processed_dataset(config.CLEAN_QUERY_NOTES_FILE)
    train_text, held_out_text, train_category, held_out_category = train_test_split(
        notes[config.NOTE_TEXT_COLUMN], notes[config.NOTE_TARGET_COLUMN], test_size=config.NOTE_HELD_OUT_SHARE,
        stratify=notes[config.NOTE_TARGET_COLUMN], random_state=config.RANDOM_SEED)
    category_model, category_scores = train_category_model(train_text, train_category, held_out_text, held_out_category)
    print(f"category held-out macro F1 {category_scores['held_out_macro_f1']:.4f} "
          f"(train {category_scores['train_macro_f1']:.4f}, gap {category_scores['generalisation_gap']:+.4f})")

    model_registry.save_model(correction_model, config.CORRECTION_MODEL_FILE)
    model_registry.save_model(effort_model, config.EFFORT_MODEL_FILE)
    model_registry.save_model(category_model, config.CATEGORY_MODEL_FILE)
    model_registry.save_feature_schema(list(correction_train.columns), config.CORRECTION_SCHEMA_FILE)
    model_registry.save_feature_schema(list(effort_train.columns), config.EFFORT_SCHEMA_FILE)

    metrics = {
        "correction": {"algorithm": type(correction_model.named_steps["estimator"]).__name__,
                       "training_rows": int(len(correction_train)), "held_out_rows": int(len(correction_eval)),
                       "scores": correction_scores, "minimum_required": config.MINIMUM_CORRECTION_ROC_AUC,
                       "meets_minimum": bool(correction_scores["held_out_roc_auc"] >= config.MINIMUM_CORRECTION_ROC_AUC),
                       "scikit_learn_version": sklearn.__version__},
        "effort": {"algorithm": type(effort_model.named_steps["estimator"]).__name__,
                   "training_rows": int(len(effort_train)), "held_out_rows": int(len(effort_eval)),
                   "scores": effort_scores, "minimum_required": config.MINIMUM_EFFORT_R2,
                   "meets_minimum": bool(effort_scores["held_out_r2"] >= config.MINIMUM_EFFORT_R2),
                   "scikit_learn_version": sklearn.__version__},
        "category": {"algorithm": " + ".join(type(step).__name__ for _, step in category_model.steps),
                     "training_rows": int(len(train_text)), "held_out_rows": int(len(held_out_text)),
                     "scores": category_scores, "minimum_required": config.MINIMUM_CATEGORY_MACRO_F1,
                     "meets_minimum": bool(category_scores["held_out_macro_f1"] >= config.MINIMUM_CATEGORY_MACRO_F1),
                     "scikit_learn_version": sklearn.__version__},
    }
    model_registry.save_metrics(metrics, config.MODEL_METRICS_FILE)
    try:
        from experiments.tracking import log_training_run
        log_training_run(metrics)
    except ImportError:
        pass
    print()
    print(f"metrics written to {config.MODEL_METRICS_FILE}")
    below = [name for name, entry in metrics.items() if not entry["meets_minimum"]]
    print("every model is above the minimum config sets for it" if not below else f"BELOW THE MINIMUM: {', '.join(below)}")


if __name__ == "__main__":
    main()
