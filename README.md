# RAG Knowledge Assistant

A production-quality Retrieval-Augmented Generation system built **from scratch** — no LangChain, no LlamaIndex. Every layer (chunking, embedding, retrieval, generation) is hand-written for full understanding and control.

The current implementation includes guarded public-URL ingestion, bounded uploads and LLM context, idempotent vector writes, isolated auto-research retrieval, optional API-key protection, a shared async API/MCP service layer, production Nginx frontend serving, Docker health checks, and backend/frontend regression tests.

It also includes an opt-in **public showcase mode**: visitors can browse a curated document library, select the papers used for retrieval, ask guarded anonymous questions, and inspect the ranked chunks, scores, citations, model, latency, and cache status behind each answer. In showcase mode, ingestion and corpus seeding remain administrator-only.

## What It Does

Upload documents — ArXiv papers, PDFs, web pages, or text files — and ask questions about them. The system retrieves relevant passages using vector similarity search and generates cited answers using an LLM (OpenAI or Claude, configurable).

Also available as an **MCP server** with auto-research tools — AI assistants like Claude Code can search ArXiv or the web, ingest relevant sources, and get cited answers without any manual document management.

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

The system retrieves the relevant sections, cites them by number, and refuses to hallucinate — if the sources don't contain an answer, it says so.

### Example: Web Page Ingestion

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

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ React/Nginx  │────▶│   FastAPI    │────▶│   Qdrant     │
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
├── main.py           FastAPI entry point
└── app/
    ├── ingestion/    PDF, ArXiv, web pages, text/markdown loading + chunking
    │   ├── pdf_loader.py       PyMuPDF text extraction with page tracking
    │   ├── arxiv_fetcher.py    ArXiv PDF downloader
    │   ├── arxiv_search.py     ArXiv API search (free, no key needed)
    │   ├── web_loader.py       Web page fetcher (trafilatura extraction)
    │   ├── web_search.py       DuckDuckGo search (free, no key needed)
    │   ├── text_loader.py      Plain text / markdown loader
    │   └── chunker.py          Section-aware + plain document chunking
    ├── embedding/    sentence-transformers (all-MiniLM-L6-v2, 384-dim)
    ├── retrieval/    Qdrant cosine similarity search
    ├── generation/   LLM client (OpenAI/Claude) + prompt templates
    ├── api/          FastAPI routes (thin delegation layer)
    ├── models.py     Shared Pydantic request/response schemas
    └── config.py     Centralized Pydantic Settings (.env loader)
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| PDF Extraction | PyMuPDF | Fast, handles complex layouts, page-level metadata |
| Embeddings | all-MiniLM-L6-v2 | 384-dim vectors, free, runs locally |
| Vector DB | Qdrant (Docker) | Free local mode, excellent SDK, metadata filtering |
| Web Scraping | trafilatura | Extracts article text, strips boilerplate automatically |
| Web Search | DuckDuckGo (duckduckgo-search) | Free, no API key, used by auto-research |
| Academic Search | ArXiv API | Free, no API key, relevance-sorted paper search |
| MCP Server | FastMCP (MCP SDK) | Exposes RAG as tools for AI assistants |
| LLM | OpenAI GPT-4o-mini / Claude Sonnet | Configurable; strong instruction-following for citations |
| Backend | FastAPI | Async, auto OpenAPI docs, Pydantic integration |
| Frontend | React + Vite + Tailwind | Fast dev, modern stack |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An **OpenAI API key** (GPT-4o-mini, ~$0.0005/query) or **Anthropic API key** (Claude Sonnet)
- Optional: Node.js 20+ and npm for frontend development and unit tests outside Docker

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/Konsing/rag-knowledge-assistant.git
cd rag-knowledge-assistant

# 2. Set up environment
cp .env.example .env
# Edit .env — add your API key and set LLM_PROVIDER to "openai" or "claude"

