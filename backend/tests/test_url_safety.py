import asyncio

import pytest

from app.ingestion import url_safety


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data",
        "https://user:password@example.com/",
    ],
)
def test_unsafe_urls_are_rejected(monkeypatch, url):
    async def resolve(hostname, port):
        del hostname, port
        return {"127.0.0.1"}

    monkeypatch.setattr(url_safety, "_resolve_host", resolve)
    with pytest.raises(url_safety.UnsafeURLError):
        asyncio.run(url_safety.validate_public_http_url(url))


def test_public_url_is_accepted(monkeypatch):
    async def resolve(hostname, port):
        assert hostname == "example.com"
        assert port == 443
        return {"93.184.216.34"}

    monkeypatch.setattr(url_safety, "_resolve_host", resolve)
    result = asyncio.run(url_safety.validate_public_http_url("https://example.com/article"))
    assert result == "https://example.com/article"
