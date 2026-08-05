import { StrictMode } from "react";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import IngestPanel from "./IngestPanel";
import { getStats } from "../api/client";

vi.mock("../api/client", () => ({
  getStats: vi.fn(),
  ingestArxivUrl: vi.fn(),
  ingestFile: vi.fn(),
  ingestWebUrl: vi.fn(),
}));

describe("IngestPanel", () => {
  beforeEach(() => {
    vi.mocked(getStats).mockReset();
    vi.mocked(getStats).mockResolvedValue({ name: "test", points_count: 4 });
  });

  it("requests stats once even under StrictMode", async () => {
    render(
      <StrictMode>
        <IngestPanel />
      </StrictMode>,
    );

    await waitFor(() => expect(getStats).toHaveBeenCalledTimes(1));
  });
});
