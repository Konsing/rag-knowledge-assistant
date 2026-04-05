"""
Ingestion pipeline: fetch/load documents -> extract text -> chunk with metadata.

Supports PDFs (local + ArXiv), plain text, markdown, and web pages.
"""

import os

from app.ingestion.arxiv_fetcher import fetch_arxiv_pdf
from app.ingestion.chunker import chunk_document, chunk_plain_document
from app.ingestion.pdf_loader import extract_text_from_pdf
from app.ingestion.text_loader import extract_text_from_file
from app.ingestion.web_loader import fetch_web_page

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")


async def ingest_pdf(file_path: str, filename: str) -> list[dict]:
    """
    Full ingestion pipeline for a local PDF file.

    Returns list of chunks with metadata, ready for embedding.
    """
    pages = extract_text_from_pdf(file_path)
    chunks = chunk_document(pages, source_file=filename)
    return chunks


async def ingest_arxiv_url(url: str) -> tuple[list[dict], str]:
    """
    Full ingestion pipeline for an ArXiv URL.

    Downloads the PDF, extracts text, and chunks it.

    Returns:
        (chunks, filename) - chunks ready for embedding, and the local filename
    """
    local_path = await fetch_arxiv_pdf(url)
    filename = os.path.basename(local_path)
    pages = extract_text_from_pdf(local_path)
    chunks = chunk_document(pages, source_file=filename)
    return chunks, filename


async def ingest_text_file(file_path: str, filename: str) -> list[dict]:
    """
    Full ingestion pipeline for a plain text or markdown file.

    Returns list of chunks with metadata, ready for embedding.
    """
    pages = extract_text_from_file(file_path)
    chunks = chunk_plain_document(pages, source_file=filename)
    return chunks


async def ingest_web_url(url: str) -> tuple[list[dict], str]:
    """
    Full ingestion pipeline for a web page URL.

    Fetches the page, extracts main content (strips boilerplate),
    and chunks it.

    Returns:
        (chunks, url) - chunks ready for embedding, and the source URL
    """
    pages = await fetch_web_page(url)
    chunks = chunk_plain_document(pages, source_file=url)
    return chunks, url
