import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChatWindow from "./ChatWindow";
import { queryKnowledgeBase } from "../api/client";

vi.mock("../api/client", () => ({
  queryKnowledgeBase: vi.fn(),
}));

describe("ChatWindow", () => {
  beforeEach(() => vi.mocked(queryKnowledgeBase).mockReset());

  it("keeps a failed first question visible and retryable", async () => {
    vi.mocked(queryKnowledgeBase).mockRejectedValueOnce(new Error("Backend unavailable"));
    render(<ChatWindow />);

    fireEvent.change(screen.getByPlaceholderText("Ask a question about your documents..."), {
      target: { value: "What failed?" },
    });
    fireEvent.click(screen.getByLabelText("Send"));

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Ask a question about your documents...")).toHaveValue(
        "What failed?",
      );
    });
  });

  it("scopes showcase queries to selected documents and displays trace metadata", async () => {
    vi.mocked(queryKnowledgeBase).mockResolvedValueOnce({
      answer: "Attention uses queries and keys [1].",
      sources: [{
        text: "Attention maps queries to key-value pairs.",
        score: 0.82,
        metadata: {
          source_file: "paper.pdf",
          page_number: 3,
          section_title: "Attention",
          chunk_index: 2,
          doc_id: "doc-1",
          title: "Attention Is All You Need",
          source_url: "https://arxiv.org/abs/1706.03762",
        },
      }],
      latency_ms: 1200,
      cached: false,
      model: "demo-model",
    });
    render(
      <ChatWindow
        demoConfig={{
          enabled: true,
          captcha_enabled: false,
          captcha_site_key: "",
          queries_per_hour: 10,
          queries_per_day: 50,
          max_selected_documents: 5,
        }}
        documents={[{
          doc_id: "doc-1",
          title: "Attention Is All You Need",
          source_file: "paper.pdf",
          source_url: "https://arxiv.org/abs/1706.03762",
          description: "Transformer paper",
          chunk_count: 12,
          page_count: 15,
          sections: ["Attention"],
          sample_questions: [],
        }]}
        selectedDocIds={["doc-1"]}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Ask a question about your documents..."), {
      target: { value: "How does attention work?" },
    });
    fireEvent.click(screen.getByLabelText("Send"));

    await waitFor(() => {
      expect(queryKnowledgeBase).toHaveBeenCalledWith(
        "How does attention work?",
        5,
        ["doc-1"],
        "",
      );
    });
    expect(await screen.findByText("demo-model · 1.2s")).toBeInTheDocument();
  });
});
