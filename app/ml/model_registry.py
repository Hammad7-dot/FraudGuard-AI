"""Loads and caches ML models, and records model metadata."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from app.ml.isolation_forest_model import IsolationForestAnomalyModel
from app.ml.shap_explainer import ShapExplainer
from app.ml.xgboost_model import XGBoostFraudModel

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    model_name: str
    version: str
    training_date: str
    dataset_version: str
    features_version: str
    metrics: dict


class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None

    def __init__(self) -> None:
        settings = get_settings()
        self.model_dir = settings.model_dir
        self.xgb_model = XGBoostFraudModel()
        self.iso_model = IsolationForestAnomalyModel()
        self.shap_explainer: Optional[ShapExplainer] = None
        self._load_latest()

    @staticmethod
    def _version_key(filename: str) -> tuple:
        match = re.search(r"_v(\d+)\.(\d+)\.(\d+)", filename)
        if not match:
            return (-1, -1, -1)
        return tuple(int(part) for part in match.groups())

    def _latest_path(self, prefix: str) -> Optional[str]:
        if not os.path.isdir(self.model_dir):
            return None
        candidates = [f for f in os.listdir(self.model_dir) if f.startswith(prefix) and f.endswith(".pkl")]
        if not candidates:
            return None
        candidates.sort(key=self._version_key)
        return os.path.join(self.model_dir, candidates[-1])

    def _load_latest(self) -> None:
        xgb_path = self._latest_path("fraud_xgboost")
        iso_path = self._latest_path("isolation_forest")
        if xgb_path:
            try:
                self.xgb_model.load(xgb_path)
                logger.info("loaded_model path=%s", xgb_path)
            except Exception as exc:  # pragma: no cover
                logger.warning("failed_to_load_xgboost error=%s", exc)
        if self.xgb_model.is_loaded:
            self.shap_explainer = ShapExplainer(self.xgb_model.model)
        if iso_path:
            try:
                self.iso_model.load(iso_path)
                logger.info("loaded_model path=%s", iso_path)
            except Exception as exc:  # pragma: no cover
                logger.warning("failed_to_load_isolation_forest error=%s", exc)

    def get_metadata(self, prefix: str) -> Optional[dict]:
        meta_path = os.path.join(self.model_dir, f"{prefix}_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                return json.load(f)
        return None

    @classmethod
    def instance(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
