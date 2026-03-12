import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { readClaudeToken, isClaudeCliInstalled } from "../src/claude-auth.js";

describe("claude-auth", () => {
  let originalHome;
  let tmpHome;

  before(() => {
    tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), "flux-claude-test-"));
    originalHome = process.env.HOME;
    process.env.HOME = tmpHome;
  });

  after(() => {
    process.env.HOME = originalHome;
    fs.rmSync(tmpHome, { recursive: true, force: true });
  });

  it("returns null when no credentials file exists", () => {
    const token = readClaudeToken();
    assert.equal(token, null);
  });

  it("reads OAuth access token from credentials file", () => {
    const claudeDir = path.join(tmpHome, ".claude");
    fs.mkdirSync(claudeDir, { recursive: true });
    fs.writeFileSync(
      path.join(claudeDir, ".credentials.json"),
      JSON.stringify({
        claudeAiOauth: {
          accessToken: "sk-ant-oat01-test-token",
          refreshToken: "sk-ant-ort01-test",
          expiresAt: Date.now() + 3600000,
        },
      })
    );
    const token = readClaudeToken();
    assert.equal(token, "sk-ant-oat01-test-token");
  });

  it("returns null when credentials file has no OAuth data", () => {
    const claudeDir = path.join(tmpHome, ".claude");
    fs.mkdirSync(claudeDir, { recursive: true });
    fs.writeFileSync(
      path.join(claudeDir, ".credentials.json"),
      JSON.stringify({})
    );
    const token = readClaudeToken();
    assert.equal(token, null);
  });
});
