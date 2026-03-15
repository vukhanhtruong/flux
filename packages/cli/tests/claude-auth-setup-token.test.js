import { describe, it, mock, beforeEach } from "node:test";
import assert from "node:assert/strict";

const mockExecSync = mock.fn();

mock.module("node:child_process", {
  namedExports: { execSync: mockExecSync },
  defaultExport: { execSync: mockExecSync },
});

const { runSetupToken } = await import("../src/claude-auth.js");

// Realistic-length token (108 chars, matching real sk-ant-oat tokens)
const FAKE_TOKEN =
  "sk-ant-oat01-4yF8Ije4abc123xyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH";

describe("runSetupToken", () => {
  beforeEach(() => {
    mockExecSync.mock.resetCalls();
  });

  it("parses token from setup-token stdout", () => {
    mockExecSync.mock.mockImplementation(() =>
      "✓ Long-lived authentication token created successfully!\n\n" +
      "Your OAuth token (valid for 1 year):\n\n" +
      `${FAKE_TOKEN}\n\n` +
      "Store this token securely."
    );
    const token = runSetupToken();
    assert.equal(token, FAKE_TOKEN);
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
      `Your OAuth token:\n\n  ${FAKE_TOKEN}  \n\nDone.`
    );
    const token = runSetupToken();
    assert.equal(token, FAKE_TOKEN);
  });

  it("strips ANSI escape codes before matching", () => {
    mockExecSync.mock.mockImplementation(() =>
      `\x1b[32m✓\x1b[0m Token:\n\x1b[1m${FAKE_TOKEN}\x1b[0m\n`
    );
    const token = runSetupToken();
    assert.equal(token, FAKE_TOKEN);
  });

  it("returns null when captured token is too short", () => {
    mockExecSync.mock.mockImplementation(() =>
      "Token:\n\nsk-ant-oat01-short\n\nDone."
    );
    const token = runSetupToken();
    assert.equal(token, null);
  });
});
