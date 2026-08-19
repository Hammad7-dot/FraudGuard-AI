"""Isolation Forest anomaly detector wrapper."""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


def build_isolation_forest() -> IsolationForest:
    return IsolationForest(n_estimators=200, contamination=0.05, random_state=42)


class IsolationForestAnomalyModel:
    """Loads a serialized Isolation Forest and converts its score into a 0-1 anomaly_score."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model = None
        self.feature_names: List[str] = []
        self.version = "unloaded"
        self.score_min = -0.5
        self.score_max = 0.5
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def load(self, model_path: str) -> None:
        payload = joblib.load(model_path)
        self.model = payload["model"]
        self.feature_names = payload.get("feature_names", [])
        self.version = payload.get("version", "unknown")
        self.score_min = payload.get("score_min", -0.5)
        self.score_max = payload.get("score_max", 0.5)

    def anomaly_score(self, feature_vector: List[float]) -> float:
        if self.model is None:
            return 0.0
        values = np.array(feature_vector, dtype=float).reshape(1, -1)
        x = pd.DataFrame(values, columns=self.feature_names) if self.feature_names else values
        try:
            raw = self.model.score_samples(x)[0]  # higher = more normal
        except Exception as exc:
            logger.error("isolation_forest_predict_failed error=%s", exc)
            raise
        # Invert and normalize to 0-1 where 1 = highly anomalous
        span = max(self.score_max - self.score_min, 1e-6)
        normalized = (self.score_max - raw) / span
        return float(np.clip(normalized, 0.0, 1.0))

    @property
    def is_loaded(self) -> bool:
        return self.model is not None
