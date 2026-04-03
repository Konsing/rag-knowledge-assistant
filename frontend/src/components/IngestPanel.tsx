import { useRef, useState } from "react";
import { ingestArxivUrl, ingestPdf, getStats } from "../api/client";
import type { CollectionStats } from "../api/client";

export default function IngestPanel() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{
    text: string;
    type: "success" | "error";
  } | null>(null);
  const [stats, setStats] = useState<CollectionStats | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function refreshStats() {
    try {
      const s = await getStats();
      setStats(s);
    } catch {
      // Silently fail — stats are informational
    }
  }

  async function handleUrlSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || loading) return;

    setLoading(true);
    setMessage(null);

    try {
      const res = await ingestArxivUrl(url.trim());
      setMessage({ text: res.message, type: "success" });
      setUrl("");
      refreshStats();
    } catch (err) {
      setMessage({
        text: err instanceof Error ? err.message : "Ingestion failed",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setMessage(null);

    try {
      const res = await ingestPdf(file);
      setMessage({ text: res.message, type: "success" });
      refreshStats();
    } catch (err) {
      setMessage({
        text: err instanceof Error ? err.message : "Upload failed",
        type: "error",
      });
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // Load stats on first render
  if (!stats) refreshStats();

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Ingest Documents
        </h2>
        {stats && (
          <p className="text-xs text-gray-400 mt-1">
            {stats.points_count} chunks indexed
          </p>
        )}
      </div>

      {/* ArXiv URL input */}
      <form onSubmit={handleUrlSubmit} className="space-y-2">
        <label className="block text-sm text-gray-600">ArXiv URL</label>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://arxiv.org/abs/2301.08745"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Ingesting..." : "Ingest Paper"}
        </button>
      </form>

      {/* Divider */}
      <div className="flex items-center gap-2">
        <div className="flex-1 border-t border-gray-200" />
        <span className="text-xs text-gray-400">or</span>
        <div className="flex-1 border-t border-gray-200" />
      </div>

      {/* PDF upload */}
      <div>
        <label className="block text-sm text-gray-600 mb-2">Upload PDF</label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          disabled={loading}
          className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 disabled:opacity-50"
        />
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`rounded-lg p-3 text-sm ${
            message.type === "success"
              ? "bg-green-50 border border-green-200 text-green-700"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}
