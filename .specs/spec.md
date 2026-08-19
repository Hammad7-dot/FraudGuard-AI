# FraudGuard AI — Project Specification

## 1. Project Overview
Build a production-style fraud detection platform capable of analyzing financial transactions in
real time and assigning each transaction a fraud risk score. The system combines supervised
machine learning, unsupervised anomaly detection, rule-based fraud detection, Redis-based
real-time state, PostgreSQL persistence, FastAPI, streaming transaction processing, explainable
risk scoring, and real-time monitoring. Primary objective: given a transaction, determine how
risky it is, explain why, and decide whether it should be approved, reviewed, or blocked.

## 2. Goals
- Accept transaction events
- Validate transaction data
- Extract relevant features
- Run fraud detection models
- Detect anomalous transactions
- Apply deterministic fraud rules
- Calculate a unified risk score
- Classify transaction risk
- Store transaction results
- Maintain real-time user/device history
- Provide an API for transaction scoring
- Provide fraud analytics
- Provide explanations for risk decisions

Every transaction receives `risk_score` (0-100), `risk_level` (LOW|MEDIUM|HIGH|CRITICAL),
`decision` (APPROVE|REVIEW|BLOCK).

## 3. Non-Goals
No real banking transactions, no real bank account connections, no automatic account freezing,
no legally binding decisions, no accuracy guarantees, not a replacement for production bank
fraud infra, no real customer financial data — all data synthetic/public.

## 4-5. Functional Requirements
- FR-01 Transaction Ingestion via `POST /api/v1/transactions`
- FR-02 Input Validation, invalid → 400

## 6. Feature Engineering
- Transaction features: amount, currency, merchant_category, country, hour, day_of_week
- User behavior features: average_transaction_amount, transaction_count_1h, transaction_count_24h,
  average_amount_24h, amount_deviation
- Velocity features: transactions_last_5_minutes, transactions_last_15_minutes,
  transactions_last_1_hour, amount_last_1_hour
- Device features: new_device, device_transaction_count, devices_used_by_user
- Geographic features: country_changed, distance_from_previous_transaction, impossible_travel

## 7. Redis
Keys: `fraud:user:{id}:transactions`, `fraud:user:{id}:amounts`, `fraud:user:{id}:devices`,
`fraud:user:{id}:last_location`. Real-time state; TTLs documented in code.

## 8. Models
- Model A: XGBoost → fraud_probability
- Model B: Isolation Forest → anomaly_score
- Model C: Rule engine, deterministic

## 9. Risk Scoring
`risk_score = ML_probability*50 + anomaly_score*25 + rule_score*25`
Levels: 0-29 LOW, 30-59 MEDIUM, 60-79 HIGH, 80-100 CRITICAL.
Decisions: LOW→APPROVE, MEDIUM→APPROVE/REVIEW, HIGH→REVIEW, CRITICAL→BLOCK. Thresholds
configurable.

## 10. Explainability
`reasons[]` for high-risk transactions using SHAP for the supervised model plus triggered rules.

## 11. API
- `POST /api/v1/transactions`, `GET /api/v1/transactions/{id}`
- `GET /api/v1/risk/{id}`
- `GET /api/v1/users/{id}/risk`, `GET /api/v1/users/{id}/history`
- `GET /api/v1/analytics/overview|fraud-trends|high-risk`
- `GET /health`, `/ready`

## 12. Database
Tables: `transactions`, `risk_assessments`, `fraud_reasons`, `users`, `devices`.

## 13. Streaming Architecture
Transaction → FastAPI → Validation → Feature Engine → (Redis + PostgreSQL) → ML Prediction →
Risk Aggregator → Risk Decision → APPROVE/REVIEW/BLOCK.

## 14. Real-Time Requirements
Target <500ms per transaction, ideal <100ms; measure feature_generation_ms, ml_prediction_ms,
rule_engine_ms, redis_latency_ms, database_latency_ms, total_processing_ms.

## 15. ML Requirements
Full training pipeline; class imbalance handling; evaluate with Precision/Recall/F1/PR-AUC/
ROC-AUC/Confusion Matrix, not accuracy alone.

## 16. Model Versioning
`model_name`, `model_version`, `training_date`, `dataset_version`, `features_version`, `metrics`
recorded per prediction/model registry entry.

## 17. Monitoring
Dashboard KPIs: Total Transactions, Fraud Detected, Fraud Rate, Blocked, Review, Avg Risk Score,
High-Risk count, Avg Processing Time. Charts: fraud rate over time, tx/min, risk score
distribution, fraud by country/merchant/device, top fraud indicators.

## 18. Alerts
Detect spikes in fraud rate (dashboard + webhook), MVP-level.

## 19. Security
Validate all input, no secrets exposed, env vars, no sensitive data logged, API auth, rate
limiting, request size validation, sanitized error responses, `.env` never committed.

## 20. Testing
Unit (features, scoring, rules, classification, validation), integration
(FastAPI→Redis→ML→Postgres), ML tests (model loading, prediction shape, probability range,
feature compatibility), performance test (synthetic tx, avg/p95/p99 latency, throughput).

## 21. Acceptance Criteria
Transaction API works; validation works; Redis stores recent activity; feature engineering
works; XGBoost + Isolation Forest + rule engine all work; risk aggregator produces 0-100 score;
APPROVE/REVIEW/BLOCK decisions made; explanations returned; Postgres stores
transactions/risk assessments; tests pass; ML metrics documented; docker-compose starts full
system; dashboard shows fraud metrics; health checks work; no secrets committed; README
explains architecture/setup.

## 22-24. Recommended Technology Stack
FastAPI, PostgreSQL, Redis, SQLAlchemy + Alembic, XGBoost + scikit-learn IsolationForest, SHAP,
Streamlit, Docker Compose, pytest.

## Development Phases
1. Scaffolding, config, schemas, DB models
2. Feature engineering + Redis streaming state
3. ML pipeline (synthetic data, training, evaluation, serialization)
4. Rule engine + risk aggregator + explanation service
5. API wiring, security, logging, exception handling
6. Dashboard
7. Tests (unit/integration/ml/performance) + docs

## Final Portfolio Architecture
```
Client -> FastAPI (/api/v1) -> Feature Service -> Redis (velocity/device/geo state)
                              -> ML Layer (XGBoost + IsolationForest + SHAP)
                              -> Rule Engine
                              -> Risk Aggregator -> Decision
                              -> PostgreSQL (transactions, risk_assessments, fraud_reasons,
                                              users, devices)
Streamlit Dashboard -> reads FastAPI / DB for KPIs, charts, high-risk queue, model metrics.
```
