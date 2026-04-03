from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    source_file: str
    page_number: int
    section_title: str
    chunk_index: int
    doc_id: str


class IngestRequest(BaseModel):
    arxiv_url: str | None = None


class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    num_chunks: int
    message: str


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class SourceChunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
