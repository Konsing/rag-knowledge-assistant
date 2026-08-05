"""
Web page text extraction.

Fetches a URL and extracts the main readable content, automatically
stripping navigation, ads, scripts, and other boilerplate.
"""

import httpx
import trafilatura
from urllib.parse import urljoin

from app.config import settings
from app.ingestion.url_safety import validate_public_http_url


async def fetch_web_page(url: str) -> list[dict]:
    """
    Fetch a web page and extract its main text content.

    Uses trafilatura for intelligent content extraction — it identifies
    the article body and strips boilerplate automatically.

    Returns:
        List of {page_number, text} dicts (single entry).

    Raises:
        ValueError: If no meaningful text could be extracted.
    """
    headers = {"User-Agent": "RAGKnowledgeAssistant/1.0 (research tool)"}
    current_url = await validate_public_http_url(url)

    async with httpx.AsyncClient(follow_redirects=False, timeout=30.0, headers=headers) as client:
        for redirect_count in range(settings.max_redirects + 1):
            async with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location or redirect_count >= settings.max_redirects:
                        raise ValueError("Web page exceeded the redirect limit")
                    current_url = await validate_public_http_url(urljoin(current_url, location))
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not any(
                    supported in content_type
                    for supported in ("text/html", "application/xhtml+xml", "text/plain")
                ):
                    raise ValueError(f"Unsupported web content type: {content_type.split(';')[0]}")

                declared_size = response.headers.get("content-length")
                if declared_size and int(declared_size) > settings.max_web_bytes:
                    raise ValueError("Web page exceeds the configured size limit")

                body = bytearray()
                async for block in response.aiter_bytes():
                    body.extend(block)
                    if len(body) > settings.max_web_bytes:
                        raise ValueError("Web page exceeds the configured size limit")
                encoding = response.encoding or "utf-8"
                html = bytes(body).decode(encoding, errors="replace")
                break
        else:  # pragma: no cover - loop always exits or raises
            raise ValueError("Web page exceeded the redirect limit")

    text = trafilatura.extract(html, output_format="markdown", include_links=True)

    if not text or len(text.strip()) < 50:
        raise ValueError(f"Could not extract meaningful text from {url}")

    return [{"page_number": 1, "text": text}]
