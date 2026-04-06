import { useRef, useState, useEffect } from "react";
import { queryKnowledgeBase } from "../api/client";
import type { SourceChunk } from "../api/client";
import MessageBubble from "./MessageBubble";

interface Message {
  question: string;
  answer: string;
  sources: SourceChunk[];
}

const SUGGESTED_QUESTIONS = [
  "What are the main findings of the papers?",
  "Summarize the methodology used",
  "What future work is suggested?",
];

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [input]);

  async function submitQuestion(question: string) {
    if (!question || loading) return;
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const response = await queryKnowledgeBase(question);
      setMessages((prev) => [
        ...prev,
        { question, answer: response.answer, sources: response.sources },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    submitQuestion(input.trim());
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {messages.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center h-full px-10">
            <div className="max-w-xl text-center">
              <div className="mx-auto w-16 h-16 rounded-xl bg-[#222] border border-[#2a2a2a] flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-[#888]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                </svg>
              </div>

              <h2 className="text-[22px] font-semibold text-[#eee] tracking-[-0.01em] mb-3">
                Ask your knowledge base
              </h2>
              <p className="text-[16px] text-[#888] mb-10 leading-relaxed">
                Ingest documents using the sidebar, then ask questions.
                Answers are grounded in your sources with citations.
              </p>

              <div className="space-y-3">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => submitQuestion(q)}
                    className="w-full text-left px-5 py-4 rounded-lg border border-[#2a2a2a] text-[16px] text-[#aaa] hover:text-[#ddd] hover:border-[#444] hover:bg-[#1e1e1e] transition-colors"
                  >
                    <span className="text-[#666] mr-2">&rarr;</span>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-8 py-8">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}

            {loading && (
              <div className="py-6 animate-fade-in">
                <div className="text-[15px] text-[#888] mb-2.5">Assistant</div>
                <div className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 bg-[#777] rounded-full typing-dot" />
                  <div className="w-2.5 h-2.5 bg-[#777] rounded-full typing-dot" />
                  <div className="w-2.5 h-2.5 bg-[#777] rounded-full typing-dot" />
                  <span className="ml-2 text-[15px] text-[#666]">Searching & generating...</span>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-lg bg-[#2a1515] border border-[#3a2020] px-5 py-4 text-[15px] text-[#f99] animate-fade-in">
                {error}
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-[#2a2a2a] bg-[#191919] px-8 py-5">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative flex items-end gap-3 bg-[#1e1e1e] border border-[#2a2a2a] rounded-xl p-2 focus-within:border-[#444] transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents..."
              rows={1}
              className="flex-1 bg-transparent px-4 py-3 text-[16px] text-[#eee] resize-none focus:outline-none placeholder:text-[#666]"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3 rounded-lg bg-[#eee] text-[#141414] hover:bg-white disabled:bg-[#222] disabled:text-[#555] disabled:cursor-not-allowed transition-colors flex-shrink-0"
              aria-label="Send"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
              </svg>
            </button>
          </div>
          <p className="text-[13px] text-[#666] mt-2.5 text-center">
            Enter to send &middot; Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
}
