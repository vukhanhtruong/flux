import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AITab } from "./AITab";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    getLlmConfig: vi.fn(),
    updateLlmConfig: vi.fn(),
  },
}));

vi.mock("../../lib/constants", () => ({
  USER_ID: "tg:12345",
}));

describe("AITab", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(api.getLlmConfig).mockImplementation(() => new Promise(() => {}));

    render(<AITab />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows empty state when no config exists", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce(null);

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText(/no ai configuration/i)).toBeInTheDocument();
    });
  });

  it("displays existing config", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "anthropic",
      model: "claude-sonnet-4-6",
      base_url: null,
      api_key_masked: "sk-a...1234",
    });

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText("claude-sonnet-4-6")).toBeInTheDocument();
    });
  });

  it("allows saving new config", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce(null);
    vi.mocked(api.updateLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "anthropic",
      model: "claude-sonnet-4-6",
      base_url: null,
      api_key_masked: "sk-a...1234",
    });

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText(/no ai configuration/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /configure/i }));

    const modelInput = screen.getByLabelText(/model/i);
    await user.clear(modelInput);
    await user.type(modelInput, "claude-sonnet-4-6");

    const apiKeyInput = screen.getByLabelText(/api key/i);
    await user.type(apiKeyInput, "sk-ant-test-key");

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(api.updateLlmConfig).toHaveBeenCalledWith(
        "tg:12345",
        expect.objectContaining({
          provider: "anthropic",
          model: "claude-sonnet-4-6",
          api_key: "sk-ant-test-key",
        })
      );
    });
  });
});
