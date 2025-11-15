#!/usr/bin/env python3
"""
Filtered retrieval script for UTS Handbook courses
Simplified version for course information retrieval
"""
import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer

# Get project root directory
SCRIPT_DIR = Path(__file__).parent.resolve()
HANDBOOK_ROOT = Path(os.environ.get('HANDBOOK_ROOT', SCRIPT_DIR.parent.parent))
DEFAULT_EMBED_DIR = HANDBOOK_ROOT / "models" / "hf" / "qwen3-embedding-0.6b"

# ---------- Course Retrieval ----------

def retrieve_courses(
    query: str,
    embed_dir: str,
    collection: str = "courses",
    course_code: str = None,
    course_name: str = None,
    host="localhost",
    port=6333,
    limit=30
):
    """Retrieve course documents with optional filtering"""
    
    # Initialize embedding model
    enc = SentenceTransformer(embed_dir)
    qv = enc.encode([query], prompt_name="query", normalize_embeddings=True)[0].tolist()
    
    # Initialize Qdrant client
    cli = QdrantClient(host=host, port=port)
    
    # Build filter if course_code or course_name is specified
    flt = None
    conditions = []
    
    if course_code:
        conditions.append(
            qm.FieldCondition(
                key="course_code",
                match=qm.MatchValue(value=course_code.upper())
            )
        )
    
    if course_name:
        # Use MatchText for partial matching on course name
        conditions.append(
            qm.FieldCondition(
                key="course_name",
                match=qm.MatchText(text=course_name)
            )
        )
    
    if conditions:
        flt = qm.Filter(must=conditions)
    
    hits = cli.search(
        collection_name=collection,
        query_vector=qv,
        query_filter=flt,
        limit=limit,
        with_payload=True
    )
    
    # Sort by score
    hits.sort(key=lambda x: x.score, reverse=True)
    return hits

# ---------- Quality Checks ----------

def check_result_quality(hits: List, query: str) -> Dict[str, Any]:
    """Perform quality checks on results"""
    
    checks = {
        'has_results': len(hits) > 0,
        'min_results': len(hits) >= 3,
        'has_high_quality': False,
        'diverse_sources': False
    }
    
    if hits:
        # Check if top result has reasonable score (> 0.3)
        checks['has_high_quality'] = hits[0].score > 0.3
        
        # Check if results are diverse (not all from same course)
        if len(hits) >= 2:
            sources = set(hit.payload.get('course_code', 'unknown') for hit in hits[:3])
            checks['diverse_sources'] = len(sources) > 1
    
    return checks

# ---------- Main Filtered Retrieval Function ----------

def query_with_filtering(
    query: str,
    embed_dir: str,
    collection: str = "courses",
    course_code: str = None,
    course_name: str = None,
    show_details: bool = True,
    topn: int = 8,
    host="localhost",
    port=6333
):
    """Main function for filtered retrieval pipeline"""
    
    if show_details:
        print("=" * 60)
        print("COURSE RETRIEVAL PIPELINE")
        print("=" * 60)
        print(f"\nQuery: {query}")
        if course_code:
            print(f"Filtering by course code: {course_code}")
        if course_name:
            print(f"Filtering by course name: {course_name}")
    
    # Retrieve documents
    if show_details:
        print(f"\n[Step 1] Retrieving course documents...")
    
    hits = retrieve_courses(
        query=query,
        embed_dir=embed_dir,
        collection=collection,
        course_code=course_code,
        course_name=course_name,
        host=host,
        port=port,
        limit=30
    )
    
    # Quality checks
    if show_details:
        print(f"\n[Step 2] Quality checks...")
    
    quality = check_result_quality(hits, query)
    
    if not quality['has_results']:
        if show_details:
            print("❌ No results found.")
        return []
    
    if not quality['min_results']:
        if show_details:
            print(f"⚠️  Only {len(hits)} result(s) found.")
    
    if quality['has_high_quality']:
        if show_details:
            print("✅ Results pass quality checks.")
    
    # Display results
    if show_details:
        print(f"\n=== Top {min(topn, len(hits))} Results ===")
        for i, hit in enumerate(hits[:topn], 1):
            payload = hit.payload or {}
            text = payload.get("text", "")[:200] + "..." if len(payload.get("text", "")) > 200 else payload.get("text", "")
            course_code = payload.get("course_code", "Unknown")
            course_name = payload.get("course_name", "Unknown")
            chunk_label = payload.get("chunk_label", "Unknown")
            
            print(f"\n{i}. Score: {hit.score:.4f}")
            print(f"   Course: {course_code} - {course_name}")
            print(f"   Section: {chunk_label}")
            print(f"   Text: {text}")
    
    return hits

# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description='Filtered retrieval for UTS courses')
    parser.add_argument('--q', required=True, help='Query string')
    parser.add_argument('--course_code', default=None, help='Filter by course code (e.g., C10302)')
    parser.add_argument('--course_name', default=None, help='Filter by course name (partial match)')
    parser.add_argument('--collection', default='courses', help='Qdrant collection name')
    parser.add_argument('--embed_dir', default=str(DEFAULT_EMBED_DIR), 
                       help='Embedding model directory')
    parser.add_argument('--topn', type=int, default=8, help='Number of top results to show')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode (minimal output)')
    parser.add_argument('--qdrant_host', default='localhost')
    parser.add_argument('--qdrant_port', type=int, default=6333)
    
    args = parser.parse_args()
    
    try:
        hits = query_with_filtering(
            query=args.q,
            embed_dir=args.embed_dir,
            collection=args.collection,
            course_code=args.course_code,
            course_name=args.course_name,
            show_details=not args.quiet,
            topn=args.topn,
            host=args.qdrant_host,
            port=args.qdrant_port
        )
        
        if args.quiet:
            # Just return JSON for pipeline integration
            result_data = {
                'query': args.q,
                'results_count': len(hits),
                'top_score': hits[0].score if hits else 0,
                'results': [
                    {
                        'score': hit.score,
                        'course_code': hit.payload.get('course_code'),
                        'course_name': hit.payload.get('course_name'),
                        'chunk_label': hit.payload.get('chunk_label'),
                        'text_preview': hit.payload.get('text', '')[:200]
                    }
                    for hit in hits[:args.topn]
                ]
            }
            print(json.dumps(result_data, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
