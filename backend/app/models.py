from pydantic import BaseModel, Field, field_validator


class ChunkMetadata(BaseModel):
    source_file: str
    page_number: int
    section_title: str
    chunk_index: int
    doc_id: str


class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    num_chunks: int
    message: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    top_k: int = Field(default=5, ge=1, le=10)

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
