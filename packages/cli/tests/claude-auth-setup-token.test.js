import { describe, it, mock, beforeEach } from "node:test";
import assert from "node:assert/strict";

const mockExecSync = mock.fn();

mock.module("node:child_process", {
  namedExports: { execSync: mockExecSync },
  defaultExport: { execSync: mockExecSync },
});

const { runSetupToken } = await import("../src/claude-auth.js");

describe("runSetupToken", () => {
  beforeEach(() => {
    mockExecSync.mock.resetCalls();
  });

  it("parses token from setup-token stdout", () => {
    mockExecSync.mock.mockImplementation(() =>
      "✓ Long-lived authentication token created successfully!\n\n" +
      "Your OAuth token (valid for 1 year):\n\n" +
      "sk-ant-oat01-4yF8Ije4abc123\n\n" +
      "Store this token securely."
    );
    const token = runSetupToken();
    assert.equal(token, "sk-ant-oat01-4yF8Ije4abc123");
    assert.equal(mockExecSync.mock.callCount(), 1);
  });

  it("returns null when command throws", () => {
    mockExecSync.mock.mockImplementation(() => {
      throw new Error("command failed");
    });
    const token = runSetupToken();
    assert.equal(token, null);
  });

  it("returns null when stdout has no token pattern", () => {
    mockExecSync.mock.mockImplementation(() => "No token here");
    const token = runSetupToken();
    assert.equal(token, null);
  });

  it("trims whitespace from captured token", () => {
    mockExecSync.mock.mockImplementation(() =>
      "Your OAuth token:\n\n  sk-ant-oat01-trimMe  \n\nDone."
    );
    const token = runSetupToken();
    assert.equal(token, "sk-ant-oat01-trimMe");
  });
});
