"""FastAPI routes for ingestion, retrieval, and service health."""

import asyncio
import os
import secrets
import tempfile
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile

from app.config import settings
from app.demo import demo_guard
from app.demo_seed import seed_demo_documents
from app.ingestion import ingest_arxiv_url, ingest_pdf, ingest_text_file, ingest_web_url
from app.models import (
    ChunkMetadata,
    DemoConfig,
    DocumentDetail,
    DocumentSummary,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceChunk,
)
from app.retrieval.search import get_collection_info, get_document, list_documents
from app.service import answer, store_chunks

router = APIRouter()
SUPPORTED_UPLOAD_SUFFIXES = {".pdf", ".txt", ".md"}


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key only when APP_API_KEY is configured."""
    if settings.app_api_key and (
        not x_api_key or not secrets.compare_digest(x_api_key, settings.app_api_key)
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def require_query_access(x_api_key: str | None = Header(default=None)) -> None:
    """Public demo queries are guarded separately; private mode uses APP_API_KEY."""
    if not settings.demo_mode:
        await require_api_key(x_api_key)


async def require_admin_key(
    x_admin_key: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    """Keep all writes private in demo mode without shipping a browser secret."""
    expected = settings.admin_api_key or settings.app_api_key
    provided = x_admin_key or x_api_key
    if expected and provided and secrets.compare_digest(provided, expected):
        return
    if not settings.demo_mode and not expected:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing admin key")


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


@router.get("/stats", dependencies=[Depends(require_query_access)])
async def collection_stats():
    try:
        return await asyncio.to_thread(get_collection_info)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Vector database is unavailable") from exc


@router.get("/demo/config", response_model=DemoConfig)
async def demo_config():
    return DemoConfig(
        enabled=settings.demo_mode,
        captcha_enabled=bool(settings.hcaptcha_secret),
        captcha_site_key=settings.hcaptcha_site_key if settings.demo_mode else "",
        queries_per_hour=settings.demo_queries_per_hour,
        queries_per_day=settings.demo_queries_per_day,
        max_selected_documents=settings.demo_max_selected_documents,
    )


@router.get(
    "/documents",
    response_model=list[DocumentSummary],
    dependencies=[Depends(require_query_access)],
)
async def document_catalog():
    try:
        return await asyncio.to_thread(list_documents)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not load document catalog") from exc


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentDetail,
    dependencies=[Depends(require_query_access)],
)
async def document_detail(doc_id: str):
    if len(doc_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    try:
        document = await asyncio.to_thread(get_document, doc_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not load document") from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post(
    "/ingest",
    response_model=IngestResponse,
    dependencies=[Depends(require_admin_key)],
)
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


@router.post(
    "/admin/seed",
    dependencies=[Depends(require_admin_key)],
)
async def seed_showcase():
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Showcase mode is disabled")
    return await seed_demo_documents()


@router.post(
    "/query",
    response_model=QueryResponse,
    dependencies=[Depends(require_query_access)],
)
async def query_knowledge_base(payload: QueryRequest, http_request: Request):
    if settings.demo_mode:
        if len(payload.question) > settings.demo_max_question_chars:
            raise HTTPException(
                status_code=422,
                detail=f"Demo questions are limited to {settings.demo_max_question_chars} characters",
            )
        if len(payload.doc_ids) > settings.demo_max_selected_documents:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Select at most "
                    f"{settings.demo_max_selected_documents} documents per question"
                ),
            )
        client_ip = http_request.client.host if http_request.client else "unknown"
        await demo_guard.verify_request(client_ip, payload.captcha_token)

    cache_key = demo_guard.cache_key(payload.question, payload.top_k, payload.doc_ids)
    if settings.demo_mode:
        cached = await demo_guard.get_cached(cache_key)
        if cached is not None:
            cached["cached"] = True
            cached["latency_ms"] = 0
            return QueryResponse.model_validate(cached)
        await demo_guard.reserve_generation()

    started = time.perf_counter()
    try:
        generated, results = await answer(
            payload.question,
            payload.top_k,
            payload.doc_ids or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Answer generation failed") from exc

    if not results:
        response = QueryResponse(
            answer="No relevant sources found in the knowledge base. Try ingesting some documents first.",
            sources=[],
            latency_ms=round((time.perf_counter() - started) * 1000),
            model=(
                settings.openai_model
                if settings.llm_provider == "openai"
                else settings.anthropic_model
            ),
        )
        if settings.demo_mode:
            await demo_guard.put_cached(cache_key, response.model_dump())
        return response

    sources = [
        SourceChunk(
            text=result["text"][:500],
            metadata=ChunkMetadata(**result["metadata"]),
            score=result["score"],
        )
        for result in results
    ]
    response = QueryResponse(
        answer=generated,
        sources=sources,
        latency_ms=round((time.perf_counter() - started) * 1000),
        model=(
            settings.openai_model
            if settings.llm_provider == "openai"
            else settings.anthropic_model
        ),
    )
    if settings.demo_mode:
        await demo_guard.put_cached(cache_key, response.model_dump())
    return response