# 3. Build and start everything in the background
docker compose up --build -d

# 4. Confirm the services started
docker compose ps

# 5. Open the UI
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/docs
# Qdrant:    http://localhost:6333/dashboard
# MCP:       http://localhost:8811/mcp (for AI assistant integration)
```

The first ingestion or query may take longer while the local embedding model downloads and loads. Follow logs with `docker compose logs -f`; rebuild after backend, dependency, environment, or production frontend changes with `docker compose up --build -d`. Stop the application with `docker compose down`. Qdrant vectors and downloaded documents persist in `qdrant_storage/` and `data/`; `docker compose down` does not delete them.

### Configuration

The most commonly changed `.env` values are:

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `openai` or `claude` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Key for the selected generation provider |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunk sizing; overlap must be smaller than chunk size |
| `TOP_K` / `SCORE_THRESHOLD` | Retrieval count and similarity cutoff |
| `MAX_UPLOAD_BYTES` / `MAX_WEB_BYTES` / `MAX_PDF_BYTES` | Ingestion safety limits |
| `APP_API_KEY` / `VITE_API_KEY` | Optional matching keys for local API protection |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API |
| `DEMO_MODE` / `ADMIN_API_KEY` | Enable public query-only mode while keeping writes private |
| `DEMO_QUERIES_PER_HOUR` / `DEMO_QUERIES_PER_DAY` | Anonymous per-client and global generation caps |
| `HCAPTCHA_SITE_KEY` / `HCAPTCHA_SECRET` | Optional hCaptcha Basic bot verification |
| `EMBEDDING_PROVIDER` | `local` or free Qdrant Cloud inference for the slim hosted API |

When `VITE_API_KEY` changes, rebuild the frontend image. It is embedded in the browser bundle and is therefore only a local access deterrent, not a substitute for user authentication.

## Supported Document Types

| Source | How to ingest | Chunking strategy |
|--------|---------------|-------------------|
| ArXiv papers | Paste URL in UI or API (`arxiv_url` field) | Section-aware (detects numbered sections, ALL-CAPS headers), strips references |
| PDF files | Upload in UI or API (`file` field) | Same as ArXiv — section-aware with page tracking |
| Web pages | Paste URL in UI or API (`url` field) | Markdown heading detection, paragraph fallback |
| Text files (.txt) | Upload in UI or API | Paragraph-based splitting |
| Markdown files (.md) | Upload in UI or API | Markdown heading detection (`#`, `##`, `###`) |

In the local stack, all sources go through the same pipeline after chunking: embed locally with sentence-transformers → store in Qdrant → available for retrieval. That local embedding and storage path has no metered service charge. The hosted showcase currently uses Qdrant Cloud's free cluster and free MiniLM inference; those vendor terms can change. LLM answer generation remains usage-billed by OpenAI or Anthropic.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Collection stats (chunk count) |
| `POST` | `/api/ingest` | Upload file (PDF/txt/md), ArXiv URL, or web URL |
| `POST` | `/api/query` | Ask a question, get cited answer |
| `GET` | `/api/demo/config` | Public UI mode and limit configuration |
| `GET` | `/api/documents` | Browse indexed documents in showcase mode |
| `GET` | `/api/documents/{doc_id}` | Inspect one document and its stored chunks |
| `POST` | `/api/admin/seed` | Idempotently seed the curated demo corpus (admin only) |

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

If `APP_API_KEY` is configured, add `-H "X-API-Key: your-key"` to stats, ingestion, and query requests. Do not add it to the health request.

## MCP Server (AI Assistant Integration)

The RAG pipeline is also available as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server, so AI assistants like Claude Code can query your knowledge base as a tool — no copy-pasting, no browser needed.

### How it works

