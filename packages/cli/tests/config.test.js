import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { readConfig, writeConfig, getConfigPath, getDataDir } from "../src/config.js";

describe("config", () => {
  let originalHome;
  let tmpHome;

  before(() => {
    tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), "flux-cli-test-"));
    originalHome = process.env.HOME;
    process.env.HOME = tmpHome;
  });

  after(() => {
    process.env.HOME = originalHome;
    fs.rmSync(tmpHome, { recursive: true, force: true });
  });

  it("returns empty config when no .env file exists", () => {
    const config = readConfig();
    assert.deepEqual(config, {});
  });

  it("writes and reads config as .env format", () => {
    const config = {
      TELEGRAM_BOT_TOKEN: "123:ABC",
      TELEGRAM_ALLOW_FROM: "456",
      CLAUDE_AUTH_TOKEN: "sk-ant-test",
      FLUX_SECRET_KEY: "uuid-here",
      PORT: "5173",
    };
    writeConfig(config);

    const envPath = path.join(tmpHome, ".flux-finance", ".env");
    assert.ok(fs.existsSync(envPath));

    const read = readConfig();
    assert.equal(read.TELEGRAM_BOT_TOKEN, "123:ABC");
    assert.equal(read.PORT, "5173");
  });

  it("creates data directories on write", () => {
    writeConfig({ PORT: "3000" });
    const dataDir = path.join(tmpHome, ".flux-finance", "data");
    assert.ok(fs.existsSync(path.join(dataDir, "sqlite")));
    assert.ok(fs.existsSync(path.join(dataDir, "zvec")));
    assert.ok(fs.existsSync(path.join(dataDir, "backups")));
  });

  it("getConfigPath returns ~/.flux-finance/.env", () => {
    const p = getConfigPath();
    assert.ok(p.endsWith(path.join(".flux-finance", ".env")));
  });

  it("getDataDir returns ~/.flux-finance/data", () => {
    const d = getDataDir();
    assert.ok(d.endsWith(path.join(".flux-finance", "data")));
  });
});
