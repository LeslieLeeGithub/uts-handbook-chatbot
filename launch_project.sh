#!/bin/bash
# Master launch script for UTS Handbook Chatbot
# This script helps you launch the entire project step by step

set -e  # Exit on error

HANDBOOK_ROOT="/home/lesli/Data/Handbook"
cd "$HANDBOOK_ROOT"

echo "=========================================="
echo "UTS Handbook Chatbot - Complete Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print step
print_step() {
    echo -e "${GREEN}[STEP $1]${NC} $2"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -i :"$1" >/dev/null 2>&1
}

# Step 0: Check prerequisites
print_step "0" "Checking prerequisites..."

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

if ! command_exists conda && ! command_exists pip; then
    echo -e "${RED}❌ Neither conda nor pip found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"
echo ""

# Step 1: Environment setup
print_step "1" "Setting up environment..."

if command_exists conda; then
    echo "Using conda..."
    if conda env list | grep -q "rag-ollama-qwen"; then
        echo "Environment 'rag-ollama-qwen' exists. Activating..."
        eval "$(conda shell.bash hook)"
        conda activate rag-ollama-qwen
    else
        echo "Creating conda environment..."
        conda env create -f env-rag-ollama-qwen.yml
        eval "$(conda shell.bash hook)"
        conda activate rag-ollama-qwen
    fi
else
    echo "Using pip..."
    pip install -r requirements.txt
fi

echo -e "${GREEN}✅ Environment ready${NC}"
echo ""

# Step 2: Check if knowledge base exists
print_step "2" "Checking knowledge base..."

COURSES_DIR="$HANDBOOK_ROOT/data/courses"
CHUNKS_FILE="$HANDBOOK_ROOT/data/processed/courses/courses_chunks.jsonl"
EMBEDDINGS_FILE="$HANDBOOK_ROOT/data/processed/courses/embeddings.npy"
PAYLOADS_FILE="$HANDBOOK_ROOT/data/processed/courses/payloads.jsonl"

if [ ! -f "$CHUNKS_FILE" ] || [ ! -f "$EMBEDDINGS_FILE" ] || [ ! -f "$PAYLOADS_FILE" ]; then
    echo -e "${YELLOW}⚠️  Knowledge base not found. Building it now...${NC}"
    echo ""
    
    # Step 2.1: Ingest courses
    print_step "2.1" "Ingesting course JSON files..."
    python src/rag/ingest_courses.py \
        --courses_dir "$COURSES_DIR" \
        --out "$CHUNKS_FILE"
    
    if [ ! -f "$CHUNKS_FILE" ]; then
        echo -e "${RED}❌ Failed to create chunks file${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Course ingestion complete${NC}"
    echo ""
    
    # Step 2.2: Generate embeddings
    print_step "2.2" "Generating embeddings (this may take 10-30 minutes)..."
    python src/rag/save_kb_files.py \
        --jsonl "$CHUNKS_FILE" \
        --embed_model_dir "$HANDBOOK_ROOT/models/hf/qwen3-embedding-0.6b" \
        --out_dir "$HANDBOOK_ROOT/data/processed/courses" \
        --batch 32
    
    if [ ! -f "$EMBEDDINGS_FILE" ] || [ ! -f "$PAYLOADS_FILE" ]; then
        echo -e "${RED}❌ Failed to generate embeddings${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Embeddings generated${NC}"
    echo ""
    
    # Step 2.3: Check if Qdrant is running
    print_step "2.3" "Checking Qdrant..."
    if ! port_in_use 6333; then
        echo -e "${YELLOW}⚠️  Qdrant is not running. Starting it...${NC}"
        cd src/rag
        ./start_qdrant.sh &
        sleep 5
        cd "$HANDBOOK_ROOT"
    fi
    
    # Wait for Qdrant to be ready
    echo "Waiting for Qdrant to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:6333/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Qdrant is ready${NC}"
            break
        fi
        sleep 1
    done
    
    # Step 2.4: Load into Qdrant
    print_step "2.4" "Loading data into Qdrant..."
    python src/rag/upsert_to_qdrant_from_files.py \
        --payloads "$PAYLOADS_FILE" \
        --emb "$EMBEDDINGS_FILE" \
        --collection courses \
        --skip_version_check
    
    echo -e "${GREEN}✅ Knowledge base loaded into Qdrant${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Knowledge base already exists${NC}"
    echo ""
fi

# Step 3: Start services
print_step "3" "Starting services..."

# Check and start Qdrant
if ! port_in_use 6333; then
    echo "Starting Qdrant..."
    cd src/rag
    ./start_qdrant.sh > "$HANDBOOK_ROOT/logs/qdrant.log" 2>&1 &
    QDRANT_PID=$!
    echo "Qdrant started (PID: $QDRANT_PID)"
    sleep 3
    cd "$HANDBOOK_ROOT"
else
    echo -e "${GREEN}✅ Qdrant is already running${NC}"
fi

# Check and start Ollama
if ! port_in_use 11434; then
    echo "Starting Ollama..."
    cd src/rag
    ./start_ollama.sh > "$HANDBOOK_ROOT/logs/ollama.log" 2>&1 &
    OLLAMA_PID=$!
    echo "Ollama started (PID: $OLLAMA_PID)"
    sleep 3
    cd "$HANDBOOK_ROOT"
else
    echo -e "${GREEN}✅ Ollama is already running${NC}"
fi

# Verify services
echo ""
echo "Verifying services..."
sleep 2

if curl -s http://localhost:6333/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant is running${NC}"
else
    echo -e "${RED}❌ Qdrant is not responding${NC}"
fi

if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama is not responding (may still be starting)${NC}"
fi

echo ""

# Step 4: Start API server
print_step "4" "Starting API server..."

if port_in_use 8000; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    echo "API server may already be running, or you need to stop the existing process"
else
    echo "Starting API server on http://localhost:8000"
    echo "Press Ctrl+C to stop"
    echo ""
    python src/api_server.py
fi

