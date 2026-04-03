# RAG Knowledge Assistant — Design Spec

## Context

Build a production-quality RAG (Retrieval-Augmented Generation) system from scratch — no LangChain, no LlamaIndex. The goal is to deeply understand every layer: chunking, embedding, vector search, and LLM-grounded generation. Primary use case is ingesting ArXiv research papers and answering questions with cited sources. This is a portfolio/learning project meant to demonstrate senior-level understanding of RAG architecture.

## Architecture: Modular Monolith

Single FastAPI backend with clear internal module boundaries. Each module owns its logic and has explicit interfaces. One `docker-compose up` runs everything.

### Project Structure

```
rag-knowledge-assistant/
├── CLAUDE.md                   # Project conventions, maintained throughout
├── README.md                   # Thorough project README (architecture, setup, usage, resume highlights)
├── nextsteps.md                # Post-project improvements and next steps (gitignored)
├── docker-compose.yml          # Qdrant + backend + frontend
├── .env.example                # Template for API keys + config
├── .gitignore                  # Includes nextsteps.md, data/, .env, qdrant_storage/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app entry point
│   └── app/
│       ├── __init__.py
│       ├── config.py           # Pydantic BaseSettings (loads .env)
│       ├── models.py           # Shared Pydantic request/response schemas
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── pdf_loader.py   # PyMuPDF text extraction
│       │   ├── arxiv_fetcher.py # Download PDF from ArXiv URL
│       │   └── chunker.py     # Section-aware text chunker with overlap
│       ├── embedding/
│       │   ├── __init__.py
│       │   └── embedder.py    # sentence-transformers all-MiniLM-L6-v2
│       ├── retrieval/
│       │   ├── __init__.py
│       │   └── search.py      # Qdrant cosine similarity search
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── llm_client.py  # Claude API wrapper
│       │   └── prompts.py     # Prompt templates for cited answers
│       └── api/
│           ├── __init__.py
│           └── routes.py      # /ingest and /query endpoints (thin)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── ChatWindow.tsx
│       │   ├── MessageBubble.tsx
│       │   └── IngestPanel.tsx
│       └── api/
│           └── client.ts
├── eval/
│   └── eval_retrieval.py       # 10 test questions, precision scoring
└── data/                       # Gitignored — local PDF storage
```

### Docker Compose Services

| Service | Image | Port | Notes |
|---------|-------|------|-------|
| qdrant | `qdrant/qdrant:latest` | 6333 | Persists to `./qdrant_storage` volume |
| backend | Custom (Python 3.11) | 8000 | Hot-reload via uvicorn `--reload` |
| frontend | Custom (Node 20) | 5173 | Vite dev server, proxies `/api` to backend |

## Data Flow: Ingestion Pipeline

```
Upload PDF / paste ArXiv URL
  → arxiv_fetcher (if URL, downloads PDF)
  → pdf_loader (PyMuPDF extracts text + page numbers)
  → chunker (section-aware splitting + overlap)
  → embedder (MiniLM encodes each chunk → 384-dim vector)
  → Qdrant upsert (vectors + metadata)
```

### ArXiv Fetcher

- Accepts both `arxiv.org/abs/XXXX.XXXXX` and `arxiv.org/pdf/XXXX.XXXXX` URL formats
- Normalizes to the PDF download URL (`arxiv.org/pdf/XXXX.XXXXX.pdf`)
- Downloads PDF to `data/` directory with the ArXiv ID as filename
- Returns the local file path to the PDF loader

### Chunking Strategy

- **Primary:** Split on section headers (regex: `\n[A-Z][A-Za-z ]+\n`, numbered sections `1. Introduction`, etc.)
- **Fallback:** Recursive character splitting at paragraph → sentence boundaries
- **Target chunk size:** ~500 tokens (~375 words)
- **Overlap:** 100 tokens between adjacent chunks
- **Strip references:** Detect and exclude bibliography/references section (noise for retrieval)
- **Metadata per chunk:** `source_file`, `page_number`, `section_title`, `chunk_index`, `doc_id`

