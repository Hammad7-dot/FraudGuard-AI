"""Trains both models on synthetic data, evaluates, and serializes versioned artifacts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import joblib

from ml_pipeline.data_cleaning import FEATURE_COLUMNS, generate_synthetic_dataset
from ml_pipeline.evaluate import evaluate_classifier
from ml_pipeline.feature_engineering import FEATURES_VERSION, split_features_labels
from ml_pipeline.train_isolation_forest import train_isolation_forest_model
from ml_pipeline.train_xgboost import train_xgboost_model

DATASET_VERSION = "synthetic-v1"
XGB_VERSION = "1.0.0"
ISO_VERSION = "1.0.0"
MODEL_DIR = "data/models"


def main() -> None:
    os.makedirs(MODEL_DIR, exist_ok=True)
    training_date = datetime.now(timezone.utc).isoformat()

    df = generate_synthetic_dataset(n_samples=20_000, fraud_rate=0.03, seed=42)

    # --- XGBoost / fallback classifier ---
    xgb_model, x_train, x_test, y_train, y_test = train_xgboost_model(df=df)
    xgb_metrics = evaluate_classifier(xgb_model, x_test, y_test)
    xgb_path = os.path.join(MODEL_DIR, f"fraud_xgboost_v{XGB_VERSION}.pkl")
    joblib.dump({"model": xgb_model, "feature_names": FEATURE_COLUMNS, "version": XGB_VERSION}, xgb_path)

    xgb_meta = {
        "model_name": "fraud_xgboost",
        "version": XGB_VERSION,
        "training_date": training_date,
        "dataset_version": DATASET_VERSION,
        "features_version": FEATURES_VERSION,
        "metrics": xgb_metrics,
        "n_train": len(x_train),
        "n_test": len(x_test),
        "algorithm": type(xgb_model).__name__,
    }
    with open(os.path.join(MODEL_DIR, "fraud_xgboost_metadata.json"), "w") as f:
        json.dump(xgb_meta, f, indent=2)

    # --- Isolation Forest ---
    iso_model, x_iso, y_iso, scores = train_isolation_forest_model(df=df)
    iso_path = os.path.join(MODEL_DIR, f"isolation_forest_v{ISO_VERSION}.pkl")
    joblib.dump(
        {
            "model": iso_model,
            "feature_names": FEATURE_COLUMNS,
            "version": ISO_VERSION,
            "score_min": float(scores.min()),
            "score_max": float(scores.max()),
        },
        iso_path,
    )
    # Rough separability check: correlation-based pseudo metric (unsupervised model, no labels used in training)
    fraud_scores = scores[y_iso == 1]
    legit_scores = scores[y_iso == 0]
    iso_meta = {
        "model_name": "isolation_forest",
        "version": ISO_VERSION,
        "training_date": training_date,
        "dataset_version": DATASET_VERSION,
        "features_version": FEATURES_VERSION,
        "metrics": {
            "mean_score_legit": round(float(legit_scores.mean()), 4),
            "mean_score_fraud": round(float(fraud_scores.mean()), 4),
            "score_min": float(scores.min()),
            "score_max": float(scores.max()),
            "note": "Unsupervised model; lower score_samples = more anomalous. "
                    "mean_score_fraud should be notably lower than mean_score_legit.",
        },
        "algorithm": type(iso_model).__name__,
    }
    with open(os.path.join(MODEL_DIR, "isolation_forest_metadata.json"), "w") as f:
        json.dump(iso_meta, f, indent=2)

    print("Saved:", xgb_path, iso_path)
    print("XGBoost metrics:", xgb_metrics)
    print("Isolation Forest metrics:", iso_meta["metrics"])


if __name__ == "__main__":
    main()
