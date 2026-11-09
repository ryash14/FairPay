"""Model inputs in one fixed shape, and the preparation saved inside each tabular model."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def _as_text(value):
    if value is None or value is pd.NA or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    try:
        if pd.isna(value):
            return np.nan
    except (TypeError, ValueError):
        pass
    return str(value)


def build_feature_frame(dataframe, numeric_columns, categorical_columns):
    """numeric_columns as floats, then categorical_columns as text, rows and index unchanged."""
    numeric = pd.DataFrame(
        {column: pd.to_numeric(dataframe[column], errors="raise").astype("Float64").astype(float)
         for column in numeric_columns},
        index=dataframe.index, columns=list(numeric_columns))
    categorical = pd.DataFrame(
        {column: pd.Series([_as_text(v) for v in dataframe[column]], index=dataframe.index, dtype=object)
         for column in categorical_columns},
        index=dataframe.index, columns=list(categorical_columns))
    return pd.concat([numeric, categorical], axis=1)


def build_model_pipeline(estimator, numeric_columns, categorical_columns):
    """Median-filled numbers and one-hot categories ahead of the estimator, unfitted."""
    categorical = Pipeline([
        ("fill", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(drop="if_binary", handle_unknown="warn", sparse_output=False)),
    ])
    preprocessing = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median"), list(numeric_columns)),
        ("categorical", categorical, list(categorical_columns)),
    ], remainder="drop")
    return Pipeline([("preprocessing", preprocessing), ("estimator", estimator)])