The MCP server runs as a separate Docker service that imports the same backend modules directly. When Claude Code calls a tool like `research_papers`, the MCP server searches ArXiv, downloads relevant papers, chunks and embeds them, stores them in Qdrant, and generates a cited answer — all in a single tool call. The knowledge base grows automatically with each research query.

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
| `research_papers` | **Auto-research**: searches ArXiv, ingests relevant papers, answers the question | ~$0.0005 |
| `research` | **Auto-research**: searches the web, ingests relevant pages, answers the question | ~$0.0005 |
| `query_knowledge_base` | Get a cited answer from already-ingested documents | ~$0.0005 |
| `search_chunks` | Find relevant chunks without LLM generation | Free |
| `ingest_arxiv` | Add a specific ArXiv paper to the knowledge base | Free |
| `ingest_web_page` | Add a web page to the knowledge base | Free |
| `get_stats` | Check how many chunks are indexed | Free |

The two `research` tools are the most powerful — they combine search, ingestion, and RAG querying into a single call:
- **`research_papers`** searches ArXiv for academic papers and ingests them with section-aware chunking optimized for academic content. Best for scientific and technical questions.
- **`research`** searches DuckDuckGo for web pages and ingests them. Best for general knowledge, current events, and non-academic topics.

You don't need to manually find and ingest anything. Just ask a question and the right tool handles everything. All ingested content persists in the knowledge base, so future queries on the same topic are instant.

`search_chunks` is a free alternative to `query_knowledge_base` — it returns raw document chunks without calling the LLM, so the AI assistant can decide whether it needs a full generated answer or just wants to look up a fact.

### Example: Auto-Research in Action

I asked Claude Code: **"Research what transformer attention mechanisms are and how they work"**

The `research_papers` tool automatically searched ArXiv, found 3 relevant papers, downloaded and ingested all of them, then answered the question — all in a single tool call:

```
Papers found and ingested:
  - Dilated Neighborhood Attention Transformer (2209.15001) — 30 chunks
  - Transformer-based Personalized Attention Mechanism (2206.03003) — 41 chunks
  - Mask-Attention-Free Transformer for 3D Instance Segmentation (2309.01692) — 28 chunks
```

**Cited answer returned:**

> Transformer attention mechanisms are techniques used within the Transformer architecture
> that allow the model to focus on different parts of the input data when making predictions.
> They calculate attention weights which indicate the relevance of each part of the input
> to the output, facilitating the understanding of relationships within the data.
>
> 1. **Exploratory Attention**: Derived from parts of the pathological specimen that need to
>    be observed. It helps in identifying which specific sections of the image are important
>    for diagnosis.
>
> 2. **Explanatory Attention**: Relates to the classification subtypes of the specimens,
>    providing context about how different features contribute to the overall classification.
>
> The Transformer utilizes a mechanism that can compute these attention weights for each part
> of the input, allowing it to handle multimodal information. For instance, it can assess
> relationships between image patches and clinical records, enhancing personalized attention
> based on clinical data [1][5].
>
> *Sources: 2206.03003.pdf p.5 (score 0.59), 2209.15001.pdf p.7 (score 0.53), 2309.01692.pdf p.2 (score 0.52)*

The entire flow — ArXiv search, PDF download, section-aware chunking, embedding, Qdrant storage, retrieval, LLM generation — happened in a single tool call. The 99 ingested chunks now persist in the knowledge base, so future questions about attention mechanisms are answered instantly without re-downloading anything.

### Other MCP tool examples

> "What are the latest developments in quantum computing?"

Claude Code calls `research`, which searches DuckDuckGo, ingests the top web pages, and returns a cited answer.

> "Use the knowledge base to look up what retrieval augmented generation is"

Claude Code calls `query_knowledge_base` and returns a cited answer from already-ingested documents.

> "Ingest this ArXiv paper: https://arxiv.org/abs/2301.08745"

Claude Code calls `ingest_arxiv`, which downloads, chunks, embeds, and stores the paper.

### Alternative: stdio transport

If you want to run the MCP server without Docker (e.g., directly on your machine), you can use stdio transport:

