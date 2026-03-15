import { describe, it, mock, beforeEach } from "node:test";
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

const { acquireClaudeToken } = await import("../src/claude-auth.js");

describe("acquireClaudeToken", () => {
  let originalLog;

  beforeEach(() => {
    mockExecSync.mock.resetCalls();
    mockPrompts.mock.resetCalls();
    originalLog = console.log;
    console.log = () => {};
  });

  it("OAuth: returns token from setup-token when CLI installed", async () => {
    mockExecSync.mock.mockImplementation((cmd) => {
      if (cmd === "claude --version") return "";
      return "Token:\nsk-ant-oat01-abc123\nDone.";
    });

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "oauth" };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, "sk-ant-oat01-abc123");
    // prompts called once for auth type choice only (no manual paste needed)
    assert.equal(mockPrompts.mock.callCount(), 1);
    console.log = originalLog;
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
    console.log = originalLog;
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
    // execSync called once for --version check only
    assert.equal(mockExecSync.mock.callCount(), 1);
    console.log = originalLog;
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
    // No execSync calls — API key path skips CLI check
    assert.equal(mockExecSync.mock.callCount(), 0);
    console.log = originalLog;
  });

  it("returns null when user cancels auth type selection", async () => {
    mockPrompts.mock.mockImplementation(async () => ({
      authType: undefined,
    }));

    const token = await acquireClaudeToken();
    assert.equal(token, null);
    console.log = originalLog;
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
    console.log = originalLog;
  });
});
