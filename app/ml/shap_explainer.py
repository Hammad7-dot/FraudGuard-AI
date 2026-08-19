"""SHAP-based explanations for the XGBoost model, with graceful fallback."""
from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import shap  # noqa: F401
    SHAP_AVAILABLE = True
except ImportError:  # pragma: no cover
    SHAP_AVAILABLE = False
    logger.warning("shap not available, explanations will fall back to feature-deviation heuristics")


class ShapExplainer:
    def __init__(self, model) -> None:
        self.model = model
        self._explainer = None
        if SHAP_AVAILABLE and model is not None:
            try:
                import shap
                self._explainer = shap.TreeExplainer(model)
            except Exception as exc:  # pragma: no cover
                logger.warning("shap_explainer_init_failed error=%s", exc)
                self._explainer = None

    @property
    def available(self) -> bool:
        return self._explainer is not None

    def top_contributions(self, feature_vector: List[float], feature_names: List[str], top_n: int = 3) -> List[Tuple[str, float]]:
        if not self.available:
            return []
        try:
            x = np.array(feature_vector, dtype=float).reshape(1, -1)
            shap_values = self._explainer.shap_values(x)
            # For a binary classifier, shap_values() may return [class0, class1];
            # we want the fraud (positive) class's contributions.
            values = shap_values[1] if isinstance(shap_values, list) else shap_values[0]
            pairs = list(zip(feature_names, values))
            pairs.sort(key=lambda p: abs(p[1]), reverse=True)
            return pairs[:top_n]
        except Exception as exc:  # pragma: no cover
            logger.warning("shap_explain_failed error=%s", exc)
            return []
