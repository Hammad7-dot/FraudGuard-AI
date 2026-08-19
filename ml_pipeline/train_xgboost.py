"""Trains the supervised fraud classifier (XGBoost, falling back to GradientBoosting)."""
from __future__ import annotations

from sklearn.model_selection import train_test_split

from app.ml.xgboost_model import build_classifier
from ml_pipeline.data_cleaning import generate_synthetic_dataset
from ml_pipeline.feature_engineering import split_features_labels


def train_xgboost_model(df=None, seed: int = 42):
    if df is None:
        df = generate_synthetic_dataset(seed=seed)
    x, y = split_features_labels(df)
    # Never train on the test set: hold out 20% purely for evaluation
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=seed, stratify=y)

    # Class imbalance handling via scale_pos_weight / class_weight equivalent
    fraud_ratio = max((y_train == 0).sum() / max((y_train == 1).sum(), 1), 1.0)
    model = build_classifier()
    if hasattr(model, "scale_pos_weight"):
        model.set_params(scale_pos_weight=fraud_ratio)
    model.fit(x_train, y_train)
    return model, x_train, x_test, y_train, y_test


if __name__ == "__main__":
    model, *_ = train_xgboost_model()
    print("Trained XGBoost/fallback model:", type(model).__name__)
