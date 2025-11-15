#!/usr/bin/env bash
set -euo pipefail

# Get the project root directory (parent of src/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HANDBOOK_ROOT="${HANDBOOK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

BASE="${HANDBOOK_ROOT}/models/ollama"
STORE="${HANDBOOK_ROOT}/models/ollama_store"
LOG="${HANDBOOK_ROOT}/logs/ollama.log"
mkdir -p "$(dirname "$LOG")" "$STORE"
nohup env LD_LIBRARY_PATH="$BASE/lib:${LD_LIBRARY_PATH:-}" \
  OLLAMA_MODELS="$STORE" \
  OLLAMA_HOST="127.0.0.1:11434" \
  "$BASE/bin/ollama" serve \
  >"$LOG" 2>&1 &
echo "Ollama started → http://127.0.0.1:11434  (log: $LOG)"
