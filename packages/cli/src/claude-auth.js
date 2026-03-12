import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { execSync } from "node:child_process";

export function readClaudeToken() {
  const credPath = path.join(os.homedir(), ".claude", ".credentials.json");
  if (!fs.existsSync(credPath)) return null;

  try {
    const data = JSON.parse(fs.readFileSync(credPath, "utf-8"));
    return data?.claudeAiOauth?.accessToken || null;
  } catch {
    return null;
  }
}

export function isClaudeCliInstalled() {
  try {
    execSync("claude --version", { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}
