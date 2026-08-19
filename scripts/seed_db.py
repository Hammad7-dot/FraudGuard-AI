"""Seeds the database with sample transactions by POSTing to a running API, or directly via the
transaction service if the API is not reachable.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime  # noqa: E402

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.schemas.transaction import TransactionCreate  # noqa: E402
from app.services.transaction_service import TransactionService  # noqa: E402
from app.streaming.redis_client import get_redis_client  # noqa: E402
from scripts.generate_synthetic_transactions import generate_stream  # noqa: E402


def seed(n: int = 100) -> None:
    init_db()
    db = SessionLocal()
    redis_client = get_redis_client()
    service = TransactionService(db, redis_client)

    transactions = generate_stream(n=n)
    created = 0
    for raw in transactions:
        try:
            tx = TransactionCreate(**raw)
            service.process_transaction(tx)
            created += 1
        except Exception as exc:
            print(f"skip {raw.get('transaction_id')}: {exc}")
    db.close()
    print(f"Seeded {created}/{len(transactions)} transactions")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    seed(count)
