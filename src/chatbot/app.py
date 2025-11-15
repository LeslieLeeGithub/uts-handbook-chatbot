#!/usr/bin/env python3
"""
Minimal FastAPI chatbot using Qwen (Transformers) for generation and Qdrant for retrieval.
This is a scaffold; adjust model names and prompts as needed.
"""

import os
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from src.embeddings.embedder import TextEmbedder
from src.vectorstore.qdrant_client import get_client, ensure_collection, search


MODEL_NAME = os.getenv('QWEN_MODEL', 'Qwen/Qwen2-0.5B-Instruct')
COLLECTION = os.getenv('QDRANT_COLLECTION', 'handbook')


app = FastAPI(title="Handbook Chatbot")


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatResponse(BaseModel):
    answer: str
    contexts: List[str]


_tokenizer = None
_model = None
_embedder = None
_qdrant = None


def _lazy_init():
    global _tokenizer, _model, _embedder, _qdrant
    if _tokenizer is None or _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=None)
    if _embedder is None:
        _embedder = TextEmbedder()
    if _qdrant is None:
        _qdrant = get_client()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    _lazy_init()
    query_vec = _embedder.encode([req.query])[0]
    results = search(_qdrant, COLLECTION, query_vec, top_k=req.top_k)
    contexts = [hit.payload.get('text', '') for hit in results]
    context_block = "\n\n".join([f"Context {i+1}: {c}" for i, c in enumerate(contexts)])
    prompt = (
        "You are a helpful assistant. Use the context to answer the question.\n"
        f"{context_block}\n\nQuestion: {req.query}\nAnswer:"
    )
    generator = pipeline("text-generation", model=_model, tokenizer=_tokenizer, max_new_tokens=256)
    out = generator(prompt, do_sample=False)[0]['generated_text']
    answer = out.split("Answer:")[-1].strip()
    return ChatResponse(answer=answer, contexts=contexts)


