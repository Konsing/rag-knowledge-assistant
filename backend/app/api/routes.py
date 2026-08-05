"""FastAPI routes for ingestion, retrieval, and service health."""

import asyncio
import os
import secrets
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app.config import settings
from app.ingestion import ingest_arxiv_url, ingest_pdf, ingest_text_file, ingest_web_url
from app.models import ChunkMetadata, IngestResponse, QueryRequest, QueryResponse, SourceChunk
from app.retrieval.search import get_collection_info
from app.service import answer, store_chunks

router = APIRouter()
SUPPORTED_UPLOAD_SUFFIXES = {".pdf", ".txt", ".md"}


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key only when APP_API_KEY is configured."""
    if settings.app_api_key and (
        not x_api_key or not secrets.compare_digest(x_api_key, settings.app_api_key)
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def _save_upload(file: UploadFile) -> tuple[str, str]:
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, TXT, or Markdown file.",
        )

    data_dir = Path(settings.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    size = 0
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=data_dir, suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="Uploaded file is too large")
                tmp.write(block)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    if size == 0:
        assert temp_path is not None
        os.unlink(temp_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if suffix == ".pdf":
        assert temp_path is not None
        with open(temp_path, "rb") as uploaded:
            if uploaded.read(5) != b"%PDF-":
                os.unlink(temp_path)
                raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")
    assert temp_path is not None
    return temp_path, filename


@router.get("/health")
async def health_check():
    try:
        info = await asyncio.to_thread(get_collection_info)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc
    return {"status": "healthy", "collection": info["name"], "points_count": info["points_count"]}


@router.get("/stats", dependencies=[Depends(require_api_key)])
async def collection_stats():
    try:
        return await asyncio.to_thread(get_collection_info)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc


@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(require_api_key)])
async def ingest_document(
    file: UploadFile | None = File(None),
    arxiv_url: str | None = Form(None),
    url: str | None = Form(None),
):
    """Load, chunk, embed, and store exactly one document source."""
    arxiv_url = arxiv_url.strip() if arxiv_url else None
    url = url.strip() if url else None
    source_count = sum(value is not None for value in (file, arxiv_url, url))
    if source_count != 1:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one file upload, ArXiv URL, or web page URL",
        )

    temp_path: str | None = None
    try:
        if arxiv_url:
            chunks, filename = await ingest_arxiv_url(arxiv_url)
        elif url:
            chunks, filename = await ingest_web_url(url)
        else:
            assert file is not None
            temp_path, filename = await _save_upload(file)
            suffix = Path(filename).suffix.lower()
            if suffix in {".txt", ".md"}:
                chunks = await ingest_text_file(temp_path, filename)
            else:
                chunks = await ingest_pdf(temp_path, filename)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not fetch the remote document") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail="Could not process the uploaded document") from exc
    finally:
        if file is not None:
            await file.close()
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted; scanned PDFs require OCR before ingestion",
        )

    try:
        stored = await store_chunks(chunks)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not store document chunks") from exc

    doc_id = chunks[0]["metadata"]["doc_id"]
    return IngestResponse(
        doc_id=doc_id,
        filename=filename,
        num_chunks=stored,
        message=f"Successfully ingested {stored} chunks from {filename}",
    )


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(require_api_key)])
async def query_knowledge_base(request: QueryRequest):
    try:
        generated, results = await answer(request.question, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Answer generation failed") from exc

    if not results:
        return QueryResponse(
            answer="No relevant sources found in the knowledge base. Try ingesting some documents first.",
            sources=[],
        )

    sources = [
        SourceChunk(
            text=result["text"][:500],
            metadata=ChunkMetadata(**result["metadata"]),
            score=result["score"],
        )
        for result in results
    ]
    return QueryResponse(answer=generated, sources=sources)
