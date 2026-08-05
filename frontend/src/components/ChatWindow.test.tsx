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
});
