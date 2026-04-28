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

  it("allows editing existing config", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "anthropic",
      model: "claude-sonnet-4-6",
      base_url: null,
      api_key_masked: "sk-a...1234",
    });
    vi.mocked(api.updateLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "openai",
      model: "gpt-4o",
      base_url: null,
      api_key_masked: "sk-a...1234",
    });

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText("claude-sonnet-4-6")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /edit/i }));

    const providerSelect = screen.getByLabelText(/provider/i);
    await user.selectOptions(providerSelect, "openai");

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(api.updateLlmConfig).toHaveBeenCalledWith(
        "tg:12345",
        expect.objectContaining({
          provider: "openai",
          model: "gpt-4o",
        })
      );
    });
  });

  it("cancels editing and restores original values", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "anthropic",
      model: "claude-sonnet-4-6",
      base_url: "https://custom.api.com",
      api_key_masked: "sk-a...1234",
    });

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText("claude-sonnet-4-6")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /edit/i }));

    const modelInput = screen.getByLabelText(/model/i);
    await user.clear(modelInput);
    await user.type(modelInput, "different-model");

    await user.click(screen.getByRole("button", { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.getByText("claude-sonnet-4-6")).toBeInTheDocument();
    });
    expect(screen.queryByDisplayValue("different-model")).not.toBeInTheDocument();
  });

  it("updates model and base_url when provider changes", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce(null);

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText(/no ai configuration/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /configure/i }));

    const providerSelect = screen.getByLabelText(/provider/i);
    await user.selectOptions(providerSelect, "ollama");

    const modelInput = screen.getByLabelText(/model/i);
    expect(modelInput).toHaveValue("llama3.2");

    const baseUrlInput = screen.getByLabelText(/base url/i);
    expect(baseUrlInput).toHaveValue("http://localhost:11434/v1");
  });

  it("displays error state", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "anthropic",
      model: "claude-sonnet-4-6",
      base_url: null,
      api_key_masked: "sk-a...1234",
    });
    vi.mocked(api.updateLlmConfig).mockRejectedValueOnce(new Error("Network error"));

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText("claude-sonnet-4-6")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /edit/i }));
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("shows validation error when model is empty", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce(null);

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText(/no ai configuration/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /configure/i }));

    const modelInput = screen.getByLabelText(/model/i);
    await user.clear(modelInput);

    const apiKeyInput = screen.getByLabelText(/api key/i);
    await user.type(apiKeyInput, "sk-test-key");

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText(/model name is required/i)).toBeInTheDocument();
    });
  });

  it("shows validation error when api key is missing for new config", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce(null);

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText(/no ai configuration/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /configure/i }));

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText(/api key is required/i)).toBeInTheDocument();
    });
  });

  it("displays all config fields in view mode", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "openrouter",
      model: "anthropic/claude-3.5-sonnet",
      base_url: "https://openrouter.ai/api/v1",
      api_key_masked: "sk-or...5678",
    });

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText("openrouter")).toBeInTheDocument();
    });
    expect(screen.getByText("anthropic/claude-3.5-sonnet")).toBeInTheDocument();
    expect(screen.getByText("https://openrouter.ai/api/v1")).toBeInTheDocument();
    expect(screen.getByText("sk-or...5678")).toBeInTheDocument();
  });

  it("shows default label when base_url is null", async () => {
    vi.mocked(api.getLlmConfig).mockResolvedValueOnce({
      user_id: "tg:12345",
      provider: "anthropic",
      model: "claude-sonnet-4-6",
      base_url: null,
      api_key_masked: "sk-a...1234",
    });

    render(<AITab />);

    await waitFor(() => {
      expect(screen.getByText("(default)")).toBeInTheDocument();
    });
  });
});
