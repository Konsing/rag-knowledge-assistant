# RAG Knowledge Assistant

## Project Overview
A production-quality RAG system built from scratch (no LangChain/LlamaIndex). Ingests documents (ArXiv papers, PDFs, web pages, text/markdown files), chunks and embeds them, stores vectors in Qdrant, retrieves relevant chunks via cosine similarity, and generates cited answers. Also exposes the pipeline as an MCP server for AI assistant integration.

## Architecture
Modular monolith — single FastAPI backend with clear module boundaries:
- `backend/app/ingestion/` — PDF loading, ArXiv fetching, web scraping, text loading, chunking
- `backend/app/embedding/` — sentence-transformers (all-MiniLM-L6-v2)
- `backend/app/retrieval/` — Qdrant cosine similarity search
- `backend/app/generation/` — LLM client (OpenAI or Claude, configurable via LLM_PROVIDER env var), prompt templates
- `backend/app/api/` — FastAPI routes (thin — delegates to modules)
- `backend/mcp_server.py` — MCP server (separate entry point, imports same modules)
- `frontend/` — React + Vite + Tailwind chat UI

## Commands
- `docker compose up` — run everything (Qdrant + backend + frontend)
- `docker compose up --build` — rebuild and run
- `docker compose up mcp-server` — run MCP server (port 8811)
- `docker compose exec backend python -m eval.eval_retrieval` — run retrieval evaluation
- `cd backend && pytest` — run backend tests

## MCP Server
- Configured in `.mcp.json` for Claude Code (streamable-http on port 8811)
- Tools: `research` (auto web search + ingest + answer), `query_knowledge_base`, `search_chunks` (free), `ingest_arxiv`, `ingest_web_page`, `get_stats`
- Shares backend modules directly — no HTTP-to-HTTP calls

## Tech Stack
- **Python 3.11**, FastAPI, Pydantic v2, PyMuPDF, sentence-transformers, anthropic SDK, openai SDK, MCP SDK, trafilatura
- **React 18**, Vite, Tailwind CSS, TypeScript
- **Qdrant** (local Docker) for vector storage
- **OpenAI** (GPT-4o-mini) or **Claude** (Sonnet) for generation — set `LLM_PROVIDER` in `.env`

## Conventions
- API routes are thin — validate input, delegate to modules, return response
- All config via Pydantic BaseSettings loading from `.env`
- Shared Pydantic models in `backend/app/models.py`
- Each module owns its logic and has explicit interfaces
- MCP server reuses backend modules via direct import (no duplication)
