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

const { acquireClaudeToken } = await import("../src/claude-auth.js");

describe("acquireClaudeToken", () => {
  let originalLog;

  beforeEach(() => {
    mockExecSync.mock.resetCalls();
    mockPrompts.mock.resetCalls();
    originalLog = console.log;
    console.log = () => {};
  });

  afterEach(() => {
    console.log = originalLog;
  });

  it("OAuth with CLI: runs setup-token then prompts for paste", async () => {
    mockExecSync.mock.mockImplementation(() => {});

    let callCount = 0;
    mockPrompts.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { authType: "oauth" };
      if (callCount === 2) return { token: "sk-ant-oat01-pasted" };
      return {};
    });

    const token = await acquireClaudeToken();
    assert.equal(token, "sk-ant-oat01-pasted");
    // execSync called twice: --version check + setup-token
    assert.equal(mockExecSync.mock.callCount(), 2);
    // prompts called twice: auth type + paste
    assert.equal(mockPrompts.mock.callCount(), 2);
  });

  it("OAuth without CLI: goes straight to paste prompt", async () => {
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
});
