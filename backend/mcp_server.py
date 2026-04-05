"""
MCP server for the RAG Knowledge Assistant.

Exposes the RAG pipeline as tools that AI assistants (Claude Code, etc.)
can call to query, search, and ingest documents into the knowledge base.

Run:
    python mcp_server.py                          # streamable-http on port 8811
    python mcp_server.py --transport stdio        # stdio for local CLI usage
"""

import argparse
import sys

from app.embedding.embedder import embed_query, embed_texts
from app.generation.llm_client import generate_answer
from app.ingestion import ingest_arxiv_url, ingest_web_url
from app.ingestion.web_search import search_web
from app.retrieval.search import ensure_collection, get_collection_info, search, upsert_chunks

# Parse args before creating FastMCP so host/port are available
_parser = argparse.ArgumentParser(description="RAG Knowledge Assistant MCP Server")
_parser.add_argument(
    "--transport",
    choices=["stdio", "streamable-http", "sse"],
    default="streamable-http",
    help="MCP transport protocol (default: streamable-http)",
)
_parser.add_argument("--port", type=int, default=8811, help="Port for HTTP transport (default: 8811)")
_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
_args = _parser.parse_args()

# Ensure Qdrant collection exists on startup
ensure_collection()

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "RAG Knowledge Assistant",
    instructions="Query and manage a local RAG knowledge base of research papers and documents",
    host=_args.host,
    port=_args.port,
)


@mcp.tool()
def query_knowledge_base(question: str, top_k: int = 5) -> dict:
    """Search the knowledge base and get a cited answer grounded in source documents.

    Embeds the question, finds the most relevant document chunks via cosine
    similarity in Qdrant, then generates an answer with [1],[2] source citations
    using the configured LLM (OpenAI or Claude).

    Costs ~$0.0005 per call (one LLM generation). Use search_chunks for free lookups.

    Args:
        question: The question to answer from the knowledge base
        top_k: Number of source chunks to retrieve (default 5)
    """
    query_vector = embed_query(question)
    results = search(query_vector, top_k=top_k)

    if not results:
        return {"answer": "No relevant sources found in the knowledge base.", "sources": []}

    answer = generate_answer(question, results)
    sources = [
        {
            "text": r["text"][:500],
            "source_file": r["metadata"]["source_file"],
            "page_number": r["metadata"]["page_number"],
            "section_title": r["metadata"]["section_title"],
            "score": round(r["score"], 3),
        }
        for r in results
    ]
    return {"answer": answer, "sources": sources}


@mcp.tool()
def search_chunks(question: str, top_k: int = 5) -> dict:
    """Search the knowledge base and return raw document chunks WITHOUT generating an answer.

    Use this for quick lookups when you don't need an LLM-generated answer.
    Returns the most relevant chunks with metadata and similarity scores.
    Free — no LLM call, just embedding + vector search.

    Args:
        question: Search query
        top_k: Number of chunks to return (default 5)
    """
    query_vector = embed_query(question)
    results = search(query_vector, top_k=top_k)
    return {
        "chunks": [
            {
                "text": r["text"][:500],
                "source_file": r["metadata"]["source_file"],
                "page_number": r["metadata"]["page_number"],
                "section_title": r["metadata"]["section_title"],
                "score": round(r["score"], 3),
            }
            for r in results
        ],
        "count": len(results),
    }


@mcp.tool()
async def ingest_arxiv(url: str) -> dict:
    """Ingest an ArXiv paper into the knowledge base.

    Downloads the PDF, extracts text, chunks it with section awareness,
    embeds the chunks locally (free), and stores them in Qdrant.

    Args:
        url: ArXiv URL (e.g. https://arxiv.org/abs/2301.08745 or https://arxiv.org/pdf/2301.08745)
    """
    chunks, filename = await ingest_arxiv_url(url)
    if not chunks:
        return {"error": "No text could be extracted from the paper"}

    vectors = embed_texts([c["text"] for c in chunks])
    upsert_chunks(chunks, vectors)

    return {
        "doc_id": chunks[0]["metadata"]["doc_id"],
        "filename": filename,
        "num_chunks": len(chunks),
        "message": f"Successfully ingested {len(chunks)} chunks from {filename}",
    }


@mcp.tool()
async def ingest_web_page(url: str) -> dict:
    """Ingest a web page into the knowledge base.

    Fetches the URL, extracts the main text content (strips navigation,
    ads, and boilerplate), chunks it, embeds locally (free), and stores
    in Qdrant.

    Args:
        url: Any web page URL to ingest
    """
    chunks, source = await ingest_web_url(url)
    if not chunks:
        return {"error": "No text could be extracted from the web page"}

    vectors = embed_texts([c["text"] for c in chunks])
    upsert_chunks(chunks, vectors)

    return {
        "doc_id": chunks[0]["metadata"]["doc_id"],
        "source": source,
        "num_chunks": len(chunks),
        "message": f"Successfully ingested {len(chunks)} chunks from {url}",
    }


@mcp.tool()
async def research(question: str, max_pages: int = 3, top_k: int = 5) -> dict:
    """Automatically search the web, ingest relevant pages, and answer a question.

    This is the all-in-one research tool. It:
    1. Searches DuckDuckGo for pages relevant to your question (free)
    2. Ingests the top results into the knowledge base (free)
    3. Queries the enriched knowledge base for a cited answer (~$0.0005)

    Use this when the knowledge base might not have information on a topic yet.
    The ingested pages persist, so future queries on the same topic are instant.

    Args:
        question: The research question to answer
        max_pages: Number of web pages to search and ingest (default 3, max 5)
        top_k: Number of source chunks to retrieve for the answer (default 5)
    """
    max_pages = min(max_pages, 5)

    # Step 1: Search the web
    web_results = search_web(question, max_results=max_pages)
    if not web_results:
        return {"error": "No web results found for this query"}

    # Step 2: Ingest each result
    ingested = []
    for result in web_results:
        url = result["url"]
        try:
            chunks, source = await ingest_web_url(url)
            if chunks:
                vectors = embed_texts([c["text"] for c in chunks])
                upsert_chunks(chunks, vectors)
                ingested.append({
                    "url": url,
                    "title": result["title"],
                    "chunks": len(chunks),
                })
        except Exception:
            # Skip pages that fail to load — move on to the next
            continue

    if not ingested:
        return {"error": "Could not extract text from any of the search results"}

    # Step 3: Query the now-enriched knowledge base
    query_vector = embed_query(question)
    results = search(query_vector, top_k=top_k)

    if not results:
        return {
            "answer": "Ingested pages but could not find relevant chunks for this specific question.",
            "sources": [],
            "ingested": ingested,
        }

    answer = generate_answer(question, results)
    sources = [
        {
            "text": r["text"][:500],
            "source_file": r["metadata"]["source_file"],
            "section_title": r["metadata"]["section_title"],
            "score": round(r["score"], 3),
        }
        for r in results
    ]

    return {
        "answer": answer,
        "sources": sources,
        "ingested": ingested,
    }


@mcp.tool()
def get_stats() -> dict:
    """Get statistics about the knowledge base.

    Returns the collection name and total number of document chunks stored.
    """
    return get_collection_info()


if __name__ == "__main__":
    mcp.run(transport=_args.transport)
