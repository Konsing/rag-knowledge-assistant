from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"  # "openai" or "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    collection_name: str = "research_papers"

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 100

    # Retrieval
    top_k: int = 5
    score_threshold: float = 0.3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
