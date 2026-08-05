import uuid
from types import SimpleNamespace

import pytest

from app.retrieval import search as module


def _chunk():
    return {
        "text": "content",
        "metadata": {
            "source_file": "notes.txt",
            "page_number": 1,
            "section_title": "Full Document",
            "chunk_index": 0,
            "doc_id": "stable-doc",
        },
    }


def test_upsert_uses_deterministic_ids(monkeypatch):
    captured = []
    monkeypatch.setattr(module, "ensure_collection", lambda: None)
    monkeypatch.setattr(
        module,
        "_client",
        SimpleNamespace(upsert=lambda **kwargs: captured.extend(kwargs["points"])),
    )

    module.upsert_chunks([_chunk()], [[0.0] * 384])
    first_id = captured[0].id
    captured.clear()
    module.upsert_chunks([_chunk()], [[0.0] * 384])

    assert captured[0].id == first_id
    uuid.UUID(str(first_id))


def test_upsert_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        module.upsert_chunks([_chunk()], [])


def test_cloud_upsert_uses_qdrant_document_inference(monkeypatch):
    captured = []
    monkeypatch.setattr(module.settings, "embedding_provider", "qdrant_cloud")
    monkeypatch.setattr(module, "ensure_collection", lambda: None)
    monkeypatch.setattr(
        module,
        "_client",
        SimpleNamespace(upsert=lambda **kwargs: captured.extend(kwargs["points"])),
    )

    module.upsert_chunks([_chunk()])
    assert captured[0].vector.text == "content"
    assert captured[0].vector.model == module.settings.embedding_model


def test_document_catalog_groups_chunks_without_vectors(monkeypatch):
    monkeypatch.setattr(module, "ensure_collection", lambda: None)
    records = [
        SimpleNamespace(payload={
            "text": "first",
            "doc_id": "doc-1",
            "title": "Demo paper",
            "source_file": "paper.pdf",
            "source_url": "https://example.com/paper",
            "description": "Description",
            "sample_questions": ["What changed?"],
            "page_number": 1,
            "section_title": "Intro",
            "chunk_index": 0,
        }),
        SimpleNamespace(payload={
            "text": "second",
            "doc_id": "doc-1",
            "title": "Demo paper",
            "source_file": "paper.pdf",
            "page_number": 2,
            "section_title": "Method",
            "chunk_index": 1,
        }),
    ]
    monkeypatch.setattr(
        module,
        "_client",
        SimpleNamespace(scroll=lambda **kwargs: (records, None)),
    )

    catalog = module.list_documents()
    assert catalog[0]["chunk_count"] == 2
    assert catalog[0]["page_count"] == 2
    assert catalog[0]["sections"] == ["Intro", "Method"]


def test_daily_generation_counter_is_persisted(monkeypatch):
    captured = []
    monkeypatch.setattr(module, "ensure_collection", lambda: None)
    monkeypatch.setattr(
        module,
        "_client",
        SimpleNamespace(
            retrieve=lambda **kwargs: [],
            upsert=lambda **kwargs: captured.extend(kwargs["points"]),
        ),
    )

    assert module.reserve_demo_generation("2026-08-05", 2) is True
    assert captured[0].payload["count"] == 1
