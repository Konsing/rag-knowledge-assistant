# RAG Knowledge Assistant

A production-quality Retrieval-Augmented Generation system built **from scratch** — no LangChain, no LlamaIndex. Every layer (chunking, embedding, retrieval, generation) is hand-written for full understanding and control.

## What It Does

Upload documents — ArXiv papers, PDFs, web pages, or text files — and ask questions about them. The system retrieves relevant passages using vector similarity search and generates cited answers using an LLM (OpenAI or Claude, configurable). Also available as an **MCP server** so AI assistants like Claude Code can query your knowledge base directly.

### Example: Real Output

I ingested [this astrophysics paper about Little Red Dots and dark matter solitons](https://arxiv.org/abs/2601.00044) and asked two questions:

**Q: "What is the opacity crisis and how does it relate to black holes?"**

> The "Opacity Crisis" refers to a phenomenon where, despite the enhanced gravitational
> support provided by the inclusion of a soliton potential in massive cores, radiative
> losses prevail. This leads to significant challenges in understanding the dynamics of
> these massive cores. The crisis highlights the limitations of current models in fully
> accounting for radiative processes in the context of black holes and their formation
> [1][2][3][4][5].
>
> *Sources: 2601.00044.pdf, p.1 — scores 0.59*

**Q: "What are the key findings about thermodynamic instability and cooling in this model?"**

> The key findings about thermodynamic instability and cooling are:
>
> 1. **Cooling Timescale**: The cooling timescale t_cool is derived based on gas properties...
> 2. **Temperature Regimes**: For mass below 2.8 x 10^7 solar masses, the cooling function
>    is suppressed, leading to a stable regime. In the line cooling regime (10^4 - 10^7 K),
>    t_cool scales as M_s^{-0.8}. For bremsstrahlung (T > 10^7 K), t_cool scales as M_s^{-3}.
> 3. **Critical Mass and Opacity Crisis**: A critical mass scale of ~2.8 x 10^7 solar masses
>    is identified. Above this, gas cools faster than the potential can adjust, leading to
>    catastrophic collapse [1][2][3][4][5].
>
> *Sources: 2601.00044.pdf, p.10 — "Thermodynamic Instability and Cooling" — scores 0.45*

The system retrieves the relevant sections, cites them by number, and refuses to hallucinate — if the papers don't contain an answer, it says so.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React UI   │────▶│   FastAPI    │────▶│   Qdrant     │
│  (Tailwind)  │◀────│   Backend    │◀────│  (Vectors)   │
│  port 5173   │     │  port 8000   │     │  port 6333   │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
┌──────────────┐    ┌───────┴────────┐
│  MCP Server  │───▶│  OpenAI/Claude │
│  port 8811   │    │  (Generation)  │
└──────────────┘    └────────────────┘
```

**Modular monolith** — single backend with clear module boundaries. The MCP server imports the same modules directly (zero duplication):

```
backend/
├── mcp_server.py     MCP server entry point (FastMCP)
└── app/
    ├── ingestion/    PDF, ArXiv, web pages, text/markdown loading + chunking
    ├── embedding/    sentence-transformers (all-MiniLM-L6-v2)
    ├── retrieval/    Qdrant cosine similarity search
    ├── generation/   LLM client + prompt templates
    ├── api/          FastAPI routes (thin delegation layer)
    └── config.py     Centralized Pydantic Settings
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| PDF Extraction | PyMuPDF | Fast, handles complex layouts, page-level metadata |
| Embeddings | all-MiniLM-L6-v2 | 384-dim vectors, free, runs locally |
| Vector DB | Qdrant (Docker) | Free local mode, excellent SDK, metadata filtering |
| Web Scraping | trafilatura | Extracts article text, strips boilerplate automatically |
| MCP Server | FastMCP (MCP SDK) | Exposes RAG as tools for AI assistants |
| LLM | OpenAI GPT-4o-mini / Claude | Configurable; strong instruction-following for citations |
| Backend | FastAPI | Async, auto OpenAPI docs, Pydantic integration |
| Frontend | React + Vite + Tailwind | Fast dev, modern stack |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An **OpenAI API key** (GPT-4o-mini, ~$0.0005/query) or **Anthropic API key** (Claude Sonnet)

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/Konsing/rag-knowledge-assistant.git
cd rag-knowledge-assistant

# 2. Set up environment
cp .env.example .env
# Edit .env — add your API key and set LLM_PROVIDER to "openai" or "claude"

# 3. Run everything (Qdrant + backend + frontend + MCP server)
docker compose up --build

# 4. Open the UI
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/docs
# Qdrant:    http://localhost:6333/dashboard
# MCP:       http://localhost:8811/mcp (for AI assistant integration)
```

## Supported Document Types

| Source | How to ingest | Chunking strategy |
|--------|---------------|-------------------|
| ArXiv papers | Paste URL in UI or API (`arxiv_url` field) | Section-aware (detects numbered sections, ALL-CAPS headers), strips references |
| PDF files | Upload in UI or API (`file` field) | Same as ArXiv ��� section-aware with page tracking |
| Web pages | Paste URL in UI or API (`url` field) | Markdown heading detection, paragraph fallback |
| Text files (.txt) | Upload in UI or API | Paragraph-based splitting |
| Markdown files (.md) | Upload in UI or API | Markdown heading detection (`#`, `##`, `###`) |

All sources go through the same pipeline after chunking: embed locally with sentence-transformers → store in Qdrant → available for retrieval. Embedding and storage are always free.

### Example: Web page ingestion

I ingested the [Wikipedia article on Retrieval-augmented generation](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) and queried:

**Q: "What is retrieval augmented generation?"**

> Retrieval-augmented generation (RAG) is a technique that enhances large language models (LLMs)
> by enabling them to retrieve and incorporate new information from external data sources when
> responding to user queries. Instead of relying solely on pre-existing training data, RAG allows
> LLMs to access specific documents, databases, or web sources to supplement their responses and
> provide more accurate and up-to-date information. This method helps reduce AI hallucinations —
> instances where models produce incorrect or fabricated information — by grounding responses in
> factual content [1][2][3].
>
> *Source: en.wikipedia.org, 10 chunks ingested, top score 0.60*

The system extracted the article text from Wikipedia (stripping navigation, ads, and sidebar boilerplate using trafilatura), chunked it, and grounded its answer in the actual article content.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/ingest` | Upload file (PDF/txt/md), ArXiv URL, or web URL |
| `POST` | `/api/query` | Ask a question, get cited answer |

### Ingest documents

```bash
# Upload a PDF
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@paper.pdf"

# ArXiv URL
curl -X POST http://localhost:8000/api/ingest \
  -F "arxiv_url=https://arxiv.org/abs/2301.00001"

# Web page
curl -X POST http://localhost:8000/api/ingest \
  -F "url=https://en.wikipedia.org/wiki/Retrieval-augmented_generation"

# Text or markdown file
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@notes.md"
```

### Query the knowledge base

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the main findings?", "top_k": 5}'
```

## MCP Server (AI Assistant Integration)

The RAG pipeline is also available as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server, so AI assistants like Claude Code can query your knowledge base as a tool — no copy-pasting, no browser needed.

### How it works

The MCP server runs as a separate Docker service that imports the same backend modules directly. When Claude Code calls a tool like `query_knowledge_base`, the MCP server embeds the question, searches Qdrant, and generates a cited answer — identical to what the React UI does.

### Setup

```bash
# 1. Start all services (MCP server included)
docker compose up --build

# 2. Register the MCP server with Claude Code
claude mcp add --transport http --scope project rag-knowledge-base http://localhost:8811/mcp

# 3. Restart Claude Code — the tools are now available
```

To verify it's connected:
```bash
claude mcp list
# Should show: rag-knowledge-base: http://localhost:8811/mcp (HTTP) - ✓ Connected
```

If you want to run the MCP server standalone (e.g., for testing without the frontend):
```bash
docker compose up qdrant mcp-server
```

### Available tools

| MCP Tool | What it does | Cost |
|----------|-------------|------|
| `research` | **Auto-research**: searches the web, ingests relevant pages, answers the question | ~$0.0005 |
| `query_knowledge_base` | Get a cited answer from already-ingested documents | ~$0.0005 |
| `search_chunks` | Find relevant chunks without LLM generation | Free |
| `ingest_arxiv` | Add an ArXiv paper to the knowledge base | Free |
| `ingest_web_page` | Add a web page to the knowledge base | Free |
| `get_stats` | Check how many chunks are indexed | Free |

The `research` tool is the most powerful — it combines web search (DuckDuckGo), page ingestion (trafilatura), and RAG querying into a single call. You don't need to manually find and ingest pages; just ask a question and it handles everything. Ingested pages persist in the knowledge base, so future queries on the same topic are instant.

I designed `search_chunks` as a free alternative to `query_knowledge_base` — it returns raw document chunks without calling the LLM, so the AI assistant can decide whether it needs a full generated answer or just wants to look up a fact.

### Example: Using MCP tools in Claude Code

Once the MCP server is running, you can ask Claude Code things like:

> "Research what transformer attention mechanisms are and how they work"

Claude Code will call `research`, which automatically searches the web for relevant pages, ingests the top results, and returns a cited answer — all in one step. The ingested pages stay in the knowledge base for future queries.

> "Use the knowledge base to look up what retrieval augmented generation is"

Claude Code will call `query_knowledge_base` and return a cited answer from already-ingested documents.

> "Ingest this ArXiv paper into the knowledge base: https://arxiv.org/abs/2301.08745"

Claude Code will call `ingest_arxiv`, which downloads the paper, chunks it, embeds it, and stores it in Qdrant.

### Alternative: stdio transport

If you want to run the MCP server without Docker (e.g., directly on your machine), you can use stdio transport:

```bash
claude mcp add -e QDRANT_HOST=localhost -e QDRANT_PORT=6333 \
  rag-knowledge-base -- python backend/mcp_server.py --transport stdio
```

This requires Qdrant running locally and Python dependencies installed on the host.

## Project Structure

```
rag-knowledge-assistant/
├── docker-compose.yml          Orchestrates all services (Qdrant, backend, frontend, MCP)
├── .mcp.json                   Claude Code MCP server configuration
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 FastAPI entry point
│   ├── mcp_server.py           MCP server entry point
│   └── app/
│       ├── config.py           Pydantic Settings (.env loader)
│       ├── models.py           Shared request/response schemas
│       ├── ingestion/          PDF, ArXiv, web, text/markdown loading + chunking
│       ├── embedding/          Vector encoding
│       ├── retrieval/          Similarity search
│       ├── generation/         LLM + prompts
│       └── api/                Route handlers
├── frontend/
│   ├── Dockerfile
│   └── src/                    React + Tailwind UI
├── eval/
│   └── eval_retrieval.py       Retrieval quality evaluation
└── data/                       Local document storage (gitignored)
```

## Build Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Project scaffold + Docker setup | Done |
| 2 | Ingestion pipeline (PDF + chunking) | Done |
| 3 | Embedding + Qdrant vector storage | Done |
| 4 | Retrieval engine (cosine similarity) | Done |
| 5 | Generation layer (Claude + citations) | Done |
| 6 | FastAPI endpoints (full implementation) | Done |
| 7 | React chat UI with source citations | Done |
| 8 | Evaluation script (precision scoring) | Done |
| 9 | MCP server (AI assistant integration) | Done |
| 10 | Broader search (web pages, text, markdown) | Done |

## What Would Change in Production

- **Embeddings:** OpenAI `text-embedding-3-small` or Cohere for better quality
- **Chunking:** Semantic chunking using embedding similarity, not just text boundaries
- **Reranking:** Cross-encoder reranker between retrieval and generation
- **Vector DB:** Managed Qdrant Cloud or Pinecone for scale + backups
- **Auth:** API keys or OAuth on all endpoints
- **Ingestion:** Async job queue (Celery/Redis) for large batch processing
- **Observability:** Structured logging, latency metrics, retrieval quality monitoring
- **Streaming:** Server-sent events for real-time answer generation

## What I Built and Why

I built every layer of this RAG system from scratch — no LangChain, no LlamaIndex — because I wanted to deeply understand how retrieval-augmented generation actually works under the hood.

**Custom ingestion pipeline.** I wrote the PDF text extraction (PyMuPDF), the ArXiv URL fetcher, and a section-aware text chunker. The chunker uses regex-based section header detection tuned for academic papers, with paragraph-level fallback splitting and configurable overlap. I iterated on the section detection against real ArXiv papers — the first version matched table headers as sections, so I tightened the patterns to only accept numbered sections and ALL-CAPS headers within reasonable bounds. This kind of iterative refinement against real data is how production chunking works.

**Hand-rolled embedding and retrieval.** I use sentence-transformers (all-MiniLM-L6-v2) to encode chunks into 384-dimensional vectors and store them in Qdrant with full metadata payloads. The same model embeds both documents and queries — this is critical because cosine similarity only works within the same vector space. I chose cosine over euclidean distance because for text embeddings, direction matters more than magnitude.

**Citation-grounded generation.** I engineered the prompt to instruct Claude to answer only from the provided context and cite sources using [1], [2] notation. Each retrieved chunk is labeled with its source file, page number, and section title. If the retrieval returns nothing relevant, the system says "I don't have enough information" rather than hallucinating — this is a deliberate design choice.

**Quantitative evaluation.** I wrote an evaluation harness with 10 test questions and expected section keywords. The system achieves 70% retrieval precision — a solid baseline that identifies exactly where improvements are needed (vocabulary mismatch on generic queries). The misses informed my understanding of when reranking and query expansion become necessary.

**Architecture decisions.** I chose a modular monolith — single FastAPI service with clear module boundaries (ingestion, embedding, retrieval, generation, API). Routes are deliberately thin — they validate input and delegate to modules. All configuration flows through Pydantic BaseSettings. I chose ArXiv papers as test data intentionally: they're open access (no licensing issues), well-structured (good for learning chunking), and make the demo credible to a technical audience.

**MCP server for AI assistant integration.** I wrapped the entire RAG pipeline as an MCP (Model Context Protocol) server using the FastMCP SDK. This means Claude Code or any MCP-compatible AI assistant can query my knowledge base, ingest new documents, and search for information — all as tool calls. The MCP server imports the same backend modules directly (zero code duplication), and I designed multiple tools at different cost tiers: `query_knowledge_base` (generates a full cited answer, ~$0.0005), `search_chunks` (returns raw chunks without an LLM call, completely free), and `research` (automatically searches the web, ingests the most relevant pages, and generates a cited answer — all in one call). The `research` tool is the most interesting: it uses DuckDuckGo to find relevant pages, trafilatura to extract their content, and the full RAG pipeline to generate a grounded answer. The ingested pages persist in the knowledge base, so it gets smarter over time without any manual curation.

**Broader document support.** I extended the system beyond just ArXiv papers to support web pages (using trafilatura for intelligent content extraction), plain text, and markdown files. The key challenge was chunking: academic papers have numbered sections and bibliography sections to strip, but web pages and markdown have different structure. Rather than adding flags to the existing chunker, I wrote a separate `chunk_plain_document()` that uses markdown heading detection and paragraph-based splitting — keeping each chunker optimized for its domain with zero regression risk to the original PDF pipeline.

**What I'd change at scale:** swap to OpenAI embeddings or Cohere for better quality, add a cross-encoder reranker between retrieval and generation, use an async job queue for ingestion, add structured logging and latency metrics, and deploy Qdrant Cloud instead of local Docker.
