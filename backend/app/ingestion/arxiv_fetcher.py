"""
ArXiv paper fetcher.

Downloads PDFs from ArXiv URLs (both /abs/ and /pdf/ formats),
saves them locally for processing.
"""

import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.config import settings


def _extract_arxiv_id(url: str) -> str:
    """
    Extract the ArXiv paper ID from a URL.

    Handles:
      - https://arxiv.org/abs/2301.00001
      - https://arxiv.org/abs/2301.00001v2
      - https://arxiv.org/pdf/2301.00001
      - https://arxiv.org/pdf/2301.00001.pdf
    """
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "arxiv.org",
        "www.arxiv.org",
        "export.arxiv.org",
    }:
        raise ValueError(f"Not a supported ArXiv URL: {url}")

    match = re.fullmatch(
        r"/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)(?:\.pdf)?/?",
        parsed.path,
        flags=re.IGNORECASE,
    )
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

    data_dir = Path(settings.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    safe_id = arxiv_id.replace("/", "_")
    local_path = data_dir / f"{safe_id}.pdf"

    # Skip download if already cached
    if local_path.exists():
        with local_path.open("rb") as cached:
            if cached.read(5) == b"%PDF-":
                return str(local_path)
        local_path.unlink()

    temp_path: Path | None = None
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            async with client.stream("GET", pdf_url) as response:
                response.raise_for_status()
                declared_size = response.headers.get("content-length")
                if declared_size and int(declared_size) > settings.max_pdf_bytes:
                    raise ValueError("ArXiv PDF exceeds the configured size limit")

                with tempfile.NamedTemporaryFile(dir=data_dir, suffix=".part", delete=False) as tmp:
                    temp_path = Path(tmp.name)
                    size = 0
                    async for block in response.aiter_bytes():
                        size += len(block)
                        if size > settings.max_pdf_bytes:
                            raise ValueError("ArXiv PDF exceeds the configured size limit")
                        tmp.write(block)

        with temp_path.open("rb") as downloaded:
            if downloaded.read(5) != b"%PDF-":
                raise ValueError("ArXiv returned content that is not a valid PDF")
        os.replace(temp_path, local_path)
        temp_path = None
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

    return str(local_path)
