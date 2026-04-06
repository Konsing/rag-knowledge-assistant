import { useState } from "react";
import Markdown from "react-markdown";
import type { SourceChunk } from "../api/client";

interface Message {
  question: string;
  answer: string;
  sources: SourceChunk[];
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-[#aaa] animate-fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[13px] tabular-nums text-[#777]">{pct}%</span>
    </div>
  );
}

export default function MessageBubble({ message }: { message: Message }) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div className="animate-fade-in">
      {/* User question */}
      <div className="py-6">
        <div className="text-[15px] text-[#888] mb-2">You</div>
        <p className="text-[18px] text-[#eee] leading-relaxed">{message.question}</p>
      </div>

      {/* AI answer */}
      <div className="py-6 border-t border-[#222]">
        <div className="text-[15px] text-[#888] mb-2">Assistant</div>
        <div className="text-[17px] text-[#ddd] leading-relaxed prose prose-invert max-w-none prose-p:my-3 prose-p:leading-relaxed prose-li:my-1.5 prose-headings:mt-5 prose-headings:mb-3 prose-headings:text-[#eee] prose-headings:text-[18px] prose-strong:text-[#eee] prose-strong:font-semibold prose-code:text-[#ddd] prose-code:bg-[#222] prose-code:px-2 prose-code:py-1 prose-code:rounded prose-code:text-[15px] prose-code:font-normal prose-a:text-[#ccc] prose-a:underline prose-a:underline-offset-2">
          <Markdown>{message.answer}</Markdown>
        </div>

        {message.sources.length > 0 && (
          <div className="mt-5">
            <button
              onClick={() => setShowSources(!showSources)}
              className="inline-flex items-center gap-2 text-[15px] text-[#888] hover:text-[#bbb] transition-colors"
            >
              <svg
                className={`w-4 h-4 transition-transform duration-200 ${showSources ? "rotate-90" : ""}`}
                fill="currentColor" viewBox="0 0 20 20"
              >
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              {message.sources.length} sources
            </button>

            {showSources && (
              <div className="mt-3 flex flex-wrap gap-2.5 animate-fade-in">
                {message.sources.map((source, i) => (
                  <div
                    key={i}
                    className="group relative bg-[#1e1e1e] border border-[#2a2a2a] rounded-lg px-4 py-3 hover:border-[#444] transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="text-[14px] text-[#666] font-medium">{i + 1}</span>
                      <span className="text-[15px] text-[#aaa] truncate max-w-[200px]">
                        {source.metadata.source_file}
                      </span>
                      <ScoreBar score={source.score} />
                    </div>
                    {(source.metadata.page_number > 0 || source.metadata.section_title) && (
                      <div className="text-[13px] text-[#666] mt-1.5">
                        {source.metadata.page_number > 0 && <span>p.{source.metadata.page_number}</span>}
                        {source.metadata.page_number > 0 && source.metadata.section_title && <span> &middot; </span>}
                        {source.metadata.section_title && <span>{source.metadata.section_title}</span>}
                      </div>
                    )}
                    {/* Hover preview */}
                    <div className="hidden group-hover:block absolute left-0 top-full mt-1.5 z-10 w-96 bg-[#1e1e1e] border border-[#444] rounded-lg p-4 shadow-lg shadow-black/30">
                      <p className="text-[14px] text-[#aaa] leading-relaxed line-clamp-4">
                        {source.text}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
