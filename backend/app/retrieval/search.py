"""
Vector storage and retrieval using Qdrant.

Handles collection management, upserting embedded chunks,
and cosine similarity search for query-time retrieval.
"""

import uuid
import warnings

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

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
    collections = [c.name for c in _client.get_collections().collections]
    if settings.collection_name not in collections:
        _client.create_collection(
            collection_name=settings.collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


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
    ensure_collection()

    points = []
    for chunk, vector in zip(chunks, vectors):
        point_id = str(uuid.uuid4())
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


def search(query_vector: list[float], top_k: int | None = None) -> list[dict]:
    """
    Search for the most similar chunks to a query vector.

    Args:
        query_vector: 384-dim embedding of the user's question
        top_k: Number of results to return (default from config)

    Returns:
        List of dicts with keys: text, metadata, score
    """
    top_k = top_k or settings.top_k
    ensure_collection()

    results = _client.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        limit=top_k,
        score_threshold=settings.score_threshold,
        with_payload=True,
    )

    hits = []
    for point in results.points:
        payload = point.payload
        hits.append({
            "text": payload.pop("text"),
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
