const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "/api";
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

export interface ChunkMetadata {
  source_file: string;
  page_number: number;
  section_title: string;
  chunk_index: number;
  doc_id: string;
  title: string;
  source_url: string;
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
  latency_ms: number;
  cached: boolean;
  model: string;
}

export interface CollectionStats {
  name: string;
  points_count: number;
}

export interface DocumentSummary {
  doc_id: string;
  title: string;
  source_file: string;
  source_url: string;
  description: string;
  chunk_count: number;
  page_count: number;
  sections: string[];
  sample_questions: string[];
}

export interface DocumentChunk {
  text: string;
  metadata: ChunkMetadata;
}

export interface DocumentDetail extends DocumentSummary {
  chunks: DocumentChunk[];
}

export interface DemoConfig {
  enabled: boolean;
  captcha_enabled: boolean;
  captcha_site_key: string;
  queries_per_hour: number;
  queries_per_day: number;
  max_selected_documents: number;
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

export function getDemoConfig(): Promise<DemoConfig> {
  return apiRequest("/demo/config", {}, 90_000);
}

export function getDocuments(): Promise<DocumentSummary[]> {
  return apiRequest("/documents");
}

export function getDocument(docId: string): Promise<DocumentDetail> {
  return apiRequest(`/documents/${encodeURIComponent(docId)}`);
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

export function queryKnowledgeBase(
  question: string,
  topK = 5,
  docIds: string[] = [],
  captchaToken = "",
): Promise<QueryResponse> {
  return apiRequest(
    "/query",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        top_k: topK,
        doc_ids: docIds,
        captcha_token: captchaToken,
      }),
    },
    90_000,
  );
}
