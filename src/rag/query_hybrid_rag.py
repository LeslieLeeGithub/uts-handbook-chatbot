#!/usr/bin/env python3
"""
Course RAG query script for UTS Handbook chatbot
Simplified version for course information retrieval
"""
import argparse
import json
import os
from pathlib import Path
import requests
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer

# Get project root directory
SCRIPT_DIR = Path(__file__).parent.resolve()
HANDBOOK_ROOT = Path(os.environ.get('HANDBOOK_ROOT', SCRIPT_DIR.parent.parent))
DEFAULT_EMBED_DIR = HANDBOOK_ROOT / "models" / "hf" / "qwen3-embedding-0.6b"

# ---------- Course retrieval function ----------

def retrieve_courses(q: str, embed_dir: str, collection: str = "courses",
                     course_code: str = None, course_name: str = None,
                     host="localhost", port=6333, limit=30):
    """Retrieve course information from Qdrant"""
    
    # Initialize embedding model
    enc = SentenceTransformer(embed_dir)
    qv = enc.encode([q], prompt_name="query", normalize_embeddings=True)[0].tolist()
    
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
    
    return hits

# ---------- Context building ----------

def build_course_context(hits: List[Dict], max_context_length: int = 4000) -> str:
    """Build context from course search results"""
    
    context_parts = []
    current_length = 0
    
    for hit in hits:
        payload = hit.payload or {}
        text = payload.get("text", "")
        
        if current_length + len(text) < max_context_length:
            # Add course information
            course_code = payload.get("course_code", "")
            course_name = payload.get("course_name", "")
            chunk_label = payload.get("chunk_label", "")
            source_url = payload.get("source_url", "")
            
            cite_parts = []
            if course_code:
                cite_parts.append(f"Course Code: {course_code}")
            if course_name:
                cite_parts.append(f"({course_name})")
            if chunk_label:
                cite_parts.append(f"- {chunk_label}")
            
            cite = " | ".join(cite_parts)
            if source_url:
                cite += f"\nSource: {source_url}"
            
            context_parts.append(f"[{cite}]\n{text}")
            current_length += len(text)
    
    return "\n\n".join(context_parts)

# ---------- Response generation ----------

def answer_with_ollama(query: str, context: str,
                       host="127.0.0.1", port=11434, 
                       model="qwen2.5:7b", concise: bool = True) -> str:
    """Generate answer using Ollama"""
    
    url = f"http://{host}:{port}/api/chat"
    
    if concise:
        system_msg = "You are a helpful assistant for UTS course information. Answer questions about courses using only the provided context. Be brief and direct. Cite sources as [Course Code: XXX]. If the information is not in the context, say you don't know."
        prompt = f"Question: {query}\n\nContext:\n{context}\n\nAnswer directly and briefly:"
    else:
        system_msg = "You are a helpful assistant for UTS course information. Answer questions about courses using only the provided context. Provide comprehensive answers. Cite sources as [Course Code: XXX]. If the information is not in the context, say you don't know."
        prompt = f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"
    
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        r = requests.post(url, json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]
    except Exception as e:
        return f"Error generating response: {e}"

# ---------- Main query function ----------

def query_courses(query: str, embed_dir: str, collection: str = "courses",
                 course_code: str = None, course_name: str = None,
                 k: int = 30, topn: int = 8, generate: bool = True, 
                 concise: bool = True, host="localhost", port=6333,
                 ollama_host="127.0.0.1", ollama_port=11434, 
                 ollama_model="qwen2.5:7b"):
    """Main course RAG query function"""
    
    print(f"Query: {query}")
    if course_code:
        print(f"Filtering by course code: {course_code}")
    if course_name:
        print(f"Filtering by course name: {course_name}")
    
    # Retrieve documents
    hits = retrieve_courses(
        query, embed_dir, collection,
        course_code=course_code,
        course_name=course_name,
        host=host, port=port, limit=k
    )
    
    if not hits:
        return "No relevant course information found."
    
    print(f"\n=== Top {topn} Results ===")
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
    
    if not generate:
        return "Search completed (no generation requested)"
    
    # Build context and generate response
    print(f"\n=== Generated Response ===")
    context = build_course_context(hits, max_context_length=4000)
    response = answer_with_ollama(
        query, 
        context,
        host=ollama_host,
        port=ollama_port,
        model=ollama_model,
        concise=concise
    )
    
    return response

# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description='UTS Course RAG query system')
    parser.add_argument('--q', required=True, help='Query string')
    parser.add_argument('--course_code', default=None, help='Filter by course code (e.g., C10302)')
    parser.add_argument('--course_name', default=None, help='Filter by course name (partial match)')
    parser.add_argument('--collection', default='courses', help='Qdrant collection name')
    parser.add_argument('--embed_dir', default=str(DEFAULT_EMBED_DIR), 
                       help='Embedding model directory')
    parser.add_argument('--k', type=int, default=30, help='Number of documents to retrieve')
    parser.add_argument('--topn', type=int, default=8, help='Number of top documents to show')
    parser.add_argument('--generate', action='store_true', help='Generate response using Ollama')
    parser.add_argument('--concise', action='store_true', default=True, help='Generate concise answers')
    parser.add_argument('--comprehensive', action='store_true', help='Generate comprehensive answers')
    parser.add_argument('--qdrant_host', default='localhost')
    parser.add_argument('--qdrant_port', type=int, default=6333)
    parser.add_argument('--ollama_host', default='127.0.0.1')
    parser.add_argument('--ollama_port', type=int, default=11434)
    parser.add_argument('--ollama_model', default='qwen2.5:7b')
    
    args = parser.parse_args()
    
    # Determine concise mode
    concise = args.concise and not args.comprehensive
    
    try:
        response = query_courses(
            query=args.q,
            embed_dir=args.embed_dir,
            collection=args.collection,
            course_code=args.course_code,
            course_name=args.course_name,
            k=args.k,
            topn=args.topn,
            generate=args.generate,
            concise=concise,
            host=args.qdrant_host,
            port=args.qdrant_port,
            ollama_host=args.ollama_host,
            ollama_port=args.ollama_port,
            ollama_model=args.ollama_model
        )
        print(response)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
