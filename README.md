# RAG Knowledge Assistant

A production-quality Retrieval-Augmented Generation system built **from scratch** — no LangChain, no LlamaIndex. Every layer (chunking, embedding, retrieval, generation) is hand-written for full understanding and control.

## What It Does

Upload ArXiv research papers (PDF or URL), and ask questions about them. The system retrieves relevant passages using vector similarity search and generates cited answers using an LLM (OpenAI or Claude, configurable).

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
                    ┌───────┴────────┐
                    │  Claude API    │
                    │  (Generation)  │
                    └────────────────┘
```

**Modular monolith** — single backend with clear module boundaries:

```
backend/app/
├── ingestion/    PDF loading, ArXiv fetching, text chunking
├── embedding/    sentence-transformers (all-MiniLM-L6-v2)
├── retrieval/    Qdrant cosine similarity search
├── generation/   Claude API + prompt templates
├── api/          FastAPI routes (thin delegation layer)
└── config.py     Centralized Pydantic Settings
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| PDF Extraction | PyMuPDF | Fast, handles complex layouts, page-level metadata |
| Embeddings | all-MiniLM-L6-v2 | 384-dim vectors, free, runs locally |
| Vector DB | Qdrant (Docker) | Free local mode, excellent SDK, metadata filtering |
| LLM | Claude API (Sonnet) | Strong instruction-following for citations |
| Backend | FastAPI | Async, auto OpenAPI docs, Pydantic integration |
| Frontend | React + Vite + Tailwind | Fast dev, modern stack |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Anthropic API key](https://console.anthropic.com/) for generation

## Quick Start

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd rag-knowledge-assistant

# 2. Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run everything
docker-compose up --build

# 4. Open the UI
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/docs
# Qdrant:    http://localhost:6333/dashboard
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/ingest` | Upload PDF or provide ArXiv URL |
| `POST` | `/api/query` | Ask a question, get cited answer |

### Ingest a paper

```bash
# Upload a PDF
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@paper.pdf"

# Or provide an ArXiv URL
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"arxiv_url": "https://arxiv.org/abs/2301.00001"}'
```

### Query the knowledge base

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the main findings?", "top_k": 5}'
```

## Project Structure

```
rag-knowledge-assistant/
├── docker-compose.yml          Orchestrates all services
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 FastAPI entry point
│   └── app/
│       ├── config.py           Pydantic Settings (.env loader)
│       ├── models.py           Shared request/response schemas
│       ├── ingestion/          PDF loading + chunking
│       ├── embedding/          Vector encoding
│       ├── retrieval/          Similarity search
│       ├── generation/         LLM + prompts
│       └── api/                Route handlers
├── frontend/
│   ├── Dockerfile
│   └── src/                    React + Tailwind UI
├── eval/
│   └── eval_retrieval.py       Retrieval quality evaluation
└── data/                       Local PDF storage (gitignored)
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

**What I'd change at scale:** swap to OpenAI embeddings or Cohere for better quality, add a cross-encoder reranker between retrieval and generation, use an async job queue for ingestion, add structured logging and latency metrics, and deploy Qdrant Cloud instead of local Docker.
