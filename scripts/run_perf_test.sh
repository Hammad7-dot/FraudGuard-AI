#!/usr/bin/env bash
# Runs the lightweight in-process performance test against the FastAPI app.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest tests/performance -q -s
