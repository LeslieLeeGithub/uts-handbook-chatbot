#!/usr/bin/env bash
set -e

# Get the project root directory (parent of src/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HANDBOOK_ROOT="${HANDBOOK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Stop Qdrant and Ollama processes
pkill -f "${HANDBOOK_ROOT}/models/qdrant/bin/qdrant" || true
pkill -f "${HANDBOOK_ROOT}/models/ollama/bin/ollama serve" || true
echo "Stopped Qdrant and Ollama."
