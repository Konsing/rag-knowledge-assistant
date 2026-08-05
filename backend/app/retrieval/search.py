"""Qdrant vector storage, retrieval, and public document-catalog helpers."""

import uuid
import warnings
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Document,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.embedding.embedder import EMBEDDING_DIM

warnings.filterwarnings("ignore", message="Qdrant client version")


def _build_client() -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            cloud_inference=settings.qdrant_cloud_inference,
            timeout=30,
        )
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


_client = _build_client()
_DEMO_USAGE_POINT_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "rag:demo:daily-usage"))


def ensure_collection() -> None:
    """Create the collection and document filter index when missing."""
    if not _client.collection_exists(settings.collection_name):
        try:
            _client.create_collection(
                collection_name=settings.collection_name,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
        except Exception:
            if not _client.collection_exists(settings.collection_name):
                raise

    info = _client.get_collection(settings.collection_name)
    if "doc_id" not in (info.payload_schema or {}):
        try:
            _client.create_payload_index(
                collection_name=settings.collection_name,
                field_name="doc_id",
                field_schema=PayloadSchemaType.KEYWORD,
                wait=True,
            )
        except Exception:
            # API and MCP processes can race to create the same index.
            info = _client.get_collection(settings.collection_name)
            if "doc_id" not in (info.payload_schema or {}):
                raise


def upsert_chunks(
    chunks: list[dict],
    vectors: list[list[float]] | None = None,
) -> int:
    """Store chunks with deterministic vector IDs and complete display metadata."""
    if settings.embedding_provider == "local":
        if vectors is None or len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
    elif vectors is not None:
        raise ValueError("vectors must be omitted when Qdrant Cloud inference is enabled")

    ensure_collection()
    points = []
    for index, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        point_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"rag:{metadata['doc_id']}:{metadata['chunk_index']}",
        ))
        vector = (
            vectors[index]
            if vectors is not None
            else Document(text=chunk["text"], model=settings.embedding_model)
        )
        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload={"text": chunk["text"], **metadata},
        ))

    for start in range(0, len(points), 100):
        _client.upsert(
            collection_name=settings.collection_name,
            points=points[start:start + 100],
            wait=True,
        )
    return len(points)


def search(
    query: list[float] | str,
    top_k: int | None = None,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """Search globally or within selected documents."""
    top_k = settings.top_k if top_k is None else top_k
    if not 1 <= top_k <= 10:
        raise ValueError("top_k must be between 1 and 10")
    ensure_collection()

    query_filter = None
    if doc_ids:
        query_filter = Filter(must=[
            FieldCondition(key="doc_id", match=MatchAny(any=doc_ids)),
        ])
    query_input = (
        Document(text=query, model=settings.embedding_model)
        if isinstance(query, str)
        else query
    )
    results = _client.query_points(
        collection_name=settings.collection_name,
        query=query_input,
        limit=top_k,
        score_threshold=settings.score_threshold,
        with_payload=True,
        query_filter=query_filter,
    )
    return [_point_to_result(point.payload or {}, point.score) for point in results.points]


def _metadata(payload: dict) -> dict:
    return {
        "source_file": payload.get("source_file", ""),
        "page_number": payload.get("page_number", 0),
        "section_title": payload.get("section_title", ""),
        "chunk_index": payload.get("chunk_index", 0),
        "doc_id": payload.get("doc_id", ""),
        "title": payload.get("title", ""),
        "source_url": payload.get("source_url", ""),
    }


def _point_to_result(payload: dict, score: float) -> dict:
    return {
        "text": payload.get("text", ""),
        "metadata": _metadata(payload),
        "score": score,
    }


def _all_payloads(max_points: int = 10_000) -> list[dict]:
    ensure_collection()
    payloads: list[dict] = []
    offset = None
    while len(payloads) < max_points:
        records, offset = _client.scroll(
            collection_name=settings.collection_name,
            limit=min(256, max_points - len(payloads)),
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        payloads.extend(dict(record.payload or {}) for record in records)
        if offset is None:
            break
    return payloads


def list_documents() -> list[dict]:
    """Return one safe catalog entry per indexed document."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for payload in _all_payloads():
        if payload.get("doc_id"):
            grouped[str(payload["doc_id"])].append(payload)

    documents = []
    for doc_id, chunks in grouped.items():
        first = chunks[0]
        source_file = str(first.get("source_file", ""))
        sections = sorted({
            str(chunk.get("section_title", ""))
            for chunk in chunks
            if chunk.get("section_title")
        })
        pages = {int(chunk.get("page_number", 0)) for chunk in chunks}
        documents.append({
            "doc_id": doc_id,
            "title": str(first.get("title") or source_file or "Untitled document"),
            "source_file": source_file,
            "source_url": str(first.get("source_url", "")),
            "description": str(first.get("description", "")),
            "chunk_count": len(chunks),
            "page_count": len({page for page in pages if page > 0}),
            "sections": sections[:20],
            "sample_questions": list(first.get("sample_questions") or [])[:5],
        })
    return sorted(documents, key=lambda item: item["title"].lower())


def get_document(doc_id: str, chunk_limit: int = 100) -> dict | None:
    """Return catalog metadata and ordered chunk previews for one document."""
    ensure_collection()
    records, _ = _client.scroll(
        collection_name=settings.collection_name,
        scroll_filter=Filter(must=[
            FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
        ]),
        limit=chunk_limit,
        with_payload=True,
        with_vectors=False,
    )
    if not records:
        return None
    payloads = sorted(
        (dict(record.payload or {}) for record in records),
        key=lambda item: int(item.get("chunk_index", 0)),
    )
    summary = next(
        (item for item in list_documents() if item["doc_id"] == doc_id),
        None,
    )
    if summary is None:
        return None
    return {
        **summary,
        "chunks": [
            {"text": payload.get("text", ""), "metadata": _metadata(payload)}
            for payload in payloads
        ],
    }


def get_collection_info() -> dict:
    ensure_collection()
    info = _client.get_collection(settings.collection_name)
    usage = _client.retrieve(
        collection_name=settings.collection_name,
        ids=[_DEMO_USAGE_POINT_ID],
        with_payload=False,
        with_vectors=False,
    )
    points_count = int(info.points_count or 0) - (1 if usage else 0)
    return {"name": settings.collection_name, "points_count": max(0, points_count)}


def reserve_demo_generation(day: str, maximum: int) -> bool:
    """Persist a tiny daily usage counter in Qdrant across free-host restarts."""
    ensure_collection()
    records = _client.retrieve(
        collection_name=settings.collection_name,
        ids=[_DEMO_USAGE_POINT_ID],
        with_payload=True,
        with_vectors=False,
    )
    payload = dict(records[0].payload or {}) if records else {}
    count = int(payload.get("count", 0)) if payload.get("date") == day else 0
    if count >= maximum:
        return False
    _client.upsert(
        collection_name=settings.collection_name,
        points=[PointStruct(
            id=_DEMO_USAGE_POINT_ID,
            vector=[0.0] * EMBEDDING_DIM,
            payload={"_kind": "demo_usage", "date": day, "count": count + 1},
        )],
        wait=True,
    )
    return True
