"""Predicts whether a pay query ends in a corrected pay."""
from sklearn.ensemble import GradientBoostingClassifier

from config import config
from data_pipeline.feature_builder import build_model_pipeline
from modeling.model_evaluation import evaluate_classifier


def train_correction_model(train_features, train_target, held_out_features, held_out_target):
    estimator = GradientBoostingClassifier(n_estimators=200, min_samples_leaf=50, random_state=config.RANDOM_SEED)
    model = build_model_pipeline(estimator, config.CORRECTION_NUMERIC_FEATURES, config.CORRECTION_CATEGORICAL_FEATURES)
    model.fit(train_features, train_target)
    return model, evaluate_classifier(model, train_features, train_target, held_out_features, held_out_target)
