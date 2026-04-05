"""
Web page text extraction.

Fetches a URL and extracts the main readable content, automatically
stripping navigation, ads, scripts, and other boilerplate.
"""

import httpx
import trafilatura


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
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()

    text = trafilatura.extract(response.text)

    if not text or len(text.strip()) < 50:
        raise ValueError(f"Could not extract meaningful text from {url}")

    return [{"page_number": 1, "text": text}]
