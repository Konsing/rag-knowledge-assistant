import asyncio

from app import service


def test_retrieve_passes_document_filter(monkeypatch):
    monkeypatch.setattr(service, "embed_query", lambda question: [len(question)])

    def fake_search(vector, top_k, doc_ids):
        assert vector == [8]
        assert top_k == 3
        assert doc_ids == ["doc-a"]
        return [{"ok": True}]

    monkeypatch.setattr(service, "search", fake_search)
    result = asyncio.run(service.retrieve("question", 3, ["doc-a"]))

    assert result == [{"ok": True}]


def test_cloud_retrieve_passes_raw_text_to_qdrant(monkeypatch):
    monkeypatch.setattr(service.settings, "embedding_provider", "qdrant_cloud")

    def fake_search(query, top_k, doc_ids):
        assert query == "question"
        assert top_k == 2
        assert doc_ids == ["doc-a"]
        return [{"ok": True}]

    monkeypatch.setattr(service, "search", fake_search)
    result = asyncio.run(service.retrieve("question", 2, ["doc-a"]))

    assert result == [{"ok": True}]
