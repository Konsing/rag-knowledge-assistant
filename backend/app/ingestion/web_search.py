"""
Web search via DuckDuckGo.

Finds relevant web pages for a given query — no API key needed, no cost.
Used by the MCP research tool to auto-discover documents to ingest.
"""

from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 3) -> list[dict]:
    """
    Search the web for pages relevant to a query.

    Returns:
        List of {title, url, snippet} dicts, up to max_results.
    """
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return results
