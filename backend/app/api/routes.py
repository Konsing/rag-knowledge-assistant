"""
FastAPI routes — thin delegation layer.

Each endpoint validates input, calls the appropriate modules,
and returns a structured response. No business logic here.
"""

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.embedding.embedder import embed_query, embed_texts
from app.generation.llm_client import generate_answer
from app.ingestion import ingest_arxiv_url, ingest_pdf, ingest_text_file, ingest_web_url
from app.models import IngestResponse, QueryRequest, QueryResponse, SourceChunk, ChunkMetadata
from app.retrieval.search import get_collection_info, search, upsert_chunks

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/stats")
async def collection_stats():
    """Return stats about the vector collection."""
    return get_collection_info()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile | None = File(None),
    arxiv_url: str | None = Form(None),
    url: str | None = Form(None),
):
    """
    Ingest a document into the knowledge base.

    Accepts one of:
    - A file upload (PDF, .txt, or .md)
    - An ArXiv URL (arxiv_url field)
    - A web page URL (url field)

    Pipeline: load/fetch → chunk → embed → store in Qdrant
    """
    if not file and not arxiv_url and not url:
        raise HTTPException(
            status_code=400,
            detail="Provide a file upload, ArXiv URL, or web page URL",
        )

    try:
        if arxiv_url:
            chunks, filename = await ingest_arxiv_url(arxiv_url)
        elif url:
            chunks, filename = await ingest_web_url(url)
        else:
            # Save uploaded file to disk temporarily
            os.makedirs(DATA_DIR, exist_ok=True)
            suffix = os.path.splitext(file.filename)[1] or ".pdf"
            with tempfile.NamedTemporaryFile(dir=DATA_DIR, suffix=suffix, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            filename = file.filename

            # Route to appropriate pipeline based on file type
            if suffix.lower() in (".txt", ".md"):
                chunks = await ingest_text_file(tmp_path, filename)
            else:
                chunks = await ingest_pdf(tmp_path, filename)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not chunks:
        raise HTTPException(status_code=422, detail="No text could be extracted from the document")

    # Embed all chunks
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    # Store in Qdrant
    upsert_chunks(chunks, vectors)

    doc_id = chunks[0]["metadata"]["doc_id"]

    return IngestResponse(
        doc_id=doc_id,
        filename=filename,
        num_chunks=len(chunks),
        message=f"Successfully ingested {len(chunks)} chunks from {filename}",
    )


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    """
    Query the knowledge base and get a cited answer.

    Pipeline: embed question → search Qdrant → generate answer with Claude
    """
    # Embed the question
    query_vector = embed_query(request.question)

    # Retrieve top-k chunks
    results = search(query_vector, top_k=request.top_k)

    if not results:
        return QueryResponse(
            answer="No relevant sources found in the knowledge base. Try ingesting some documents first.",
            sources=[],
        )

    # Generate cited answer
    try:
        answer = generate_answer(request.question, results)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM generation failed: {str(e)}",
        )

    # Build response with source citations
    sources = [
        SourceChunk(
            text=r["text"][:500],  # Truncate for response size
            metadata=ChunkMetadata(**r["metadata"]),
            score=r["score"],
        )
        for r in results
    ]

    return QueryResponse(answer=answer, sources=sources)
