"""Generates and cleans a synthetic transaction dataset for training.

No real fraud data is available (see .specs/blocked.md BLOCK-003), so this module produces a
synthetic dataset with injected fraudulent patterns matching the feature schema used at
inference time (app/services/feature_service.py FEATURE_ORDER).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "amount",
    "hour",
    "day_of_week",
    "avg_transaction_amount",
    "transaction_count_1h",
    "transaction_count_24h",
    "amount_deviation",
    "transactions_last_5_minutes",
    "transactions_last_15_minutes",
    "transactions_last_1_hour",
    "amount_last_1_hour",
    "new_device",
    "device_transaction_count",
    "country_changed",
    "distance_from_previous_transaction",
    "impossible_travel",
]


def generate_synthetic_dataset(n_samples: int = 20_000, fraud_rate: float = 0.03, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_fraud = int(n_samples * fraud_rate)
    n_legit = n_samples - n_fraud

    def legit_rows(n: int) -> pd.DataFrame:
        avg_amount = rng.gamma(shape=3.0, scale=40, size=n) + 10
        amount = avg_amount * rng.normal(1.0, 0.25, n).clip(0.1, None)
        return pd.DataFrame({
            "amount": amount,
            "hour": rng.integers(0, 24, n),
            "day_of_week": rng.integers(0, 7, n),
            "avg_transaction_amount": avg_amount,
            "transaction_count_1h": rng.poisson(0.3, n),
            "transaction_count_24h": rng.poisson(3, n),
            "amount_deviation": (amount - avg_amount) / avg_amount,
            "transactions_last_5_minutes": rng.poisson(0.1, n),
            "transactions_last_15_minutes": rng.poisson(0.2, n),
            "transactions_last_1_hour": rng.poisson(0.4, n),
            "amount_last_1_hour": amount * rng.poisson(0.4, n),
            "new_device": rng.binomial(1, 0.05, n),
            "device_transaction_count": rng.integers(1, 50, n),
            "country_changed": rng.binomial(1, 0.02, n),
            "distance_from_previous_transaction": rng.exponential(50, n),
            "impossible_travel": np.zeros(n),
            "label": np.zeros(n, dtype=int),
        })

    def fraud_rows(n: int) -> pd.DataFrame:
        avg_amount = rng.gamma(shape=3.0, scale=40, size=n) + 10
        # Fraud: much larger amounts, high velocity, new devices, impossible travel
        amount = avg_amount * rng.uniform(4, 20, n)
        impossible_travel = rng.binomial(1, 0.4, n)
        return pd.DataFrame({
            "amount": amount,
            "hour": rng.integers(0, 24, n),
            "day_of_week": rng.integers(0, 7, n),
            "avg_transaction_amount": avg_amount,
            "transaction_count_1h": rng.poisson(4, n),
            "transaction_count_24h": rng.poisson(12, n),
            "amount_deviation": (amount - avg_amount) / avg_amount,
            "transactions_last_5_minutes": rng.poisson(4, n),
            "transactions_last_15_minutes": rng.poisson(6, n),
            "transactions_last_1_hour": rng.poisson(8, n),
            "amount_last_1_hour": amount * rng.poisson(3, n),
            "new_device": rng.binomial(1, 0.7, n),
            "device_transaction_count": rng.integers(0, 3, n),
            "country_changed": rng.binomial(1, 0.5, n),
            "distance_from_previous_transaction": rng.exponential(4000, n),
            "impossible_travel": impossible_travel,
            "label": np.ones(n, dtype=int),
        })

    df = pd.concat([legit_rows(n_legit), fraud_rows(n_fraud)], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return clean_dataset(df)


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna()
    for col in FEATURE_COLUMNS:
        df[col] = df[col].clip(lower=-1e6, upper=1e6)
    df["amount"] = df["amount"].clip(lower=0.01)
    return df


if __name__ == "__main__":
    dataset = generate_synthetic_dataset()
    dataset.to_csv("data/processed/synthetic_transactions.csv", index=False)
    print(f"Generated {len(dataset)} rows -> data/processed/synthetic_transactions.csv")
