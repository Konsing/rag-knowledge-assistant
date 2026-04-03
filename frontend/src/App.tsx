import ChatWindow from "./components/ChatWindow";
import IngestPanel from "./components/IngestPanel";

function App() {
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              RAG Knowledge Assistant
            </h1>
            <p className="text-xs text-gray-500">
              Ask questions about your research papers
            </p>
          </div>
          <span className="text-xs text-gray-300 hidden sm:block">
            Built from scratch &mdash; no LangChain
          </span>
        </div>
      </header>

      {/* Main layout: sidebar + chat */}
      <div className="flex-1 flex overflow-hidden max-w-7xl w-full mx-auto">
        {/* Sidebar: Ingest panel */}
        <aside className="w-80 flex-shrink-0 border-r border-gray-200 bg-white p-4 overflow-y-auto hidden md:block">
          <IngestPanel />
        </aside>

        {/* Chat area */}
        <main className="flex-1 flex flex-col bg-gray-50">
          <ChatWindow />
        </main>
      </div>
    </div>
  );
}

export default App;
