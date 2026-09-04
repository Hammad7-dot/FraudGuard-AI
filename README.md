# FraudGuard AI — Real-Time Fraud Detection & Risk Engine

A portfolio-grade fraud detection MVP: FastAPI + SQLAlchemy + Redis + XGBoost + Isolation
Forest + a deterministic rule engine, combined into a single 0-100 risk score, with a
Streamlit monitoring dashboard.

See `.specs/spec.md`, `.specs/rules.md`, `.specs/decisions.md`, `.specs/blocked.md` for the
full spec, engineering rules, ADRs, and known limitations this build intentionally defers.

## Architecture

```
Client -> FastAPI (/api/v1) -> FeatureService -> Redis (velocity/device/geo state, degrades gracefully)
                              -> ML layer (XGBoost + IsolationForest [+ SHAP if available])
                              -> Rule engine (deterministic)
                              -> Risk aggregator -> risk_score/level/decision
                              -> PostgreSQL/SQLite (transactions, risk_assessments,
                                                     fraud_reasons, users, devices)
Streamlit dashboard -> reads directly from the same DB for KPIs/charts/high-risk queue/model metrics.
```

Risk formula: `risk_score = fraud_probability*50 + anomaly_score*25 + rule_score*25` (0-100).
Levels: 0-29 LOW, 30-59 MEDIUM, 60-79 HIGH, 80-100 CRITICAL (configurable in `app/core/config.py`).
Decisions: LOW→APPROVE, MEDIUM→APPROVE/REVIEW (REVIEW if score ≥ 45), HIGH→REVIEW, CRITICAL→BLOCK.

## Local development (quick start, no Docker required)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Uses SQLite (DATABASE_URL default) and gracefully degrades if Redis isn't running.
cp .env.example .env   # required: replace API_KEY with a private value

# Train models (writes versioned artifacts to data/models/)
python -m ml_pipeline.serialize_model

# Run the API
uvicorn app.main:app --reload

# In another shell, seed some sample data
python scripts/seed_db.py 100

# Run the dashboard
streamlit run dashboard/streamlit_app.py
```

By default `REQUIRE_API_KEY=true`, so `API_KEY` must be supplied through `.env` or the
environment. Send that private value in the `x-api-key` header on protected requests.
The static dashboard asks for the key at runtime and keeps it only in page memory.

## Full stack via Docker Compose (FastAPI + Postgres + Redis + Streamlit)

```bash
$env:API_KEY="replace-with-a-long-random-value"  # PowerShell
docker compose up --build
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:8501

`docker-compose.yml` wires the API to Postgres (`DATABASE_URL`) and Redis (`REDIS_URL`); the
dashboard reads from the same Postgres instance.

## Running tests

```bash
pytest tests/unit tests/integration tests/ml -q
```

Performance test (in-process, ~200 synthetic transactions through a TestClient, prints
avg/p95/p99 latency):

```bash
bash scripts/run_perf_test.sh
# or directly:
pytest tests/performance -q -s
```

## Training models

`ml_pipeline/` generates a synthetic dataset on the fly (no real fraud data exists — see
`.specs/blocked.md` BLOCK-003), trains XGBoost (falls back to sklearn GradientBoosting if
xgboost isn't installable) and an Isolation Forest, evaluates with precision/recall/F1/
PR-AUC/ROC-AUC/confusion matrix, and serializes versioned artifacts + metadata JSON to
`data/models/`:

```bash
python -m ml_pipeline.serialize_model
```

`app/ml/model_registry.py` auto-loads the latest matching artifact on API startup.

## API surface

- `POST /api/v1/transactions` — score a transaction, persist it, return risk_score/level/decision/reasons
- `GET /api/v1/transactions/{id}` — retrieve full transaction details & risk evaluation
- `POST /api/v1/transactions/{id}/feedback` — submit analyst feedback (`CONFIRMED_FRAUD`, `FALSE_POSITIVE`, `LEGITIMATE`) with optional analyst notes
- `GET /api/v1/risk/{id}`
- `GET /api/v1/users/{id}/risk`, `GET /api/v1/users/{id}/history`
- `GET /api/v1/analytics/overview`, `/fraud-trends`, `/high-risk`
- `GET /health`, `GET /api/v1/ready`

## Database

Defaults to SQLite (`sqlite:///./fraudguard.db`) for zero-setup local dev; set `DATABASE_URL`
to a Postgres DSN for production use (intended DB per spec). Alembic migrations live in
`app/db/migrations/` (`alembic upgrade head`); `init_db()` also auto-creates tables as a
convenience fallback for quick local runs.

## Redis key design

- `fraud:user:{id}:transactions` — sorted set of transaction epoch timestamps, TTL 1h
- `fraud:user:{id}:amounts` — sorted set of `timestamp:amount`, TTL 1h
- `fraud:user:{id}:devices` — set of device ids seen for the user, TTL 30d
- `fraud:user:{id}:last_location` — hash of last known lat/lon/country/timestamp, TTL 7d

Redis is treated as ephemeral, real-time state only — PostgreSQL is the system of record
(ADR-007). If Redis is unreachable, `RedisClient` catches the connection error, logs a
warning, and every tracker falls back to safe defaults so the API keeps working.

## Known gaps vs. the full spec (see `.specs/blocked.md`)

- No Kafka streaming bus (BLOCK-002, deferred) — the MVP processes transactions synchronously
  through FastAPI + Redis instead.
- No production fraud labels (BLOCK-003) — models train on a synthetic dataset with injected
  fraud patterns.
- No Prometheus/Grafana — structured logging is used instead; the Streamlit dashboard covers
  the monitoring requirement for this MVP.
- No automatic model retraining/drift detection (BLOCK-005) — models are trained on demand via
  `ml_pipeline/serialize_model.py`.
- No real banking integration, account freezing, or accuracy guarantees (BLOCK-001, BLOCK-004)
  — by design, per non-goals.
