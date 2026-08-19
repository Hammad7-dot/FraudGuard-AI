import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.config import get_settings  # noqa: E402
from dashboard.components.theme import (empty_state, page_header, section_title,  # noqa: E402
                                         sidebar_brand)

st.set_page_config(page_title="Model Metrics — FraudGuard AI", page_icon="🧠", layout="wide")
sidebar_brand()
page_header("🧠", "Model Metrics", "Training metrics and metadata for the two ML models behind the risk score.")

settings = get_settings()
model_dir = settings.model_dir

for prefix, label, icon in [
    ("fraud_xgboost", "XGBoost Fraud Classifier", "🌳"),
    ("isolation_forest", "Isolation Forest (anomaly detection)", "🌲"),
]:
    meta_path = os.path.join(model_dir, f"{prefix}_metadata.json")
    section_title(f"{icon} {label}")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)

        metrics = meta.get("metrics", meta) if isinstance(meta, dict) else {}
        numeric_metrics = {
            k: v for k, v in metrics.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
        } if isinstance(metrics, dict) else {}

        if numeric_metrics:
            keys = list(numeric_metrics.keys())[:5]
            cols = st.columns(len(keys))
            for c, k in zip(cols, keys):
                v = numeric_metrics[k]
                c.metric(k.replace("_", " ").title(), f"{v:.4f}" if isinstance(v, float) else v)

        with st.expander("Full metadata"):
            st.json(meta)
    else:
        empty_state(f"No metadata found at {meta_path}. Run `python -m ml_pipeline.serialize_model` to train models.")
