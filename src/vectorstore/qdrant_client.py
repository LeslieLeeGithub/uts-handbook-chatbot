#!/usr/bin/env python3
"""
Minimal Qdrant client wrapper for upserting and searching embeddings.
"""

import os
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


def get_client() -> QdrantClient:
    url = os.getenv('QDRANT_URL', 'http://localhost:6333')
    api_key = os.getenv('QDRANT_API_KEY') or None
    return QdrantClient(url=url, api_key=api_key)


def ensure_collection(client: QdrantClient, name: str, vector_size: int):
    if name not in [c.name for c in client.get_collections().collections]:
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def upsert_documents(client: QdrantClient, collection: str, vectors: List[List[float]], payloads: List[Dict]):
    points = [
        PointStruct(id=i, vector=vectors[i], payload=payloads[i])
        for i in range(len(vectors))
    ]
    client.upsert(collection_name=collection, points=points)


def search(client: QdrantClient, collection: str, query_vector: List[float], top_k: int = 5):
    return client.search(collection_name=collection, query_vector=query_vector, limit=top_k)