### Why These Parameters

- 500 tokens: enough for a coherent thought, small enough for precise retrieval
- 100-token overlap: prevents losing context at chunk boundaries
- MiniLM max input is 256 tokens — it truncates longer inputs, but we store the full chunk text for LLM context
- Section-aware splitting respects document structure; academic papers have clear sections

## Data Flow: Query Pipeline

```
User question
  → embedder (same MiniLM model encodes query → 384-dim vector)
  → Qdrant search (cosine similarity, top-k=5, optional score threshold ≥ 0.3)
  → generation (Claude Sonnet with retrieved chunks as numbered context)
  → Response: { answer (with [1],[2] citations), sources [{text, file, page, score}] }
```

### Retrieval Parameters

- **top-k = 5** — good default balance of recall vs noise
- **Score threshold = 0.3** — filter irrelevant chunks when KB doesn't have an answer
- **Same embedding model** for docs and queries — required for cosine similarity to work

### Generation Prompt Design

- System prompt: answer ONLY from provided context, cite using [1], [2] notation
- Each chunk labeled with index and metadata (file, page, section)
- If no relevant context: respond "I don't have enough information" — no hallucination
- Keep prompt under ~4000 tokens to leave room for response

## Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| PDF extraction | PyMuPDF (fitz) | Fast, handles complex layouts, page-level text |
| Embeddings | all-MiniLM-L6-v2 | 384-dim, free, local, good quality/speed balance |
| Vector DB | Qdrant (Docker) | Free local mode, great Python SDK, metadata filtering |
| LLM | Claude API (Sonnet) | Strong instruction following for citations |
| Backend | FastAPI | Async, auto OpenAPI docs, Pydantic integration |
| Frontend | React + Vite + Tailwind | Fast dev, modern stack, good for portfolio |
| Test data | ArXiv open-access papers | Free, well-structured PDFs, signals data licensing awareness |

## Production Differences (to discuss in interviews)

- Embeddings: OpenAI `text-embedding-3-small` or Cohere for better quality
- Chunking: semantic chunking via embedding similarity, not just text boundaries
- Vector DB: managed Qdrant Cloud or Pinecone for scale + backups
- Auth: API key or OAuth on endpoints
- Ingestion: async job queue (Celery/Redis) for large batches
- Observability: structured logging, latency metrics, retrieval quality monitoring
- Reranking: cross-encoder reranker between retrieval and generation for better precision

## Build Phases

| Phase | Focus | Key Deliverable |
|-------|-------|-----------------|
| 1 | Project scaffold | docker-compose up works, CLAUDE.md + README.md + nextsteps.md created, all dirs + deps in place |
| 2 | Ingestion pipeline | PDF loader + section-aware chunker + ArXiv fetcher |
| 3 | Embedding + storage | Embed chunks with MiniLM, upsert to Qdrant |
| 4 | Retrieval engine | Embed query, cosine search, return top-k chunks |
| 5 | Generation layer | Claude API call with context, cited answers |
| 6 | FastAPI layer | /ingest and /query endpoints, error handling |
| 7 | React chat UI | Chat interface with answer + source citations |
| 8 | Eval script | 10 test questions, retrieval precision scoring |

Each phase is self-contained and testable independently.

## Verification Plan

- **Phase 1:** `docker-compose up` starts all 3 services without errors; FastAPI docs at localhost:8000/docs; React app at localhost:5173
- **Phase 2:** Unit test: load a PDF, verify chunks have correct metadata and overlap
- **Phase 3:** Integration test: embed chunks, verify Qdrant collection has expected point count
- **Phase 4:** Integration test: query Qdrant, verify returned chunks are semantically relevant
- **Phase 5:** Manual test: pass chunks to Claude, verify cited answer format
- **Phase 6:** curl /ingest with a PDF, then curl /query — end-to-end test
- **Phase 7:** Visual test: UI renders answer with clickable citations
- **Phase 8:** Run eval script, verify precision metrics are logged