```bash
claude mcp add -e QDRANT_HOST=localhost -e QDRANT_PORT=6333 \
  rag-knowledge-base -- python backend/mcp_server.py --transport stdio
```

This requires Qdrant running locally and Python dependencies installed on the host.

## Safety and Runtime Behavior

- Docker ports bind to `127.0.0.1` by default. Put an authenticated TLS reverse proxy in front of the services before exposing them remotely.
- Compose serves the compiled frontend through unprivileged Nginx. Source changes require `docker compose up --build`; use `npm run dev` for frontend hot reload.
- Set `APP_API_KEY` and the matching `VITE_API_KEY` to require `X-API-Key` on stats, ingestion, and query API calls. Health remains public for container probes.
- Web ingestion accepts public HTTP(S) destinations only, revalidates redirects, rejects private/link-local/reserved addresses, and caps downloaded content at 5 MB.
- Uploads must be exactly one PDF, TXT, or Markdown file and are capped at 25 MB. PDF signatures are validated; scanned PDFs still require an external OCR step.
- Identical source content receives stable document and vector IDs, so retrying the same ingestion replaces those vector points instead of growing duplicates.
- Auto-research answers are filtered to the documents ingested by that tool call; unrelated existing collection content is excluded.
- The local embedding model is loaded lazily on the first ingest or query. The first call can therefore take longer while the model cache is populated.
- Showcase mode keeps ingestion behind `X-Admin-Key`, supports optional server-verified hCaptcha, limits requests per client, stores a global daily generation counter in Qdrant, and caches repeated questions. The public browser never receives an LLM, Qdrant, hCaptcha secret, or administrator key.

## Public Showcase Deployment

The repository includes a no-monthly-hosting-cost deployment path using Vercel Hobby for the static frontend, Render Free for the slim FastAPI image, Qdrant Cloud Free for vector storage and free `all-MiniLM-L6-v2` inference, and hCaptcha Basic for bot protection. OpenAI or Anthropic answer generation is still usage-billed, so configure a dedicated project key and a provider-side budget limit.

`DEMO_MODE` is a backend environment variable. For local use, copy `.env.example` to the repository-root `.env` and set `DEMO_MODE=true`; the hosted Render configuration already sets it to true in `render.yaml`. Do not add it to Vercel.

Free plans are controlled by their vendors and cannot be guaranteed forever. Render currently cold-starts free services after inactivity, and Qdrant may suspend or eventually delete an inactive free cluster. The application therefore keeps the deployment portable and the curated corpus reproducible through `backend/demo_documents.json` and the idempotent seed operation.

See [docs/SHOWCASE_DEPLOYMENT.md](docs/SHOWCASE_DEPLOYMENT.md) for account creation, environment variables, deployment, seeding, security checks, cold-start expectations, and interview-day preparation.

## Tests and Evaluation

Run the test suites from the repository root after creating `.env`:

```bash
# Backend unit, API, security, retrieval, service, demo, and MCP tests (52 tests)
docker compose run --rm --no-deps backend pytest -q

# Frontend component tests (4 tests; requires Node.js 20+)
cd frontend
npm ci
npm test

# Type-check and produce the same frontend bundle used by Docker
npm run build
cd ..

# Validate Compose and build all production images
docker compose config --quiet
docker compose build

# Smoke-test a running stack
curl --fail http://localhost:8000/api/health
curl --fail http://localhost:5173/api/health

# Corpus-specific retrieval hit-rate evaluation
docker compose exec backend python eval/eval_retrieval.py \
  --doc-id YOUR_FIXTURE_DOC_ID --min-hit-rate 0.7
```

The backend tests do not require a live Qdrant instance because external services are isolated in unit tests. The retrieval evaluation does require a running stack and an already-ingested matching fixture document. Its metric is hit rate at *k*: a question is a hit when at least one expected term appears in the retrieved top-*k*. It is a lightweight retrieval regression signal, not precision or end-to-end answer-quality scoring.

