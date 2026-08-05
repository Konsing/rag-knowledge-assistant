import { useEffect, useState } from "react";
import { getDemoConfig, getDocuments } from "./api/client";
import type { DemoConfig, DocumentSummary } from "./api/client";
import ChatWindow from "./components/ChatWindow";
import DocumentLibrary from "./components/DocumentLibrary";
import IngestPanel from "./components/IngestPanel";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [demoConfig, setDemoConfig] = useState<DemoConfig | null>(null);
  const [configLoaded, setConfigLoaded] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [loadNonce, setLoadNonce] = useState(0);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [draftQuestion, setDraftQuestion] = useState<{ text: string; nonce: number } | null>(null);

  useEffect(() => {
    let active = true;
    async function loadShowcase() {
      setWorkspaceError(null);
      setConfigLoaded(false);
      try {
        const config = await getDemoConfig();
        if (!active) return;
        setDemoConfig(config);
        if (config.enabled) {
          const indexedDocuments = await getDocuments();
          if (!active) return;
          setDocuments(indexedDocuments);
          setSelectedDocIds(
            indexedDocuments.slice(0, config.max_selected_documents).map((document) => document.doc_id),
          );
        }
      } catch (error) {
        if (active) {
          setDemoConfig(null);
          setWorkspaceError(error instanceof Error ? error.message : "Could not reach the API");
        }
      } finally {
        if (active) {
          setDocumentsLoading(false);
          setConfigLoaded(true);
        }
      }
    }
    void loadShowcase();
    return () => { active = false; };
  }, [loadNonce]);

  const showcaseEnabled = demoConfig?.enabled === true;

  return (
    <div className="h-[100dvh] flex flex-col bg-[#191919] text-[#eee]">
      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-20 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={`
            w-[320px] flex-shrink-0 bg-[#141414] border-r border-[#2a2a2a] overflow-y-auto scrollbar-thin
            flex flex-col
            transition-transform duration-200 ease-in-out
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
            md:translate-x-0
            fixed md:relative inset-y-0 left-0 z-30 md:z-0
          `}
        >
          {/* Sidebar header */}
          <div className="px-6 pt-6 pb-2">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-[18px] font-semibold text-[#eee] tracking-[-0.01em]">RAG Assistant</h1>
                <p className="text-[14px] text-[#777] mt-0.5">
                  {showcaseEnabled ? "retrieval showcase" : "knowledge base"}
                </p>
              </div>
              {/* Mobile close */}
              <button
                onClick={() => setSidebarOpen(false)}
                className="md:hidden p-1.5 rounded-md hover:bg-[#222] transition-colors"
                aria-label="Close sidebar"
              >
                <svg className="w-5 h-5 text-[#777]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <div className="flex-1 px-6 py-5">
            {!configLoaded ? (
              <p className="text-[14px] text-[#777]">Loading workspace…</p>
            ) : workspaceError ? (
              <div className="rounded-lg border border-[#3a3020] bg-[#241f17] p-4 text-[14px] text-[#d2b77c]">
                <p>The free API may be waking up. {workspaceError}</p>
                <button
                  type="button"
                  onClick={() => setLoadNonce((value) => value + 1)}
                  className="mt-3 rounded-md bg-[#eee] px-3 py-2 font-medium text-[#141414]"
                >
                  Retry connection
                </button>
              </div>
            ) : showcaseEnabled && demoConfig ? (
              <DocumentLibrary
                documents={documents}
                loading={documentsLoading}
                selectedIds={selectedDocIds}
                maxSelected={demoConfig.max_selected_documents}
                onSelectionChange={setSelectedDocIds}
                onUseQuestion={(text) => setDraftQuestion({ text, nonce: Date.now() })}
              />
            ) : (
              <IngestPanel />
            )}
          </div>
        </aside>

        {/* Chat area */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#191919]">
          {/* Mobile header */}
          <div className="md:hidden flex items-center gap-3 px-6 py-4 border-b border-[#2a2a2a]">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-md hover:bg-[#222] transition-colors"
              aria-label="Open sidebar"
            >
              <svg className="w-6 h-6 text-[#aaa]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>
            <span className="text-[17px] font-semibold text-[#eee]">RAG Assistant</span>
          </div>

          {workspaceError ? (
            <div className="flex h-full items-center justify-center px-8 text-center text-[#777]">
              The API is unavailable or waking from its free-tier sleep. Use “Retry connection” in the sidebar.
            </div>
          ) : (
            <ChatWindow
              demoConfig={showcaseEnabled ? demoConfig : null}
              documents={documents}
              selectedDocIds={selectedDocIds}
              draftQuestion={draftQuestion}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
