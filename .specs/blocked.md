# Known Limitations / Blocked Items

## BLOCK-001: Real Banking Integration
Status: Blocked, out of scope. No connections to real bank accounts or payment processors.

## BLOCK-002: Real-Time Kafka Streaming
Status: Deferred to Phase 2. MVP uses direct FastAPI request handling + Redis for real-time
state instead of a Kafka event bus.

## BLOCK-003: Production Fraud Labels
Status: Blocked. No access to real, labeled production fraud data; the project uses
synthetically generated data with injected fraud patterns.

## BLOCK-004: Guaranteed Fraud Accuracy
Status: Not possible. Fraud patterns evolve continuously; no model can guarantee accuracy
against adversarial, adaptive behavior.

## BLOCK-005: Automatic Model Retraining
Status: Deferred to a future drift-detection / retraining pipeline. MVP models are trained
once via `ml_pipeline/` scripts and manually re-run when needed.

## Also deferred (advanced/production-scale infra, out of scope for this MVP)
- Prometheus / Grafana observability stack (structured logs used instead)
- Kubernetes deployment manifests (docker-compose only)
- Multi-region / high-availability Redis and Postgres clustering
