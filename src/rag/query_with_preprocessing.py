#!/usr/bin/env python3
"""
Complete RAG pipeline for UTS Handbook courses
Simplified version without complex preprocessing
"""
import argparse
import os
from pathlib import Path
from typing import List, Dict
from filtered_retrieval import query_with_filtering, check_result_quality
from query_hybrid_rag import build_course_context, answer_with_ollama

# Get project root directory
SCRIPT_DIR = Path(__file__).parent.resolve()
HANDBOOK_ROOT = Path(os.environ.get('HANDBOOK_ROOT', SCRIPT_DIR.parent.parent))
DEFAULT_EMBED_DIR = HANDBOOK_ROOT / "models" / "hf" / "qwen3-embedding-0.6b"


def query_with_full_pipeline(
    query: str,
    embed_dir: str,
    collection: str = "courses",
    course_code: str = None,
    course_name: str = None,
    generate: bool = True,
    topn: int = 8,
    model: str = "qwen2.5:7b",
    concise: bool = True,
    host="localhost",
    port=6333,
    ollama_host="127.0.0.1",
    ollama_port=11434
):
    """
    Complete RAG pipeline for course information retrieval and generation.
    """
    
    print("=" * 70)
    print("UTS HANDBOOK RAG PIPELINE")
    print("=" * 70)
    
    # Step 1: Retrieve with filtering
    print(f"\n[1/3] Retrieving course documents...")
    
    hits = query_with_filtering(
        query=query,
        embed_dir=embed_dir,
        collection=collection,
        course_code=course_code,
        course_name=course_name,
        show_details=False,  # We'll show details ourselves
        topn=topn,
        host=host,
        port=port
    )
    
    # Step 2: Quality checks
    print(f"\n[2/3] Quality checks...")
    quality = check_result_quality(hits, query)
    
    if not quality['has_results']:
        print("❌ No results found.")
        return "No relevant course information found."
    
    print(f"  Results: {len(hits)}")
    if quality['has_high_quality']:
        print("  Quality: ✅ Good")
    if quality['diverse_sources']:
        print("  Diversity: ✅ Multiple courses found")
    
    # Display results
    print(f"\n[3/3] Top results ({min(topn, len(hits))}):")
    for i, hit in enumerate(hits[:topn], 1):
        payload = hit.payload or {}
        text = payload.get("text", "")[:150] + "..." if len(payload.get("text", "")) > 150 else payload.get("text", "")
        course_code = payload.get("course_code", "Unknown")
        course_name = payload.get("course_name", "Unknown")
        chunk_label = payload.get("chunk_label", "Unknown")
        
        print(f"  {i}. Score {hit.score:.3f} | {course_code} - {chunk_label}")
        print(f"     {text[:80]}...")
    
    # Step 3: Generate response (if requested)
    if generate:
        print(f"\n[4/4] Generating response...")
        context = build_course_context(hits, max_context_length=4000)
        
        response = answer_with_ollama(
            query=query,
            context=context,
            host=ollama_host,
            port=ollama_port,
            model=model,
            concise=concise
        )
        
        print(f"\n{'='*70}")
        print("GENERATED RESPONSE")
        print(f"{'='*70}")
        print(response)
        
        return response
    
    return "Search completed (no generation requested)"


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description='Complete RAG pipeline for UTS courses')
    parser.add_argument('--q', required=True, help='Query string')
    parser.add_argument('--course_code', default=None, help='Filter by course code (e.g., C10302)')
    parser.add_argument('--course_name', default=None, help='Filter by course name (partial match)')
    parser.add_argument('--collection', default='courses', help='Qdrant collection name')
    parser.add_argument('--embed_dir', default=str(DEFAULT_EMBED_DIR), 
                       help='Embedding model directory')
    parser.add_argument('--topn', type=int, default=8, help='Number of top results to show')
    parser.add_argument('--generate', action='store_true', help='Generate response using Ollama')
    parser.add_argument('--model', default='qwen2.5:7b', help='Ollama model')
    parser.add_argument('--concise', action='store_true', default=True, help='Generate concise answers (default: True)')
    parser.add_argument('--comprehensive', action='store_true', help='Generate comprehensive answers')
    parser.add_argument('--qdrant_host', default='localhost')
    parser.add_argument('--qdrant_port', type=int, default=6333)
    parser.add_argument('--ollama_host', default='127.0.0.1')
    parser.add_argument('--ollama_port', type=int, default=11434)
    
    args = parser.parse_args()
    
    # Determine concise mode
    concise = args.concise and not args.comprehensive
    
    try:
        response = query_with_full_pipeline(
            query=args.q,
            embed_dir=args.embed_dir,
            collection=args.collection,
            course_code=args.course_code,
            course_name=args.course_name,
            generate=args.generate,
            topn=args.topn,
            model=args.model,
            concise=concise,
            host=args.qdrant_host,
            port=args.qdrant_port,
            ollama_host=args.ollama_host,
            ollama_port=args.ollama_port
        )
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
