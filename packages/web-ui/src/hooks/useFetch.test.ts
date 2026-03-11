import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useFetch } from "./useFetch";

describe("useFetch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should return data on successful fetch", async () => {
    const mockData = { message: "Success" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const { result } = renderHook(() => useFetch("/api/test"));

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it("should handle HTTP errors gracefully", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    });

    const { result } = renderHook(() => useFetch("/api/test"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toContain("404");
    expect(result.current.data).toBeNull();
  });

  it("should handle network errors", async () => {
    const networkError = new Error("Network failure");
    globalThis.fetch = vi.fn().mockRejectedValue(networkError);

    const { result } = renderHook(() => useFetch("/api/test"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toEqual(networkError);
  });

  it("should abort previous request if refetched quickly", async () => {
    const mockAbort = vi.fn();
    // Use an AbortController mock tracker indirectly through the fetch signal
    globalThis.fetch = vi.fn().mockImplementation((_url, init) => {
      if (init?.signal) {
        init.signal.addEventListener('abort', mockAbort);
      }
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({ ok: true, json: () => Promise.resolve({}) });
        }, 100);
      });
    });

    const { result } = renderHook(() => useFetch("/api/slow"));
    
    // Trigger refetch before the first one completes
    act(() => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(mockAbort).toHaveBeenCalled();
    });
  });
});
