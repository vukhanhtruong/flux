import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Settings } from "./Settings";

vi.mock("../context/ProfileContext", () => ({
  useProfile: () => ({
    profile: {
      user_id: "tg:12345",
      username: "test",
      channel: "telegram",
      platform_id: "12345",
      currency: "USD",
      timezone: "UTC",
      locale: "en-US",
    },
    loading: false,
    error: null,
  }),
}));

vi.mock("../lib/api", () => ({
  api: {
    listScheduledTasks: vi.fn().mockResolvedValue([]),
    getLlmConfig: vi.fn().mockResolvedValue(null),
    updateLlmConfig: vi.fn(),
  },
}));

describe("Settings", () => {
  it("renders AI tab when clicked", async () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>
    );

    const user = userEvent.setup();
    const aiTab = screen.getByRole("button", { name: /ai/i });
    await user.click(aiTab);

    expect(screen.getByText(/no ai configuration/i)).toBeInTheDocument();
  });
});
