import os

import pytest

from ml_pipeline.data_cleaning import FEATURE_COLUMNS, generate_synthetic_dataset
from ml_pipeline.evaluate import evaluate_classifier
from ml_pipeline.feature_engineering import split_features_labels
from ml_pipeline.train_isolation_forest import train_isolation_forest_model
from ml_pipeline.train_xgboost import train_xgboost_model


@pytest.fixture(scope="module")
def small_dataset():
    return generate_synthetic_dataset(n_samples=2000, fraud_rate=0.05, seed=1)


def test_dataset_has_expected_columns(small_dataset):
    for col in FEATURE_COLUMNS:
        assert col in small_dataset.columns
    assert "label" in small_dataset.columns


def test_xgboost_training_and_prediction_shape(small_dataset):
    model, x_train, x_test, y_train, y_test = train_xgboost_model(df=small_dataset)
    proba = model.predict_proba(x_test)
    assert proba.shape[0] == len(x_test)
    assert proba.shape[1] == 2


def test_xgboost_probabilities_in_valid_range(small_dataset):
    model, x_train, x_test, y_train, y_test = train_xgboost_model(df=small_dataset)
    proba = model.predict_proba(x_test)[:, 1]
    assert (proba >= 0).all() and (proba <= 1).all()


def test_evaluate_classifier_returns_expected_metrics(small_dataset):
    model, x_train, x_test, y_train, y_test = train_xgboost_model(df=small_dataset)
    metrics = evaluate_classifier(model, x_test, y_test)
    for key in ("precision", "recall", "f1", "pr_auc", "roc_auc", "confusion_matrix"):
        assert key in metrics


def test_isolation_forest_training_and_scores(small_dataset):
    model, x, y, scores = train_isolation_forest_model(df=small_dataset)
    assert len(scores) == len(x)
    # Fraud should on average look more anomalous (lower score_samples) than legit
    fraud_mean = scores[y == 1].mean()
    legit_mean = scores[y == 0].mean()
    assert fraud_mean <= legit_mean


def test_model_wrapper_loads_serialized_artifact(tmp_path, small_dataset):
    import joblib

    from app.ml.xgboost_model import XGBoostFraudModel

    model, x_train, x_test, y_train, y_test = train_xgboost_model(df=small_dataset)
    path = tmp_path / "fraud_xgboost_v0.0.1.pkl"
    joblib.dump({"model": model, "feature_names": FEATURE_COLUMNS, "version": "0.0.1"}, path)

    wrapper = XGBoostFraudModel(model_path=str(path))
    assert wrapper.is_loaded
    proba = wrapper.predict_proba(x_test.iloc[0].tolist())
    assert 0.0 <= proba <= 1.0


def test_isolation_forest_wrapper_loads_serialized_artifact(tmp_path, small_dataset):
    import joblib

    from app.ml.isolation_forest_model import IsolationForestAnomalyModel

    model, x, y, scores = train_isolation_forest_model(df=small_dataset)
    path = tmp_path / "isolation_forest_v0.0.1.pkl"
    joblib.dump(
        {"model": model, "feature_names": FEATURE_COLUMNS, "version": "0.0.1",
         "score_min": float(scores.min()), "score_max": float(scores.max())},
        path,
    )
    wrapper = IsolationForestAnomalyModel(model_path=str(path))
    assert wrapper.is_loaded
    score = wrapper.anomaly_score(x.iloc[0].tolist())
    assert 0.0 <= score <= 1.0
