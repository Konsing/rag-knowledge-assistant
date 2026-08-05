"""Shared orchestration for the API and MCP entry points."""

import asyncio

from app.embedding.embedder import embed_query, embed_texts
from app.generation.llm_client import generate_answer
from app.retrieval.search import search, upsert_chunks


async def store_chunks(chunks: list[dict]) -> int:
    """Embed and idempotently store chunks without blocking the event loop."""
    texts = [chunk["text"] for chunk in chunks]
    vectors = await asyncio.to_thread(embed_texts, texts)
    return await asyncio.to_thread(upsert_chunks, chunks, vectors)


async def retrieve(question: str, top_k: int, doc_ids: list[str] | None = None) -> list[dict]:
    query_vector = await asyncio.to_thread(embed_query, question)
    return await asyncio.to_thread(search, query_vector, top_k, doc_ids)


async def answer(question: str, top_k: int, doc_ids: list[str] | None = None) -> tuple[str, list[dict]]:
    results = await retrieve(question, top_k, doc_ids)
    if not results:
        return "", []
    generated = await asyncio.to_thread(generate_answer, question, results)
    return generated, results
