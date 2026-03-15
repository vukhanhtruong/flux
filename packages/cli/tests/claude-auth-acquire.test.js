import { describe, it, mock, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

const mockExecSync = mock.fn();
const mockPrompts = mock.fn();

mock.module("node:child_process", {
  namedExports: { execSync: mockExecSync },
  defaultExport: { execSync: mockExecSync },
});

mock.module("prompts", {
  defaultExport: mockPrompts,
});

mock.module("chalk", {
  defaultExport: {
    dim: (s) => s,
    green: (s) => s,
    yellow: (s) => s,
  },
});

mock.module("ora", {
  defaultExport: () => ({
    start: function () { return this; },
    succeed: function () { return this; },
    warn: function () { return this; },
    fail: function () { return this; },
  }),
});

const { acquireClaudeToken, verifyClaudeToken } = await import("../src/claude-auth.js");

// Realistic-length token (108 chars)
const FAKE_OAUTH =
  "sk-ant-oat01-4yF8Ije4abc123xyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH";

describe("acquireClaudeToken", () => {
  let originalLog;
  let originalFetch;

  beforeEach(() => {
    mockExecSync.mock.resetCalls();
    mockPrompts.mock.resetCalls();
    originalLog = console.log;
    originalFetch = globalThis.fetch;
    console.log = () => {};
    // Default: verification succeeds
    globalThis.fetch = async () => ({ status: 200 });
  });

  afterEach(() => {
    console.log = originalLog;
    globalThis.fetch = originalFetch;
  });

  it("OAuth: returns token from setup-token when CLI installed", async () => {
    mockExecSync.mock.mockImplementation((cmd) => {
      if (cmd === "claude --version") return "";
      return `Token:\n${FAKE_OAUTH}\nDone.`;
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "oauth" };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, FAKE_OAUTH);
    // prompts called once for auth type choice only (no manual paste needed)
    assert.equal(mockPrompts.mock.callCount(), 1);
  });

  it("OAuth: falls back to manual paste when setup-token fails", async () => {
    mockExecSync.mock.mockImplementation((cmd) => {
      if (cmd === "claude --version") return "";
      throw new Error("failed");
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "oauth" };
      if (callCount === 2) return { token: "sk-ant-oat01-manual" };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, "sk-ant-oat01-manual");
    assert.equal(mockPrompts.mock.callCount(), 2);
  });

  it("OAuth: goes straight to manual paste when CLI not installed", async () => {
    mockExecSync.mock.mockImplementation(() => {
      throw new Error("command not found");
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "oauth" };
      if (callCount === 2) return { token: "sk-ant-oat01-pasted" };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, "sk-ant-oat01-pasted");
    assert.equal(mockExecSync.mock.callCount(), 1);
  });

  it("API key: prompts for API key directly", async () => {
    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "apikey" };
      if (callCount === 2) return { token: "sk-ant-api03-xyz789" };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, "sk-ant-api03-xyz789");
    assert.equal(mockExecSync.mock.callCount(), 0);
  });

  it("returns null when user cancels auth type selection", async () => {
    mockPrompts.mock.mockImplementation(async () => ({
      authType: undefined,
    }));

    const token = await acquireClaudeToken();
    assert.equal(token, null);
  });

  it("returns null when no token pasted", async () => {
    mockExecSync.mock.mockImplementation(() => {
      throw new Error("command not found");
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "oauth" };
      if (callCount === 2) return { token: undefined };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, null);
  });

  it("still returns token when verification fails", async () => {
    globalThis.fetch = async () => ({ status: 401 });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "apikey" };
      if (callCount === 2) return { token: "sk-ant-api03-unverified" };
      return {};
    });

    const token = await acquireClaudeToken();
    // Token is returned even if verification fails (non-blocking warning)
    assert.equal(token, "sk-ant-api03-unverified");
  });
});

describe("verifyClaudeToken", () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns true when API responds with 200", async () => {
    globalThis.fetch = async () => ({ status: 200 });
    assert.equal(await verifyClaudeToken("sk-ant-api03-valid"), true);
  });

  it("returns false when API responds with 401", async () => {
    globalThis.fetch = async () => ({ status: 401 });
    assert.equal(await verifyClaudeToken("sk-ant-api03-invalid"), false);
  });

  it("returns false when fetch throws", async () => {
    globalThis.fetch = async () => { throw new Error("network error"); };
    assert.equal(await verifyClaudeToken("sk-ant-api03-test"), false);
  });

  it("uses x-api-key header for API keys", async () => {
    let capturedHeaders;
    globalThis.fetch = async (_url, opts) => {
      capturedHeaders = opts.headers;
      return { status: 200 };
    };
    await verifyClaudeToken("sk-ant-api03-key");
    assert.equal(capturedHeaders["x-api-key"], "sk-ant-api03-key");
    assert.equal(capturedHeaders["authorization"], undefined);
  });

  it("uses Bearer header for OAuth tokens", async () => {
    let capturedHeaders;
    globalThis.fetch = async (_url, opts) => {
      capturedHeaders = opts.headers;
      return { status: 200 };
    };
    await verifyClaudeToken("sk-ant-oat01-token");
    assert.equal(capturedHeaders["authorization"], "Bearer sk-ant-oat01-token");
    assert.equal(capturedHeaders["x-api-key"], undefined);
  });
});
