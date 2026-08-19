"""Generates a stream of synthetic transactions (some fraudulent patterns) for demos."""
from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

MERCHANT_CATEGORIES = ["grocery", "electronics", "travel", "restaurant", "fuel", "online_retail", "jewelry"]
COUNTRIES = ["US", "GB", "FR", "DE", "IN", "CN", "JP", "AU", "BR", "CA", "NG", "AE"]
CURRENCIES = ["USD", "GBP", "EUR", "INR", "JPY", "AUD"]


def generate_transaction(user_id: str, fraudulent: bool, base_time: datetime) -> dict:
    if fraudulent:
        amount = round(random.uniform(3000, 25000), 2)
        country = random.choice(COUNTRIES)
        device_id = f"device-{uuid.uuid4().hex[:8]}"
    else:
        amount = round(random.uniform(5, 400), 2)
        country = "US"
        device_id = f"device-{user_id}-primary"

    return {
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": amount,
        "currency": random.choice(CURRENCIES),
        "merchant_id": f"merchant-{random.randint(1, 500)}",
        "merchant_category": random.choice(MERCHANT_CATEGORIES),
        "country": country,
        "device_id": device_id,
        "timestamp": base_time.isoformat(),
    }


def generate_stream(n: int = 100, fraud_rate: float = 0.08, users: int = 20) -> list[dict]:
    transactions = []
    now = datetime.now(timezone.utc)
    for i in range(n):
        user_id = f"user-{random.randint(1, users)}"
        fraudulent = random.random() < fraud_rate
        ts = now - timedelta(minutes=random.randint(0, 60 * 24))
        transactions.append(generate_transaction(user_id, fraudulent, ts))
    return transactions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--fraud-rate", type=float, default=0.08)
    parser.add_argument("--out", type=str, default="data/raw/synthetic_transactions.jsonl")
    args = parser.parse_args()

    txs = generate_stream(n=args.count, fraud_rate=args.fraud_rate)
    with open(args.out, "w") as f:
        for tx in txs:
            f.write(json.dumps(tx) + "\n")
    print(f"Wrote {len(txs)} synthetic transactions to {args.out}")
