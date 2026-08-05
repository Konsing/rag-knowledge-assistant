import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.demo_seed import seed_demo_documents

logger = logging.getLogger(__name__)


async def _seed_showcase() -> None:
    try:
        result = await seed_demo_documents()
        logger.info("Showcase seed complete: %s", result)
    except Exception:
        logger.exception("Showcase auto-seed failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_task = None
    if settings.demo_mode and settings.demo_auto_seed:
        seed_task = asyncio.create_task(_seed_showcase())
        app.state.seed_task = seed_task
    yield
    if seed_task and not seed_task.done():
        seed_task.cancel()

app = FastAPI(
    title="RAG Knowledge Assistant",
    description="Retrieval-Augmented Generation system for research papers",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response

app.include_router(router, prefix="/api")
