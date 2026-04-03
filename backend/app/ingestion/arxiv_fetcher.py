"""
ArXiv paper fetcher.

Downloads PDFs from ArXiv URLs (both /abs/ and /pdf/ formats),
saves them locally for processing.
"""

import os
import re

import httpx

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")


def _extract_arxiv_id(url: str) -> str:
    """
    Extract the ArXiv paper ID from a URL.

    Handles:
      - https://arxiv.org/abs/2301.00001
      - https://arxiv.org/abs/2301.00001v2
      - https://arxiv.org/pdf/2301.00001
      - https://arxiv.org/pdf/2301.00001.pdf
    """
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    if not match:
        raise ValueError(f"Could not parse ArXiv ID from URL: {url}")
    return match.group(1)


def _build_pdf_url(arxiv_id: str) -> str:
    """Build the direct PDF download URL from an ArXiv ID."""
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


async def fetch_arxiv_pdf(url: str) -> str:
    """
    Download an ArXiv paper PDF and save it locally.

    Args:
        url: ArXiv URL (abs or pdf format)

    Returns:
        Local file path to the downloaded PDF
    """
    arxiv_id = _extract_arxiv_id(url)
    pdf_url = _build_pdf_url(arxiv_id)

    os.makedirs(DATA_DIR, exist_ok=True)
    local_path = os.path.join(DATA_DIR, f"{arxiv_id}.pdf")

    # Skip download if already cached
    if os.path.exists(local_path):
        return local_path

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(pdf_url)
        response.raise_for_status()

    with open(local_path, "wb") as f:
        f.write(response.content)

    return local_path
