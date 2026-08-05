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
