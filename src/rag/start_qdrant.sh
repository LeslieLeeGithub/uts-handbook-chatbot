#!/usr/bin/env bash
set -euo pipefail

# Get the project root directory (parent of src/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HANDBOOK_ROOT="${HANDBOOK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

QDRANT_BASE="${HANDBOOK_ROOT}/models/qdrant"
QDRANT_STORE="${HANDBOOK_ROOT}/models/qdrant_store"
QDRANT_LOG="${HANDBOOK_ROOT}/logs/qdrant.log"
mkdir -p "$(dirname "$QDRANT_LOG")" "$QDRANT_STORE"

# Create a config file for Qdrant
QDRANT_CONFIG="${HANDBOOK_ROOT}/models/qdrant_config.yaml"
cat > "$QDRANT_CONFIG" << EOF
storage:
  storage_path: "$QDRANT_STORE"

service:
  http_port: 6333
  grpc_port: 6334
  host: "127.0.0.1"
EOF

nohup "$QDRANT_BASE/bin/qdrant" --config-path "$QDRANT_CONFIG" \
  >"$QDRANT_LOG" 2>&1 &
echo "Qdrant started → http://127.0.0.1:6333  (log: $QDRANT_LOG)"
