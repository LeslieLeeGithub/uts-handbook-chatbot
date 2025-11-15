#!/usr/bin/env bash
set -e

# Get the project root directory (parent of src/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HANDBOOK_ROOT="${HANDBOOK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Export HANDBOOK_ROOT so child scripts can use it
export HANDBOOK_ROOT

"${SCRIPT_DIR}/start_qdrant.sh"
sleep 1
"${SCRIPT_DIR}/start_ollama.sh"
