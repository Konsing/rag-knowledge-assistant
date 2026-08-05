import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.demo import DemoGuard
from app import demo as demo_module
from main import app


client = TestClient(app)


def test_demo_ingestion_requires_server_side_admin_key(monkeypatch):
    monkeypatch.setattr(routes.settings, "demo_mode", True)
    monkeypatch.setattr(routes.settings, "admin_api_key", "admin-secret")
    monkeypatch.setattr(routes.settings, "app_api_key", "")

    assert client.post("/api/ingest").status_code == 401
    response = client.post("/api/ingest", headers={"X-Admin-Key": "admin-secret"})
    assert response.status_code == 400


def test_document_catalog_is_public_in_demo_mode(monkeypatch):
    monkeypatch.setattr(routes.settings, "demo_mode", True)
    monkeypatch.setattr(routes, "list_documents", lambda: [{
        "doc_id": "doc-1",
        "title": "Demo paper",
        "source_file": "paper.pdf",
        "source_url": "https://arxiv.org/abs/1234.5678",
        "description": "A curated paper",
        "chunk_count": 2,
        "page_count": 1,
        "sections": ["Introduction"],
        "sample_questions": ["What is new?"],
    }])

    response = client.get("/api/documents")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Demo paper"


def test_demo_query_is_document_scoped_and_reports_trace_metadata(monkeypatch):
    monkeypatch.setattr(routes.settings, "demo_mode", True)
    monkeypatch.setattr(routes.settings, "demo_max_question_chars", 500)
    monkeypatch.setattr(routes.settings, "demo_max_selected_documents", 5)
    monkeypatch.setattr(routes.settings, "hcaptcha_secret", "")
    monkeypatch.setattr(routes.demo_guard, "verify_request", AsyncMock())
    monkeypatch.setattr(routes.demo_guard, "get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr(routes.demo_guard, "reserve_generation", AsyncMock())
    monkeypatch.setattr(routes.demo_guard, "put_cached", AsyncMock())

    async def fake_answer(question, top_k, doc_ids):
        assert question == "How does attention work?"
        assert top_k == 3
        assert doc_ids == ["doc-1"]
        return "From the selected paper [1].", [{
            "text": "Attention maps queries to key-value pairs.",
            "metadata": {
                "source_file": "paper.pdf",
                "page_number": 3,
                "section_title": "Attention",
                "chunk_index": 2,
                "doc_id": "doc-1",
                "title": "Demo paper",
                "source_url": "https://arxiv.org/abs/1234.5678",
            },
            "score": 0.82,
        }]

    monkeypatch.setattr(routes, "answer", fake_answer)
    response = client.post("/api/query", json={
        "question": "How does attention work?",
        "top_k": 3,
        "doc_ids": ["doc-1"],
    })

    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["metadata"]["title"] == "Demo paper"
    assert body["model"]
    assert body["cached"] is False


def test_hourly_demo_limit(monkeypatch):
    monkeypatch.setattr(routes.settings, "hcaptcha_secret", "")
    monkeypatch.setattr(routes.settings, "demo_queries_per_hour", 1)
    guard = DemoGuard()

    asyncio.run(guard.verify_request("203.0.113.10", ""))
    with pytest.raises(Exception) as error:
        asyncio.run(guard.verify_request("203.0.113.10", ""))
    assert getattr(error.value, "status_code", None) == 429


def test_hcaptcha_verification_is_bound_to_configured_site_key(monkeypatch):
    submitted = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"success": True}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, data):
            submitted.update({"url": url, "data": data})
            return FakeResponse()

    monkeypatch.setattr(demo_module.settings, "hcaptcha_secret", "captcha-secret")
    monkeypatch.setattr(demo_module.settings, "hcaptcha_site_key", "captcha-site")
    monkeypatch.setattr(demo_module.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    asyncio.run(DemoGuard().verify_request("203.0.113.11", "captcha-token"))

    assert submitted["url"] == demo_module.HCAPTCHA_VERIFY_URL
    assert submitted["data"] == {
        "secret": "captcha-secret",
        "response": "captcha-token",
        "remoteip": "203.0.113.11",
        "sitekey": "captcha-site",
    }
