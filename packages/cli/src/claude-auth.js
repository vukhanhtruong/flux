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

export function runSetupToken() {
  try {
    execSync("claude setup-token", { stdio: "inherit" });
    return true;
  } catch {
    return false;
  }
}

export async function acquireClaudeToken() {
  const prompts = (await import("prompts")).default;
  const chalk = (await import("chalk")).default;

  const { authType } = await prompts({
    type: "select",
    name: "authType",
    message: "Which authentication method?",
    choices: [
      {
        title: "OAuth token (recommended) — expires ~1 year, use with Claude CLI",
        value: "oauth",
      },
      {
        title: "API key — never expires, requires Anthropic API plan",
        value: "apikey",
      },
    ],
    initial: 0,
  });

  if (!authType) return null;

  let token = null;

  if (authType === "oauth") {
    if (isClaudeCliInstalled()) {
      console.log(chalk.dim("\n  Running: claude setup-token\n"));
      runSetupToken();
      console.log(
        chalk.dim("\n  Copy the token shown above and paste it below.\n")
      );
    }

    const { token: pasted } = await prompts({
      type: "password",
      name: "token",
      message: "Paste your OAuth token (sk-ant-oat...)",
    });
    token = pasted;
  } else {
    const { token: pasted } = await prompts({
      type: "password",
      name: "token",
      message: "Paste your API key (sk-ant-api...)",
    });
    token = pasted;
  }

  return token || null;
}
