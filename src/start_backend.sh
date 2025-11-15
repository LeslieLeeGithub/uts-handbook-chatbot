#!/bin/bash
# Quick start script for Handbook Chatbot Backend

echo "🚀 Starting Handbook Chatbot Backend..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed or not in PATH"
    exit 1
fi

# Activate conda environment
# IMPORTANT: Use 'stormai' environment where RAG dependencies are installed
echo "📦 Activating conda environment 'stormai'..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate stormai

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate conda environment 'stormai'"
    echo "   The API server needs 'stormai' environment (not 'stormai-be')"
    echo "   because it imports RAG query functions that require:"
    echo "   - sentence-transformers"
    echo "   - qdrant-client"
    echo "   - ollama"
    echo "   - transformers"
    echo ""
    echo "   Try: conda activate stormai"
    exit 1
fi

# Check if Qdrant and Ollama are running
echo "🔍 Checking services..."
qdrant_running=$(ss -ltnp 2>/dev/null | grep -c ':6333' || echo "0")
ollama_running=$(ss -ltnp 2>/dev/null | grep -c ':11434' || echo "0")

# Get the project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
STORM_AI_ROOT="${STORM_AI_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

if [ "$qdrant_running" -eq 0 ]; then
    echo "⚠️  Qdrant is not running on port 6333"
    echo "   Start it with: ${STORM_AI_ROOT}/scripts/start_qdrant.sh"
fi

if [ "$ollama_running" -eq 0 ]; then
    echo "⚠️  Ollama is not running on port 11434"
    echo "   Start it with: ${STORM_AI_ROOT}/scripts/start_ollama.sh"
fi

if [ "$qdrant_running" -eq 0 ] || [ "$ollama_running" -eq 0 ]; then
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Change to backend directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/backend"

# Check if api_server.py exists
if [ ! -f "api_server.py" ]; then
    echo "❌ api_server.py not found in $SCRIPT_DIR/backend"
    exit 1
fi

# Start the FastAPI server
echo ""
echo "🌟 Starting FastAPI server on http://localhost:8000"
echo "📚 API docs available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python api_server.py

