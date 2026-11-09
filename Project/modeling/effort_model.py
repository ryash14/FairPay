"""Estimates the analyst hours remediating a pay query will take."""
from sklearn.linear_model import LinearRegression

from config import config
from data_pipeline.feature_builder import build_model_pipeline
from modeling.model_evaluation import evaluate_regressor


def train_effort_model(train_features, train_target, held_out_features, held_out_target):
    model = build_model_pipeline(LinearRegression(), config.EFFORT_NUMERIC_FEATURES, config.EFFORT_CATEGORICAL_FEATURES)
    model.fit(train_features, train_target)
    return model, evaluate_regressor(model, train_features, train_target, held_out_features, held_out_target)
