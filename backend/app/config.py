from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: Literal["openai", "claude"] = "openai"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-sonnet-4-20250514"
    max_context_chars: int = Field(default=24_000, ge=4_000, le=100_000)

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_cloud_inference: bool = False
    collection_name: str = "research_papers"

    # Embeddings. Cloud inference keeps the public demo small enough for free hosts.
    embedding_provider: Literal["local", "qdrant_cloud"] = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Chunking
    chunk_size: int = Field(default=500, ge=50, le=4_000)
    chunk_overlap: int = Field(default=100, ge=0, le=1_000)

    # Retrieval
    top_k: int = Field(default=5, ge=1, le=10)
    score_threshold: float = Field(default=0.3, ge=-1.0, le=1.0)

    # Ingestion and network safety
    data_dir: Path = Path("data")
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    max_web_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    max_pdf_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    max_redirects: int = Field(default=5, ge=0, le=10)

    # API/MCP exposure. API authentication is opt-in for local development.
    app_api_key: str = ""
    admin_api_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = Field(default=8811, ge=1, le=65535)

    # Public showcase mode. Ingestion stays admin-only while querying is guarded.
    demo_mode: bool = False
    demo_auto_seed: bool = False
    demo_documents_file: Path = Path("demo_documents.json")
    demo_queries_per_hour: int = Field(default=10, ge=1, le=1_000)
    demo_queries_per_day: int = Field(default=100, ge=1, le=100_000)
    demo_max_question_chars: int = Field(default=500, ge=50, le=4_000)
    demo_cache_size: int = Field(default=100, ge=0, le=10_000)
    demo_max_selected_documents: int = Field(default=5, ge=1, le=20)
    hcaptcha_site_key: str = ""
    hcaptcha_secret: str = ""

    @model_validator(mode="after")
    def validate_chunking(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.embedding_provider == "qdrant_cloud":
            if not self.qdrant_url or not self.qdrant_api_key:
                raise ValueError(
                    "QDRANT_URL and QDRANT_API_KEY are required for Qdrant Cloud embeddings"
                )
            self.qdrant_cloud_inference = True
        if bool(self.hcaptcha_site_key) != bool(self.hcaptcha_secret):
            raise ValueError(
                "HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET must either both be set or both be empty"
            )
        if self.demo_mode and not (self.admin_api_key or self.app_api_key):
            raise ValueError("ADMIN_API_KEY is required when DEMO_MODE is enabled")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
