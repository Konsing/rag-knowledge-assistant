const BASE_URL = "/api";
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

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

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = 30_000,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(init.headers);
  if (API_KEY) headers.set("X-API-Key", API_KEY);

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
    const body = await response.text();
    let parsed: unknown = null;
    if (body) {
      try {
        parsed = JSON.parse(body);
      } catch {
        parsed = body;
      }
    }

    if (!response.ok) {
      const detail =
        typeof parsed === "object" && parsed !== null && "detail" in parsed
          ? String((parsed as { detail: unknown }).detail)
          : `Request failed with status ${response.status}`;
      throw new Error(detail);
    }
    return parsed as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out. The document or query may be too large.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export function healthCheck(): Promise<{ status: string }> {
  return apiRequest("/health");
}

export function getStats(): Promise<CollectionStats> {
  return apiRequest("/stats");
}

export function ingestArxivUrl(url: string): Promise<IngestResponse> {
  const form = new FormData();
  form.append("arxiv_url", url);
  return apiRequest("/ingest", { method: "POST", body: form }, 120_000);
}

export function ingestFile(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest("/ingest", { method: "POST", body: form }, 120_000);
}

export function ingestWebUrl(url: string): Promise<IngestResponse> {
  const form = new FormData();
  form.append("url", url);
  return apiRequest("/ingest", { method: "POST", body: form }, 120_000);
}

export function queryKnowledgeBase(question: string, topK = 5): Promise<QueryResponse> {
  return apiRequest(
    "/query",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
    },
    90_000,
  );
}
