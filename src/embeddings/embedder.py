#!/usr/bin/env python3
"""
Simple embedding helper using sentence-transformers.
"""

from typing import List

from sentence_transformers import SentenceTransformer


class TextEmbedder:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> List[list]:
        embeddings = self.model.encode(texts, convert_to_numpy=False, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]


