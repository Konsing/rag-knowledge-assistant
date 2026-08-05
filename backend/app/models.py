from pydantic import BaseModel, Field, field_validator


class ChunkMetadata(BaseModel):
    source_file: str
    page_number: int
    section_title: str
    chunk_index: int
    doc_id: str
    title: str = ""
    source_url: str = ""


class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    num_chunks: int
    message: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    top_k: int = Field(default=5, ge=1, le=10)
    doc_ids: list[str] = Field(default_factory=list, max_length=20)
    captcha_token: str = Field(default="", max_length=4_096)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class SourceChunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    latency_ms: int = 0
    cached: bool = False
    model: str = ""


class DocumentSummary(BaseModel):
    doc_id: str
    title: str
    source_file: str
    source_url: str = ""
    description: str = ""
    chunk_count: int
    page_count: int
    sections: list[str] = Field(default_factory=list)
    sample_questions: list[str] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    text: str
    metadata: ChunkMetadata


class DocumentDetail(DocumentSummary):
    chunks: list[DocumentChunk]


class DemoConfig(BaseModel):
    enabled: bool
    captcha_enabled: bool
    captcha_site_key: str = ""
    queries_per_hour: int
    queries_per_day: int
    max_selected_documents: int
