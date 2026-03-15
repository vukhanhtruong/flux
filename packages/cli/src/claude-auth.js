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
    const output = execSync("claude setup-token", {
      encoding: "utf-8",
      stdio: ["inherit", "pipe", "inherit"],
    });
    const match = output.match(/sk-ant-oat\S+/);
    return match ? match[0].trim() : null;
  } catch {
    return null;
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
      console.log(chalk.dim("  Running: claude setup-token\n"));
      token = runSetupToken();
      if (token) {
        console.log(chalk.green("  Token captured successfully.\n"));
      } else {
        console.log(
          chalk.yellow("  Auto-setup failed. Please paste token manually.\n")
        );
      }
    }

    if (!token) {
      const { token: pasted } = await prompts({
        type: "password",
        name: "token",
        message: "Paste your OAuth token (sk-ant-oat...)",
      });
      token = pasted;
    }
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
