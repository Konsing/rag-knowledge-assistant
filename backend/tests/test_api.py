from fastapi.testclient import TestClient

from app.api import routes
from main import app


client = TestClient(app)


def test_query_validation_rejects_blank_question():
    response = client.post("/api/query", json={"question": "   "})
    assert response.status_code == 422


def test_ingest_requires_exactly_one_source():
    response = client.post("/api/ingest")
    assert response.status_code == 400


def test_health_checks_qdrant(monkeypatch):
    monkeypatch.setattr(
        routes,
        "get_collection_info",
        lambda: {"name": "test", "points_count": 2},
    )
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "collection": "test", "points_count": 2}


def test_optional_api_key(monkeypatch):
    monkeypatch.setattr(routes.settings, "app_api_key", "secret")
    monkeypatch.setattr(
        routes,
        "get_collection_info",
        lambda: {"name": "test", "points_count": 2},
    )

    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/stats", headers={"X-API-Key": "secret"}).status_code == 200
