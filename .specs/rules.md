# Engineering Rules

## Code
- Type hints everywhere
- PEP 8 formatting
- Business logic lives outside API routes (in services/ml/rules layers)
- Small, testable functions
- No hardcoded secrets — env-var config only
- Pydantic schemas for all I/O
- Structured logging
- Explicit exception handling

## ML
- Never train on the test set
- Prevent data leakage
- Preserve feature schema between training and inference
- Save model metadata + version alongside artifacts
- Evaluate with fraud-appropriate metrics (precision/recall/F1/PR-AUC/ROC-AUC/confusion matrix),
  not accuracy alone
- Document class imbalance handling

## Redis
- Temporary state only — Postgres is the source of truth
- Documented key naming and TTLs
- Never depend solely on Redis for history

## API
- Version everything under `/api/v1`
- Consistent error response schema
- Validate all input
- No internal stack traces exposed to clients
- Auth required for protected endpoints

## Security
- Never commit `.env`
- Never log passwords/API keys
- No real financial data — synthetic/test data only
