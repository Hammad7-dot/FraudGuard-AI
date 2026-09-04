"""XGBoost fraud classifier wrapper with graceful fallback to sklearn GradientBoosting."""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb  # noqa: F401
    XGBOOST_AVAILABLE = True
except ImportError:  # pragma: no cover
    XGBOOST_AVAILABLE = False
    logger.warning("xgboost not available, will fall back to sklearn GradientBoostingClassifier")


def build_classifier():
    """Return a fresh untrained classifier instance, preferring XGBoost."""
    if XGBOOST_AVAILABLE:
        import xgboost as xgb
        return xgb.XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
        )
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier(n_estimators=150, max_depth=3, random_state=42)


class XGBoostFraudModel:
    """Loads a serialized model and predicts fraud_probability for feature vectors."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path
        self.model = None
        self.feature_names: List[str] = []
        self.version = "unloaded"
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def load(self, model_path: str) -> None:
        payload = joblib.load(model_path)
        self.model = payload["model"]
        self.feature_names = payload.get("feature_names", [])
        self.version = payload.get("version", "unknown")
        self.model_path = model_path

    def predict_proba(self, feature_vector: List[float]) -> float:
        if self.model is None:
            return 0.0
        values = np.array(feature_vector, dtype=float).reshape(1, -1)
        x = pd.DataFrame(values, columns=self.feature_names) if self.feature_names else values
        try:
            proba = self.model.predict_proba(x)[0][1]
        except Exception as exc:
            logger.error("xgboost_predict_failed error=%s", exc)
            raise
        return float(np.clip(proba, 0.0, 1.0))

    @property
    def is_loaded(self) -> bool:
        return self.model is not None
