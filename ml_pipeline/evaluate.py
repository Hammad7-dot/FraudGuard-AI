"""Evaluates the trained classifier with fraud-appropriate metrics (not accuracy alone)."""
from __future__ import annotations

from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                              precision_score, recall_score, roc_auc_score)


def evaluate_classifier(model, x_test, y_test) -> dict:
    y_pred = model.predict(x_test)
    y_proba = model.predict_proba(x_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred).tolist()
    metrics = {
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "pr_auc": round(float(average_precision_score(y_test, y_proba)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        "confusion_matrix": cm,
        "confusion_matrix_labels": ["true_negative", "false_positive", "false_negative", "true_positive"],
    }
    return metrics
