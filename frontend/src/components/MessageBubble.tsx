import { useState } from "react";
import Markdown from "react-markdown";
import type { SourceChunk } from "../api/client";

interface Message {
  question: string;
  answer: string;
  sources: SourceChunk[];
}

export default function MessageBubble({ message }: { message: Message }) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div className="space-y-3">
      {/* User question */}
      <div className="flex justify-end">
        <div className="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[80%]">
          {message.question}
        </div>
      </div>

      {/* AI answer */}
      <div className="flex justify-start">
        <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-sm">
          <div className="text-gray-800 prose prose-sm max-w-none prose-p:my-1 prose-li:my-0.5 prose-headings:mt-3 prose-headings:mb-1">
            <Markdown>{message.answer}</Markdown>
          </div>

          {message.sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              {showSources
                ? "Hide sources"
                : `Show ${message.sources.length} sources`}
            </button>
          )}

          {showSources && (
            <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
              {message.sources.map((source, i) => (
                <div
                  key={i}
                  className="text-sm bg-gray-50 rounded-lg p-3 border border-gray-100"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-0.5 rounded">
                      [{i + 1}]
                    </span>
                    <span className="text-gray-500 text-xs">
                      {source.metadata.source_file} &middot; p.
                      {source.metadata.page_number} &middot;{" "}
                      {source.metadata.section_title}
                    </span>
                    <span className="ml-auto text-xs text-gray-400">
                      {(source.score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="text-gray-600 text-xs leading-relaxed line-clamp-3">
                    {source.text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
