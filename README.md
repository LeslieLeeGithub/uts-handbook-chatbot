# UTS Handbook Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers questions about UTS courses using Qwen embeddings, Qdrant vector database, and Ollama LLM.

## Features

- 🤖 **Intelligent Course Search**: Ask questions about UTS courses and get accurate answers
- 🔍 **Automatic Course Code Detection**: Extracts course codes (e.g., C04379) from your questions
- 📚 **Comprehensive Course Data**: Answers questions about admission requirements, career options, subjects, and more
- 🚀 **Fast Setup**: Automated scripts for building the knowledge base and launching services
- 💬 **Web Interface**: Simple HTML/CSS/JS frontend with chat widget

## Project Structure

```
Handbook/
├── src/
│   ├── api_server.py          # FastAPI backend server
│   ├── rag/                   # RAG pipeline scripts
│   │   ├── ingest_courses.py  # Convert JSON → chunks
│   │   ├── save_kb_files.py   # Generate embeddings
│   │   ├── upsert_to_qdrant_from_files.py  # Load into Qdrant
│   │   ├── query_hybrid_rag.py # Query functions
│   │   └── filtered_retrieval.py
│   ├── js/chatbot.js          # Frontend JavaScript
│   ├── css/chatbot.css        # Frontend styles
│   └── crawl/                 # Course crawler
├── data/
│   ├── courses/               # Course JSON files (input)
│   └── processed/             # Processed chunks and embeddings
├── models/                    # Embedding models (not in git)
├── test_chatbot.html          # Test frontend
├── launch_project.sh          # Automated launch script
└── requirements.txt          # Python dependencies
```

## Prerequisites

- Python 3.8+ (Python 3.11 recommended)
- Conda (recommended) or pip
- 8GB+ RAM (16GB recommended)
- GPU (optional, for faster embeddings)

## Quick Start

### 1. Environment Setup

```bash
cd /path/to/Handbook

# Option A: Using conda (recommended)
conda env create -f env-rag-ollama-qwen.yml
conda activate SIG

# Option B: Using pip
pip install -r requirements.txt
```

### 2. Download Models

**Embedding Model** (auto-downloads on first use):
- Model: `qwen3-embedding-0.6b`
- Location: `models/hf/qwen3-embedding-0.6b`
- Downloads automatically when running `save_kb_files.py`

**Ollama Model** (after starting Ollama):
```bash
ollama pull qwen2.5:7b
```

### 3. Build Knowledge Base

**Step 1: Ingest Course JSON Files**
```bash
python src/rag/ingest_courses.py \
  --courses_dir data/courses \
  --out data/processed/courses/courses_chunks.jsonl
```

This processes all JSON files in `data/courses/` and creates chunks with metadata.

**Step 2: Generate Embeddings**
```bash
python src/rag/save_kb_files.py \
  --jsonl data/processed/courses/courses_chunks.jsonl \
  --embed_model_dir models/hf/qwen3-embedding-0.6b \
  --out_dir data/processed/courses \
  --batch 32
```

This generates vector embeddings (takes 10-30 minutes depending on CPU/GPU).

**Step 3: Load into Qdrant**
```bash
python src/rag/upsert_to_qdrant_from_files.py \
  --payloads data/processed/courses/payloads.jsonl \
  --emb data/processed/courses/embeddings.npy \
  --collection courses \
  --skip_version_check
```

### 4. Launch Services

**Automated (Recommended):**
```bash
./launch_project.sh
```

**Manual:**
```bash
# Terminal 1: Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# Terminal 2: Start Ollama
ollama serve

# Terminal 3: Start API Server
conda activate SIG
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 4: Start Frontend (optional)
cd /path/to/Handbook
python3 -m http.server 8080
```

### 5. Test the Chatbot

Open `http://localhost:8080/test_chatbot.html` in your browser.

Try asking:
- "which subjects do i need to do for C04379"
- "tell me about the Bachelor of Business"
- "what are the admission requirements for C10302"

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Available Courses
```bash
curl http://localhost:8000/api/chatbot/courses/
```

### Chat
```bash
curl -X POST http://localhost:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "which subjects do i need to do for C04379",
    "concise": true,
    "use_preprocessing": true
  }'
```

