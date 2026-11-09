"""Reads an employee note and names the query category it describes."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from modeling.model_evaluation import evaluate_text_classifier


def train_category_model(train_text, train_target, held_out_text, held_out_target):
    model = Pipeline([("preprocessing", TfidfVectorizer()), ("estimator", LogisticRegression())])
    model.fit(train_text, train_target)
    return model, evaluate_text_classifier(model, train_text, train_target, held_out_text, held_out_target)
