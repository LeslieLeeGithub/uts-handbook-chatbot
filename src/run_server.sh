#!/usr/bin/env bash
set -euo pipefail

export $(grep -v '^#' configs/example.env | xargs -d '\n' -I {} echo {}) || true

# Use PORT environment variable or default to 8001 (to avoid conflict with other projects)
PORT=${PORT:-8001}

uvicorn src.chatbot.app:app --host 0.0.0.0 --port $PORT