### Chat with Course Filter
```bash
curl -X POST http://localhost:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "what are the admission requirements?",
    "course_code": "C04379",
    "course_name": "Master of Business Analytics",
    "concise": true
  }'
```

## How It Works

1. **Ingestion**: Course JSON files are split into chunks (overview, admission, career, etc.)
2. **Embedding**: Text chunks are converted to vector embeddings using Qwen3
3. **Storage**: Embeddings are stored in Qdrant with metadata (course_code, course_name, chunk_type)
4. **Query**: User questions are embedded and searched in Qdrant
5. **Retrieval**: Top relevant chunks are retrieved (optionally filtered by course_code)
6. **Generation**: Ollama LLM generates answers based on retrieved context

## Course Code Detection

The chatbot automatically extracts course codes from your questions:
- Pattern: `C` followed by 5 digits (e.g., `C04379`, `c10302`)
- Works in both current message and conversation history
- Example: "which subjects do i need to do for c04379" → automatically filters to course C04379

## Configuration

### Environment Variables

Set these in your shell or `.env` file:

```bash
export HANDBOOK_ROOT=/path/to/Handbook
export HANDBOOK_EMBED_DIR=models/hf/qwen3-embedding-0.6b
export HANDBOOK_DEFAULT_COLLECTION=courses
export HANDBOOK_K=30
export HANDBOOK_TOPN=8
export HANDBOOK_MODEL=qwen2.5:7b
```

### API Server Defaults

- **Port**: 8000
- **Collection**: `courses`
- **Embedding Model**: `qwen3-embedding-0.6b`
- **LLM Model**: `qwen2.5:7b`
- **Top K**: 30 (retrieval)
- **Top N**: 8 (display)

## Troubleshooting

### "Collection `courses` doesn't exist"
Run Step 3 of the knowledge base build process to load data into Qdrant.

### "ModuleNotFoundError"
Activate the correct conda environment:
```bash
conda activate SIG
```

### "Qdrant client version incompatible"
Use `--skip_version_check` flag when running `upsert_to_qdrant_from_files.py`.

### Course code not detected
- Ensure course codes follow the pattern: `C` + 5 digits
- Check that the course code exists in your data
- Verify the course was loaded into Qdrant

### CORS errors
- Ensure API server is running on port 8000
- Check that frontend is accessing the correct API endpoint
- Verify CORS settings in `api_server.py`

## Data Format

### Input: Course JSON Files

Each course JSON file in `data/courses/` should contain:
- `course_code`: Course code (e.g., "C04379")
- `course_name`: Course name
- `overview`: Course description
- `admission_requirements`: Admission criteria
- `career_options`: Career information
- `learning_outcomes`: Learning outcomes
- Other course metadata

### Output: Chunks

Each chunk in the database contains:
- `text`: Chunk content
- `course_code`: Course code
- `course_name`: Course name
- `chunk_type`: Type (overview, admission, career, etc.)
- `unique_id`: Unique identifier

## Development

### Adding New Course Data

1. Add JSON files to `data/courses/`
2. Re-run ingestion: `python src/rag/ingest_courses.py ...`
3. Re-generate embeddings: `python src/rag/save_kb_files.py ...`
4. Re-load into Qdrant: `python src/rag/upsert_to_qdrant_from_files.py ...`

### Modifying Query Logic

Edit files in `src/rag/`:
- `query_hybrid_rag.py`: Basic retrieval
- `filtered_retrieval.py`: Filtered retrieval
- `query_with_preprocessing.py`: Full pipeline

### Frontend Customization

Edit:
- `src/js/chatbot.js`: Chatbot logic
- `src/css/chatbot.css`: Styling
- `test_chatbot.html`: Test interface

## Testing

### Test API Endpoints
```bash
# Python script
python test_api_endpoints.py

# Bash script
./test_api.sh
```

### Test Frontend
Open `test_chatbot.html` in a browser with the API server running.

## Utilities

- `check_missing_courses.py`: Check which courses from CSV are missing JSON files
- `check_duplicates.py`: Check for duplicate IDs in JSONL files
- `check_open_ports.py`: Check if Qdrant/Ollama ports are available

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions, please [create an issue or contact maintainers].
