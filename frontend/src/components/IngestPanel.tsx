import { useRef, useState } from "react";
import { ingestArxivUrl, ingestPdf, ingestWebUrl, getStats } from "../api/client";
import type { CollectionStats } from "../api/client";

type Tab = "arxiv" | "web" | "file";

export default function IngestPanel() {
  const [activeTab, setActiveTab] = useState<Tab>("arxiv");
  const [url, setUrl] = useState("");
  const [webUrl, setWebUrl] = useState("");
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
      // Silently fail
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
      setMessage({ text: err instanceof Error ? err.message : "Ingestion failed", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  async function handleWebUrlSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!webUrl.trim() || loading) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await ingestWebUrl(webUrl.trim());
      setMessage({ text: res.message, type: "success" });
      setWebUrl("");
      refreshStats();
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "Ingestion failed", type: "error" });
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
      setMessage({ text: err instanceof Error ? err.message : "Upload failed", type: "error" });
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (!stats) refreshStats();

  const tabs: { key: Tab; label: string }[] = [
    { key: "arxiv", label: "ArXiv Paper" },
    { key: "web", label: "Web Page" },
    { key: "file", label: "Upload File" },
  ];

  return (
    <div className="space-y-6">
      {/* Section label */}
      <div className="text-[13px] font-semibold text-[#777] uppercase tracking-[0.08em]">Ingest</div>

      {/* Nav items as sidebar links */}
      <div className="flex flex-col gap-1.5">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setMessage(null); }}
            className={`
              text-left px-4 py-2.5 rounded-lg text-[15px] transition-colors
              ${activeTab === tab.key
                ? "bg-[#222] text-[#ddd]"
                : "text-[#888] hover:text-[#bbb] hover:bg-[#1e1e1e]"
              }
            `}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active form */}
      <div className="min-h-[160px]">
        {activeTab === "arxiv" && (
          <form onSubmit={handleUrlSubmit} className="space-y-3 animate-fade-in">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://arxiv.org/abs/2301.08745"
              className="w-full bg-[#1e1e1e] border border-[#2a2a2a] rounded-lg px-4 py-3.5 text-[16px] text-[#eee] placeholder:text-[#666] focus:outline-none focus:border-[#444] transition-colors"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="w-full bg-[#eee] text-[#141414] px-4 py-3.5 rounded-lg text-[16px] font-semibold hover:bg-white disabled:bg-[#222] disabled:text-[#555] disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Ingesting...
                </span>
              ) : "Ingest Paper"}
            </button>
          </form>
        )}

        {activeTab === "web" && (
          <form onSubmit={handleWebUrlSubmit} className="space-y-3 animate-fade-in">
            <input
              type="text"
              value={webUrl}
              onChange={(e) => setWebUrl(e.target.value)}
              placeholder="https://en.wikipedia.org/wiki/..."
              className="w-full bg-[#1e1e1e] border border-[#2a2a2a] rounded-lg px-4 py-3.5 text-[16px] text-[#eee] placeholder:text-[#666] focus:outline-none focus:border-[#444] transition-colors"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !webUrl.trim()}
              className="w-full bg-[#eee] text-[#141414] px-4 py-3.5 rounded-lg text-[16px] font-semibold hover:bg-white disabled:bg-[#222] disabled:text-[#555] disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Ingesting...
                </span>
              ) : "Ingest Web Page"}
            </button>
          </form>
        )}

        {activeTab === "file" && (
          <div className="animate-fade-in">
            <label
              className={`
                flex flex-col items-center justify-center w-full h-44 border border-dashed rounded-lg cursor-pointer transition-colors
                ${loading
                  ? "border-[#2a2a2a] bg-[#1a1a1a] cursor-not-allowed"
                  : "border-[#444] hover:border-[#666] bg-[#1e1e1e]"
                }
              `}
            >
              <svg className="w-10 h-10 text-[#666] mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              <span className="text-[16px] text-[#999]">Drop file or click to browse</span>
              <span className="text-[14px] text-[#666] mt-1.5">PDF, TXT, or Markdown</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md"
                onChange={handleFileUpload}
                disabled={loading}
                className="hidden"
              />
            </label>
          </div>
        )}
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`rounded-lg px-4 py-3 text-[15px] animate-fade-in ${
            message.type === "success"
              ? "bg-[#1e1e1e] border border-[#2a2a2a] text-[#bbb]"
              : "bg-[#2a1515] border border-[#3a2020] text-[#f99]"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="mt-auto pt-4">
          <div className="bg-[#1e1e1e] border border-[#2a2a2a] rounded-lg px-4 py-3.5">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[14px] text-[#777]">Indexed</span>
              <span className="text-[14px] text-[#bbb] tabular-nums">{stats.points_count.toLocaleString()} chunks</span>
            </div>
            <div className="h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#eee] rounded-full transition-all duration-500"
                style={{ width: `${Math.min((stats.points_count / 500) * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
