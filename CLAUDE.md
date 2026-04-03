# RAG Knowledge Assistant

## Project Overview
A production-quality RAG system built from scratch (no LangChain/LlamaIndex). Ingests ArXiv research papers, chunks and embeds them, stores vectors in Qdrant, retrieves relevant chunks via cosine similarity, and generates cited answers using Claude API.

## Architecture
Modular monolith — single FastAPI backend with clear module boundaries:
- `backend/app/ingestion/` — PDF loading, ArXiv fetching, text chunking
- `backend/app/embedding/` — sentence-transformers (all-MiniLM-L6-v2)
- `backend/app/retrieval/` — Qdrant cosine similarity search
- `backend/app/generation/` — LLM client (OpenAI or Claude, configurable via LLM_PROVIDER env var), prompt templates
- `backend/app/api/` — FastAPI routes (thin — delegates to modules)
- `frontend/` — React + Vite + Tailwind chat UI

## Commands
- `docker compose up` — run everything (Qdrant + backend + frontend)
- `docker compose up --build` — rebuild and run
- `docker compose exec backend python -m eval.eval_retrieval` — run retrieval evaluation
- `cd backend && pytest` — run backend tests

## Tech Stack
- **Python 3.11**, FastAPI, Pydantic v2, PyMuPDF, sentence-transformers, anthropic SDK, openai SDK
- **React 18**, Vite, Tailwind CSS, TypeScript
- **Qdrant** (local Docker) for vector storage
- **OpenAI** (GPT-4o-mini) or **Claude** (Sonnet) for generation — set `LLM_PROVIDER` in `.env`

## Conventions
- API routes are thin — validate input, delegate to modules, return response
- All config via Pydantic BaseSettings loading from `.env`
- Shared Pydantic models in `backend/app/models.py`
- Each module owns its logic and has explicit interfaces
