import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../api";
import type { LlmConfig, LlmConfigUpdate } from "../../types";

describe("api.llmConfig", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe("getLlmConfig", () => {
    it("returns config when found", async () => {
      const mockConfig: LlmConfig = {
        user_id: "tg:12345",
        provider: "anthropic",
        model: "claude-sonnet-4-6",
        base_url: null,
        api_key_masked: "sk-a...1234",
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfig),
      });

      const result = await api.getLlmConfig("tg:12345");

      expect(result).toEqual(mockConfig);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/llm-config?user_id=tg%3A12345"),
        expect.objectContaining({
          headers: { "Content-Type": "application/json" },
        })
      );
    });

    it("returns null when not found", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
      });

      const result = await api.getLlmConfig("tg:12345");

      expect(result).toBeNull();
    });
  });

  describe("updateLlmConfig", () => {
    it("sends update request", async () => {
      const update: LlmConfigUpdate = {
        provider: "openai",
        model: "gpt-4o",
        base_url: "https://api.openai.com/v1",
        api_key: "sk-new-key",
      };
      const mockResponse: LlmConfig = {
        user_id: "tg:12345",
        provider: "openai",
        model: "gpt-4o",
        base_url: "https://api.openai.com/v1",
        api_key_masked: "sk-n...key",
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.updateLlmConfig("tg:12345", update);

      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/llm-config?user_id=tg%3A12345"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify(update),
        })
      );
    });
  });

  describe("deleteLlmConfig", () => {
    it("sends delete request", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.deleteLlmConfig("tg:12345");

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/llm-config?user_id=tg%3A12345"),
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });
});
