"""Trains the unsupervised Isolation Forest anomaly detector on legitimate-looking transactions."""
from __future__ import annotations

from app.ml.isolation_forest_model import build_isolation_forest
from ml_pipeline.data_cleaning import generate_synthetic_dataset
from ml_pipeline.feature_engineering import split_features_labels


def train_isolation_forest_model(df=None, seed: int = 42):
    if df is None:
        df = generate_synthetic_dataset(seed=seed)
    x, y = split_features_labels(df)
    model = build_isolation_forest()
    # Isolation Forest is unsupervised: fit on the full unlabeled feature matrix
    model.fit(x)
    scores = model.score_samples(x)
    return model, x, y, scores


if __name__ == "__main__":
    model, x, y, scores = train_isolation_forest_model()
    print("Trained IsolationForest, score range:", scores.min(), scores.max())
