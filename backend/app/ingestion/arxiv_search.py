"""
ArXiv paper search via the free ArXiv API.

Finds relevant papers for a query — no API key needed, no cost.
Used by the MCP research_papers tool to auto-discover papers to ingest.
"""

import re
import xml.etree.ElementTree as ET

import httpx

ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract the ArXiv ID from an entry URL like http://arxiv.org/abs/2301.08745v1."""
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?$", entry_id)
    return match.group(1) if match else entry_id


async def search_arxiv(query: str, max_results: int = 3) -> list[dict]:
    """
    Search ArXiv for papers relevant to a query.

    Returns:
        List of {title, arxiv_id, url, abstract, authors} dicts.
    """
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(ARXIV_API_URL, params=params)
        response.raise_for_status()

    # Parse Atom XML
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(response.text)

    results = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)
        entry_id = entry.find("atom:id", ns)

        authors = [
            a.find("atom:name", ns).text
            for a in entry.findall("atom:author", ns)
            if a.find("atom:name", ns) is not None
        ]

        if title is not None and entry_id is not None:
            arxiv_id = _extract_arxiv_id(entry_id.text.strip())
            results.append({
                "title": " ".join(title.text.strip().split()),
                "arxiv_id": arxiv_id,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "abstract": " ".join(summary.text.strip().split())[:500] if summary is not None else "",
                "authors": authors[:5],  # First 5 authors
            })

    return results
