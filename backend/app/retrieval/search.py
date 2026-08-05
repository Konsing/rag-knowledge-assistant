"""
Vector storage and retrieval using Qdrant.

Handles collection management, upserting embedded chunks,
and cosine similarity search for query-time retrieval.
"""

import uuid
import warnings

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.embedding.embedder import EMBEDDING_DIM

# Suppress minor version mismatch warnings (API is backward-compatible)
warnings.filterwarnings("ignore", message="Qdrant client version")

# Initialize Qdrant client — connects to the Qdrant container via Docker networking
_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection() -> None:
    """
    Create the vector collection if it doesn't exist.

    Uses cosine distance because we care about directional similarity
    between text embeddings, not their magnitude.
    """
    if not _client.collection_exists(settings.collection_name):
        try:
            _client.create_collection(
                collection_name=settings.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
        except Exception:
            # The API and MCP services may race to create the collection.
            if not _client.collection_exists(settings.collection_name):
                raise


def upsert_chunks(chunks: list[dict], vectors: list[list[float]]) -> int:
    """
    Store embedded chunks in Qdrant.

    Each point gets a UUID, the embedding vector, and the full chunk
    metadata as payload (source_file, page_number, section_title, etc.)
    plus the original text for retrieval.

    Args:
        chunks: List of {text, metadata} dicts from the chunker
        vectors: Corresponding embedding vectors from the embedder

    Returns:
        Number of points upserted
    """
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must have the same length")
    ensure_collection()

    points = []
    for chunk, vector in zip(chunks, vectors):
        metadata = chunk["metadata"]
        point_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"rag:{metadata['doc_id']}:{metadata['chunk_index']}",
        ))
        payload = {
            "text": chunk["text"],
            **chunk["metadata"],
        }
        points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    # Upsert in batches of 100 to avoid oversized requests
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        _client.upsert(
            collection_name=settings.collection_name,
            points=batch,
            wait=True,
        )

    return len(points)


def search(
    query_vector: list[float],
    top_k: int | None = None,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """
    Search for the most similar chunks to a query vector.

    Args:
        query_vector: 384-dim embedding of the user's question
        top_k: Number of results to return (default from config)

    Returns:
        List of dicts with keys: text, metadata, score
    """
    top_k = settings.top_k if top_k is None else top_k
    if not 1 <= top_k <= 10:
        raise ValueError("top_k must be between 1 and 10")
    ensure_collection()

    query_filter = None
    if doc_ids:
        query_filter = Filter(must=[
            FieldCondition(key="doc_id", match=MatchAny(any=doc_ids)),
        ])

    results = _client.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        limit=top_k,
        score_threshold=settings.score_threshold,
        with_payload=True,
        query_filter=query_filter,
    )

    hits = []
    for point in results.points:
        payload = dict(point.payload or {})
        hits.append({
            "text": payload.get("text", ""),
            "metadata": {
                "source_file": payload.get("source_file", ""),
                "page_number": payload.get("page_number", 0),
                "section_title": payload.get("section_title", ""),
                "chunk_index": payload.get("chunk_index", 0),
                "doc_id": payload.get("doc_id", ""),
            },
            "score": point.score,
        })

    return hits


def get_collection_info() -> dict:
    """Get stats about the current collection (point count, etc.)."""
    ensure_collection()
    info = _client.get_collection(settings.collection_name)
    return {
        "name": settings.collection_name,
        "points_count": info.points_count,
    }