For a quick manual functional test, open `http://localhost:5173`, upload a small PDF/TXT/Markdown file, wait for the ingestion result, and ask a question whose answer appears in that file. Confirm that the answer includes expandable source cards with the expected document, page/section metadata, and similarity scores.

## Project Structure

```
rag-knowledge-assistant/
├── docker-compose.yml          Orchestrates all services (Qdrant, backend, frontend, MCP)
├── render.yaml                 Render Free API deployment blueprint
├── .env.example                Environment variables template
├── .mcp.json                   Claude Code MCP server configuration
├── docs/
│   └── SHOWCASE_DEPLOYMENT.md  Guarded public-demo deployment runbook
├── backend/
│   ├── Dockerfile
│   ├── Dockerfile.demo         Slim hosted image (cloud embeddings, no PyTorch)
│   ├── demo_documents.json     Reproducible curated showcase corpus
│   ├── requirements-demo.txt   Slim hosted dependency set
│   ├── requirements.txt
│   ├── main.py                 FastAPI entry point
│   ├── mcp_server.py           MCP server entry point (7 tools)
│   ├── tests/                  Unit, API, security, and orchestration tests
│   └── app/
│       ├── config.py           Pydantic Settings (.env loader)
│       ├── demo.py             CAPTCHA, limits, daily cap, and response cache
│       ├── demo_seed.py        Idempotent curated-corpus seeding
│       ├── models.py           Shared request/response schemas
│       ├── service.py          Shared async API/MCP orchestration
│       ├── ingestion/          PDF, ArXiv, web, text/markdown loading + chunking
│       │   ├── pdf_loader.py       PyMuPDF text extraction
│       │   ├── arxiv_fetcher.py    ArXiv PDF downloader
│       │   ├── arxiv_search.py     ArXiv API search
│       │   ├── web_loader.py       Web page fetcher (trafilatura)
│       │   ├── web_search.py       DuckDuckGo search
│       │   ├── url_safety.py       Public URL/DNS/redirect validation
│       │   ├── text_loader.py      Plain text / markdown loader
│       │   └── chunker.py          Section-aware + plain chunking
│       ├── embedding/          Vector encoding (sentence-transformers)
│       ├── retrieval/          Qdrant cosine similarity search
│       ├── generation/         LLM client + prompt templates
│       └── api/                Route handlers
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf              Production SPA serving + /api proxy
│   ├── package-lock.json       Reproducible frontend dependencies
│   ├── vercel.json             Static hosting and browser security headers
│   └── src/
│       ├── App.tsx             Local and showcase workspace layout
│       ├── api/client.ts       API client (ingest, query, catalog, demo config)
│       └── components/
│           ├── ChatWindow.tsx   Chat interface with markdown rendering
│           ├── DocumentLibrary.tsx Curated corpus and chunk inspector
│           ├── HCaptcha.tsx     Public-demo bot challenge
│           ├── IngestPanel.tsx   Document ingestion sidebar
│           └── MessageBubble.tsx Individual message display
├── eval/
│   └── eval_retrieval.py       Retrieval quality evaluation (10 test questions)
└── data/                       Local document storage (gitignored)
```

## What Would Change in Production

- **Embeddings:** OpenAI `text-embedding-3-small` or Cohere for better quality
- **Chunking:** Semantic chunking using embedding similarity, not just text boundaries
- **Reranking:** Cross-encoder reranker between retrieval and generation
- **Vector DB:** Managed Qdrant Cloud or Pinecone for scale + backups
- **Auth:** Replace the optional single API key with per-user OAuth/JWT and authorization
- **Ingestion:** Async job queue (Celery/Redis) for large batch processing
- **Observability:** Structured logging, latency metrics, retrieval quality monitoring
- **Streaming:** Server-sent events for real-time answer generation

