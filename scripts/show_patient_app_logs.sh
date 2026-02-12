#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
APP_LOG="$LOG_DIR/patient_calculator_errors.log"
RUNTIME_LOG="$LOG_DIR/patient_calculator_runtime.log"

echo "=== App Exception Log ==="
if [[ -f "$APP_LOG" ]]; then
  tail -n 200 "$APP_LOG"
else
  echo "No file: $APP_LOG"
fi

echo
echo "=== Streamlit Runtime Log ==="
if [[ -f "$RUNTIME_LOG" ]]; then
  tail -n 200 "$RUNTIME_LOG"
else
  echo "No file: $RUNTIME_LOG"
fi
