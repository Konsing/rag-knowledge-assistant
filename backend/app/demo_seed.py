"""Idempotently seed the public showcase with a small curated ArXiv corpus."""

import asyncio
import json
from pathlib import Path

from app.config import settings
from app.ingestion import ingest_arxiv_url
from app.retrieval.search import list_documents
from app.service import store_chunks


def load_demo_manifest() -> list[dict]:
    path = Path(settings.demo_documents_file)
    if not path.is_absolute():
        path = Path.cwd() / path
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Demo document manifest must contain a JSON list")
    return data


async def seed_demo_documents() -> dict:
    """Ingest missing manifest entries and preserve existing vector points."""
    existing = await asyncio.to_thread(list_documents)
    existing_sources = {
        document.get("source_url") or document.get("source_file")
        for document in existing
    }
    seeded: list[dict] = []
    skipped: list[str] = []
    failures: list[dict] = []

    for document in load_demo_manifest():
        source_url = str(document.get("source_url", "")).strip()
        if not source_url:
            failures.append({"title": document.get("title", ""), "error": "missing source_url"})
            continue
        if source_url in existing_sources:
            skipped.append(source_url)
            continue
        try:
            chunks, filename = await ingest_arxiv_url(source_url)
            display_metadata = {
                "title": str(document.get("title") or filename),
                "source_url": source_url,
                "description": str(document.get("description", "")),
                "sample_questions": list(document.get("sample_questions") or [])[:5],
            }
            for chunk in chunks:
                chunk["metadata"].update(display_metadata)
            count = await store_chunks(chunks)
            seeded.append({
                "doc_id": chunks[0]["metadata"]["doc_id"],
                "title": display_metadata["title"],
                "chunks": count,
            })
            existing_sources.add(source_url)
        except Exception as exc:
            failures.append({
                "title": str(document.get("title", "")),
                "error": type(exc).__name__,
            })

    return {"seeded": seeded, "skipped": skipped, "failures": failures}
