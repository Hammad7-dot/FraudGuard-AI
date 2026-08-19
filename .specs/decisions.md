# Architecture Decision Records

## ADR-001: FastAPI
Chosen for async support, Pydantic validation, automatic OpenAPI docs, easy ML integration, and
strong performance characteristics for a real-time scoring API.

## ADR-002: PostgreSQL
Chosen as the system of record: reliable, transactional, strong Python support (SQLAlchemy),
and analytics-friendly for reporting/dashboard queries.

## ADR-003: Redis
Chosen for fast access to recent transaction velocity, device history, location history, and
short-window user behavior. Postgres alone is not ideal for every real-time lookup at
sub-100ms latency targets.

## ADR-004: XGBoost
Chosen for the supervised model: strong tabular performance, captures nonlinear relationships,
established fraud-detection baseline, provides feature importance, and is SHAP-friendly for
explainability.

## ADR-005: Isolation Forest
Chosen as a second, independent detection mechanism that does not require labels, catching
unusual patterns the supervised classifier may miss or that predate labeled fraud examples.

## ADR-006: Hybrid Risk Engine
Combines rules + ML + anomaly detection so no single mechanism is a single point of failure;
deterministic rules catch known hard patterns even if models drift or misbehave.

## ADR-007: Postgres as Source of Truth
Redis is explicitly ephemeral. A Redis outage or flush must not destroy transaction/risk
history — Postgres always persists the durable record.
