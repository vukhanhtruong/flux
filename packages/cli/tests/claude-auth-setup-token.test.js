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

  it("returns true when setup-token succeeds", () => {
    mockExecSync.mock.mockImplementation(() => {});
    assert.equal(runSetupToken(), true);
    assert.equal(mockExecSync.mock.callCount(), 1);
    const [cmd, opts] = mockExecSync.mock.calls[0].arguments;
    assert.equal(cmd, "claude setup-token");
    assert.equal(opts.stdio, "inherit");
  });

  it("returns false when command throws", () => {
    mockExecSync.mock.mockImplementation(() => {
      throw new Error("command failed");
    });
    assert.equal(runSetupToken(), false);
  });
});
