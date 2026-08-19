"""Splits the synthetic dataset into X/y using the shared feature schema."""
from __future__ import annotations

import pandas as pd

from ml_pipeline.data_cleaning import FEATURE_COLUMNS

FEATURES_VERSION = "1.0.0"


def split_features_labels(df: pd.DataFrame):
    x = df[FEATURE_COLUMNS].copy()
    y = df["label"].copy()
    return x, y
