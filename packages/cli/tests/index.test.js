import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.join(__dirname, "..", "src", "index.js");

describe("cli", () => {
  it("shows help with --help flag", () => {
    const output = execSync(`node ${CLI} --help`, { encoding: "utf-8" });
    assert.ok(output.includes("flux-finance"));
    assert.ok(output.includes("start"));
    assert.ok(output.includes("stop"));
    assert.ok(output.includes("status"));
    assert.ok(output.includes("logs"));
    assert.ok(output.includes("update"));
    assert.ok(output.includes("reset"));
  });

  it("shows version with --version flag", () => {
    const output = execSync(`node ${CLI} --version`, { encoding: "utf-8" });
    assert.match(output.trim(), /^\d+\.\d+\.\d+$/);
  });
});
