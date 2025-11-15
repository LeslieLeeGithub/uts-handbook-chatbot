#!/usr/bin/env python3
"""
Quick test to check Qdrant connection and collections
"""

import os
from pathlib import Path
from qdrant_client import QdrantClient

# Get project root directory (parent of src/)
SCRIPT_DIR = Path(__file__).parent.resolve()
HANDBOOK_ROOT = Path(os.environ.get('HANDBOOK_ROOT', SCRIPT_DIR.parent.parent))
DEFAULT_EMBED_DIR = HANDBOOK_ROOT / "models" / "hf" / "qwen3-embedding-0.6b"

cli = QdrantClient(host="localhost", port=6333)

# Check collections
collections = cli.get_collections()
print("Available collections:")
for col in collections.collections:
    print(f"  - {col.name}")

# Check general_kb specifically
try:
    count = cli.count("general_kb")
    print(f"\nTotal points in 'general_kb': {count.count}")
    
    if count.count > 0:
        print("\n✅ Collection has data!")
        
        # Try a simple search
        from sentence_transformers import SentenceTransformer
        enc = SentenceTransformer(str(DEFAULT_EMBED_DIR))
        qv = enc.encode(["on-site detention"], prompt_name="query", normalize_embeddings=True)[0].tolist()
        
        hits = cli.search(
            collection_name="general_kb",
            query_vector=qv,
            limit=3
        )
        print(f"Search results: {len(hits)} hits")
        if hits:
            print(f"Top score: {hits[0].score:.4f}")
            print(f"Top result preview: {hits[0].payload.get('text', '')[:100]}")
    else:
        print("\n❌ Collection exists but is empty!")
        print("You need to upsert data to general_terminology collection.")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

