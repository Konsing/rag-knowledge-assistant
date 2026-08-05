import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DocumentLibrary from "./DocumentLibrary";

const documents = [{
  doc_id: "doc-1",
  title: "Attention Is All You Need",
  source_file: "1706.03762.pdf",
  source_url: "https://arxiv.org/abs/1706.03762",
  description: "Transformer paper",
  chunk_count: 12,
  page_count: 15,
  sections: ["Introduction"],
  sample_questions: ["How does attention work?"],
}];

describe("DocumentLibrary", () => {
  it("lets visitors choose retrieval scope and reuse sample questions", () => {
    const onSelectionChange = vi.fn();
    const onUseQuestion = vi.fn();
    render(
      <DocumentLibrary
        documents={documents}
        loading={false}
        selectedIds={[]}
        maxSelected={3}
        onSelectionChange={onSelectionChange}
        onUseQuestion={onUseQuestion}
      />,
    );

    fireEvent.click(screen.getByLabelText("Use Attention Is All You Need in retrieval"));
    expect(onSelectionChange).toHaveBeenCalledWith(["doc-1"]);

    fireEvent.click(screen.getByText("“How does attention work?”"));
    expect(onUseQuestion).toHaveBeenCalledWith("How does attention work?");
  });
});
