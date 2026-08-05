import { useState } from "react";
import { getDocument } from "../api/client";
import type { DocumentDetail, DocumentSummary } from "../api/client";

interface Props {
  documents: DocumentSummary[];
  loading: boolean;
  selectedIds: string[];
  maxSelected: number;
  onSelectionChange: (ids: string[]) => void;
  onUseQuestion: (question: string) => void;
}

export default function DocumentLibrary({
  documents,
  loading,
  selectedIds,
  maxSelected,
  onSelectionChange,
  onUseQuestion,
}: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, DocumentDetail>>({});
  const [detailError, setDetailError] = useState<string | null>(null);

  function toggleSelected(docId: string) {
    if (selectedIds.includes(docId)) {
      onSelectionChange(selectedIds.filter((id) => id !== docId));
      return;
    }
    if (selectedIds.length < maxSelected) {
      onSelectionChange([...selectedIds, docId]);
    }
  }

  async function toggleDetails(docId: string) {
    if (expandedId === docId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(docId);
    setDetailError(null);
    if (!details[docId]) {
      try {
        const detail = await getDocument(docId);
        setDetails((current) => ({ ...current, [docId]: detail }));
      } catch (error) {
        setDetailError(error instanceof Error ? error.message : "Could not load chunks");
      }
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[13px] font-semibold text-[#777] uppercase tracking-[0.08em]">
          Document library
        </div>
        <p className="mt-2 text-[13px] leading-relaxed text-[#777]">
          Choose up to {maxSelected} curated papers. Open a paper to inspect the chunks stored in Qdrant.
        </p>
      </div>

      {loading && <p className="text-[14px] text-[#777]">Loading indexed documents…</p>}

      {!loading && documents.length === 0 && (
        <div className="rounded-lg border border-[#3a3020] bg-[#241f17] p-4 text-[14px] text-[#d2b77c]">
          The showcase corpus is still being prepared. An administrator can run the seed endpoint.
        </div>
      )}

      <div className="space-y-3">
        {documents.map((document) => {
          const selected = selectedIds.includes(document.doc_id);
          const detail = details[document.doc_id];
          const expanded = expandedId === document.doc_id;
          return (
            <article
              key={document.doc_id}
              className={`rounded-xl border p-4 transition-colors ${
                selected ? "border-[#555] bg-[#222]" : "border-[#2a2a2a] bg-[#1b1b1b]"
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => toggleSelected(document.doc_id)}
                  disabled={!selected && selectedIds.length >= maxSelected}
                  aria-label={`Use ${document.title} in retrieval`}
                  className="mt-1 h-4 w-4 accent-[#eee]"
                />
                <div className="min-w-0 flex-1">
                  <h2 className="text-[15px] font-medium leading-snug text-[#ddd]">
                    {document.title}
                  </h2>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-[#777]">
                    {document.description || document.source_file}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-[#666]">
                    <span>{document.chunk_count} chunks</span>
                    {document.page_count > 0 && <span>{document.page_count} pages</span>}
                  </div>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-3 border-t border-[#2a2a2a] pt-3 text-[13px]">
                <button
                  type="button"
                  onClick={() => void toggleDetails(document.doc_id)}
                  className="text-[#999] hover:text-[#eee]"
                  aria-expanded={expanded}
                >
                  {expanded ? "Hide chunks" : "Inspect chunks"}
                </button>
                {document.source_url && (
                  <a
                    href={document.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#777] hover:text-[#bbb]"
                  >
                    Original source ↗
                  </a>
                )}
              </div>

              {document.sample_questions.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {document.sample_questions.slice(0, 2).map((question) => (
                    <button
                      key={question}
                      type="button"
                      onClick={() => onUseQuestion(question)}
                      className="block w-full rounded-md bg-[#191919] px-3 py-2 text-left text-[12px] leading-relaxed text-[#888] hover:text-[#ccc]"
                    >
                      “{question}”
                    </button>
                  ))}
                </div>
              )}

              {expanded && (
                <div className="mt-3 max-h-72 space-y-2 overflow-y-auto border-t border-[#2a2a2a] pt-3 scrollbar-thin">
                  {!detail && !detailError && <p className="text-[13px] text-[#666]">Loading chunks…</p>}
                  {detailError && <p className="text-[13px] text-[#f99]">{detailError}</p>}
                  {detail?.chunks.map((chunk) => (
                    <div key={chunk.metadata.chunk_index} className="rounded-lg bg-[#161616] p-3">
                      <div className="mb-1.5 text-[11px] uppercase tracking-wide text-[#666]">
                        Chunk {chunk.metadata.chunk_index + 1}
                        {chunk.metadata.page_number > 0 && ` · p.${chunk.metadata.page_number}`}
                        {chunk.metadata.section_title && ` · ${chunk.metadata.section_title}`}
                      </div>
                      <p className="text-[12px] leading-relaxed text-[#999]">{chunk.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>

      <div className="rounded-lg border border-[#2a2a2a] bg-[#1e1e1e] px-4 py-3 text-[13px] text-[#777]">
        {selectedIds.length} of {documents.length} documents selected
      </div>
    </div>
  );
}
