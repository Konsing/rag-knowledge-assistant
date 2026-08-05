"""
Text embedding using sentence-transformers.

Encodes text chunks into 384-dimensional vectors using all-MiniLM-L6-v2.
The model is loaded once and reused across all requests.
"""

from functools import lru_cache
from typing import Any

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

@lru_cache(maxsize=1)
def _get_model() -> Any:
    """Load the embedding model lazily and reuse it across requests."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Local embeddings are not installed; use EMBEDDING_PROVIDER=qdrant_cloud "
            "or install the local embedding dependencies"
        ) from exc
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Encode a list of text strings into embedding vectors.

    Args:
        texts: List of text chunks to embed

    Returns:
        List of 384-dimensional float vectors
    """
    if not texts:
        return []
    embeddings = _get_model().encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """
    Encode a single query string into an embedding vector.

    Uses the same model as document embedding — this is critical
    because cosine similarity only works within the same vector space.
    """
    embedding = _get_model().encode([query], show_progress_bar=False)
    return embedding[0].tolist()
