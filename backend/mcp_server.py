"""MCP tools for querying and expanding the RAG knowledge base."""

import argparse
import asyncio
import logging
import time

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.ingestion import ingest_arxiv_url, ingest_web_url
from app.ingestion.arxiv_search import search_arxiv
from app.ingestion.web_search import search_web
from app.retrieval.search import ensure_collection, get_collection_info
from app.service import answer, retrieve, store_chunks

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "RAG Knowledge Assistant",
    instructions="Query and manage a local RAG knowledge base of research papers and documents",
    host=settings.mcp_host,
    port=settings.mcp_port,
)


def _question(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("question must not be blank")
    if len(value) > 4_000:
        raise ValueError("question must be at most 4000 characters")
    return value


def _bounded(value: int, name: str, maximum: int) -> int:
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


def _sources(results: list[dict], include_page: bool = True) -> list[dict]:
    sources = []
    for result in results:
        source = {
            "text": result["text"][:500],
            "source_file": result["metadata"]["source_file"],
            "section_title": result["metadata"]["section_title"],
            "score": round(result["score"], 3),
        }
        if include_page:
            source["page_number"] = result["metadata"]["page_number"]
        sources.append(source)
    return sources


@mcp.tool()
async def query_knowledge_base(question: str, top_k: int = 5) -> dict:
    """Get a cited answer grounded in documents already in the knowledge base."""
    question = _question(question)
    top_k = _bounded(top_k, "top_k", 10)
    generated, results = await answer(question, top_k)
    if not results:
        return {"answer": "No relevant sources found in the knowledge base.", "sources": []}
    return {"answer": generated, "sources": _sources(results)}


@mcp.tool()
async def search_chunks(question: str, top_k: int = 5) -> dict:
    """Return relevant raw chunks without calling a generation model."""
    question = _question(question)
    top_k = _bounded(top_k, "top_k", 10)
    results = await retrieve(question, top_k)
    return {"chunks": _sources(results), "count": len(results)}


@mcp.tool()
async def research_papers(question: str, max_papers: int = 3, top_k: int = 5) -> dict:
    """Search ArXiv, ingest papers, and answer only from those papers."""
    question = _question(question)
    max_papers = _bounded(max_papers, "max_papers", 5)
    top_k = _bounded(top_k, "top_k", 10)

    papers = await search_arxiv(question, max_results=max_papers)
    if not papers:
        return {"error": "No papers found on ArXiv for this query"}

    ingested: list[dict] = []
    failures: list[dict] = []
    doc_ids: list[str] = []
    for paper in papers:
        try:
            chunks, _ = await ingest_arxiv_url(paper["url"])
            if not chunks:
                raise ValueError("no text could be extracted")
            count = await store_chunks(chunks)
            doc_ids.append(chunks[0]["metadata"]["doc_id"])
            ingested.append({
                "title": paper["title"],
                "arxiv_id": paper["arxiv_id"],
                "url": paper["url"],
                "authors": paper["authors"],
                "chunks": count,
            })
        except Exception as exc:
            logger.warning("Failed to ingest ArXiv result %s: %s", paper.get("url"), exc)
            failures.append({"url": paper.get("url", ""), "error": type(exc).__name__})

    if not ingested:
        return {"error": "Could not download or extract any found papers", "failures": failures}

    generated, results = await answer(question, top_k, doc_ids)
    response = {
        "answer": generated or "Ingested papers but found no relevant chunks.",
        "sources": _sources(results),
        "papers_ingested": ingested,
    }
    if failures:
        response["failures"] = failures
    return response


@mcp.tool()
async def ingest_arxiv(url: str) -> dict:
    """Ingest one ArXiv paper into the knowledge base."""
    chunks, filename = await ingest_arxiv_url(url.strip())
    if not chunks:
        return {"error": "No text could be extracted from the paper"}
    count = await store_chunks(chunks)
    return {
        "doc_id": chunks[0]["metadata"]["doc_id"],
        "filename": filename,
        "num_chunks": count,
        "message": f"Successfully ingested {count} chunks from {filename}",
    }


@mcp.tool()
async def ingest_web_page(url: str) -> dict:
    """Ingest one public web page into the knowledge base."""
    chunks, source = await ingest_web_url(url.strip())
    if not chunks:
        return {"error": "No text could be extracted from the web page"}
    count = await store_chunks(chunks)
    return {
        "doc_id": chunks[0]["metadata"]["doc_id"],
        "source": source,
        "num_chunks": count,
        "message": f"Successfully ingested {count} chunks from {source}",
    }


@mcp.tool()
async def research(question: str, max_pages: int = 3, top_k: int = 5) -> dict:
    """Search the web, ingest pages, and answer only from those pages."""
    question = _question(question)
    max_pages = _bounded(max_pages, "max_pages", 5)
    top_k = _bounded(top_k, "top_k", 10)

    web_results = await asyncio.to_thread(search_web, question, max_pages)
    if not web_results:
        return {"error": "No web results found for this query"}

    ingested: list[dict] = []
    failures: list[dict] = []
    doc_ids: list[str] = []
    for result in web_results:
        try:
            chunks, _ = await ingest_web_url(result["url"])
            if not chunks:
                raise ValueError("no text could be extracted")
            count = await store_chunks(chunks)
            doc_ids.append(chunks[0]["metadata"]["doc_id"])
            ingested.append({"url": result["url"], "title": result["title"], "chunks": count})
        except Exception as exc:
            logger.warning("Failed to ingest web result %s: %s", result.get("url"), exc)
            failures.append({"url": result.get("url", ""), "error": type(exc).__name__})

    if not ingested:
        return {"error": "Could not extract text from any search result", "failures": failures}

    generated, results = await answer(question, top_k, doc_ids)
    response = {
        "answer": generated or "Ingested pages but found no relevant chunks.",
        "sources": _sources(results, include_page=False),
        "ingested": ingested,
    }
    if failures:
        response["failures"] = failures
    return response


@mcp.tool()
async def get_stats() -> dict:
    """Return the collection name and total number of stored chunks."""
    return await asyncio.to_thread(get_collection_info)


def _wait_for_qdrant(attempts: int = 20) -> None:
    for attempt in range(attempts):
        try:
            ensure_collection()
            return
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Knowledge Assistant MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="streamable-http",
    )
    parser.add_argument("--port", type=int, default=settings.mcp_port)
    parser.add_argument("--host", default=settings.mcp_host)
    args = parser.parse_args()

    _wait_for_qdrant()
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
