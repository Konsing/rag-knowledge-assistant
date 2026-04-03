const BASE_URL = "/api";

// --- Types mirroring backend Pydantic models ---

export interface ChunkMetadata {
  source_file: string;
  page_number: number;
  section_title: string;
  chunk_index: number;
  doc_id: string;
}

export interface SourceChunk {
  text: string;
  metadata: ChunkMetadata;
  score: number;
}

export interface IngestResponse {
  doc_id: string;
  filename: string;
  num_chunks: number;
  message: string;
}

export interface QueryResponse {
  answer: string;
  sources: SourceChunk[];
}

export interface CollectionStats {
  name: string;
  points_count: number;
}

// --- API functions ---

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function getStats(): Promise<CollectionStats> {
  const res = await fetch(`${BASE_URL}/stats`);
  return res.json();
}

export async function ingestArxivUrl(url: string): Promise<IngestResponse> {
  const form = new FormData();
  form.append("arxiv_url", url);

  const res = await fetch(`${BASE_URL}/ingest`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Ingestion failed");
  }

  return res.json();
}

export async function ingestPdf(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/ingest`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Ingestion failed");
  }

  return res.json();
}

export async function queryKnowledgeBase(
  question: string,
  topK: number = 5
): Promise<QueryResponse> {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Query failed");
  }

  return res.json();
}