## What I Built and Why

I built every layer of this RAG system from scratch — no LangChain, no LlamaIndex — because I wanted to deeply understand how retrieval-augmented generation actually works under the hood.

**Custom ingestion pipeline.** I wrote the PDF text extraction (PyMuPDF), the ArXiv URL fetcher, and a section-aware text chunker. The chunker uses regex-based section header detection tuned for academic papers, with paragraph-level fallback splitting and configurable overlap. I iterated on the section detection against real ArXiv papers — the first version matched table headers as sections, so I tightened the patterns to only accept numbered sections and ALL-CAPS headers within reasonable bounds. This kind of iterative refinement against real data is how production chunking works.

**Hand-rolled embedding and retrieval.** I use sentence-transformers (all-MiniLM-L6-v2) to encode chunks into 384-dimensional vectors and store them in Qdrant with full metadata payloads. The same model embeds both documents and queries — this is critical because cosine similarity only works within the same vector space. I chose cosine over euclidean distance because for text embeddings, direction matters more than magnitude.

**Citation-grounded generation.** I engineered the prompt to instruct the LLM to answer only from the provided context and cite sources using [1], [2] notation. Each retrieved chunk is labeled with its source file, page number, and section title. If the retrieval returns nothing relevant, the system says "I don't have enough information" rather than hallucinating — this is a deliberate design choice. The generation layer supports both OpenAI (GPT-4o-mini) and Claude (Sonnet), configurable via a single environment variable.

**Quantitative evaluation.** I wrote an evaluation harness with 10 test questions and expected section keywords. Its baseline is a 70% retrieval hit rate at five results—not precision—and it can be restricted to a fixture document and fail CI below a configured threshold. The misses identify where reranking and query expansion become necessary.

**Architecture decisions.** I chose a modular monolith — single FastAPI service with clear module boundaries (ingestion, embedding, retrieval, generation, API). Routes are deliberately thin — they validate input and delegate to modules. All configuration flows through Pydantic BaseSettings. I chose ArXiv papers as test data intentionally: they're open access (no licensing issues), well-structured (good for learning chunking), and make the demo credible to a technical audience.

**MCP server for AI assistant integration.** I wrapped the entire RAG pipeline as an MCP (Model Context Protocol) server using the FastMCP SDK. This means Claude Code or any MCP-compatible AI assistant can query my knowledge base, ingest new documents, and search for information — all as tool calls. The MCP server imports the same backend modules directly (zero code duplication), and I designed multiple tools at different cost tiers: `query_knowledge_base` (generates a full cited answer, ~$0.0005), `search_chunks` (returns raw chunks without an LLM call, completely free), and two auto-research tools that combine search, ingestion, and RAG into a single call.

**Auto-research tools.** I built two research tools that make the knowledge base self-expanding. `research_papers` searches ArXiv's free API for academic papers matching a question, downloads and ingests the top results with section-aware chunking optimized for academic content, then queries only those newly ingested documents for a cited answer. `research` does the same for general web content, with public-network URL validation and trafilatura extraction. Ingested content persists in Qdrant for future direct queries, while each research answer remains isolated from unrelated older documents.

**Broader document support.** I extended the system beyond just ArXiv papers to support web pages (using trafilatura for intelligent content extraction), plain text, and markdown files. The key challenge was chunking: academic papers have numbered sections and bibliography sections to strip, but web pages and markdown have different structure. Rather than adding flags to the existing chunker, I wrote a separate `chunk_plain_document()` that uses markdown heading detection and paragraph-based splitting — keeping each chunker optimized for its domain with zero regression risk to the original PDF pipeline.

**What I'd change at scale:** swap to OpenAI embeddings or Cohere for better quality, add a cross-encoder reranker between retrieval and generation, use an async job queue for ingestion, add structured logging and latency metrics, and deploy Qdrant Cloud instead of local Docker.
