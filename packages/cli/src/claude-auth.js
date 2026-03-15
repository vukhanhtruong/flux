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

const MIN_TOKEN_LENGTH = 80;

export function runSetupToken() {
  try {
    const output = execSync("claude setup-token", {
      encoding: "utf-8",
      stdio: ["inherit", "pipe", "inherit"],
    });
    // Strip ANSI escape codes before matching
    const clean = output.replace(/\x1b\[[0-9;]*m/g, "");
    const match = clean.match(/sk-ant-oat\S+/);
    if (!match) return null;
    const token = match[0].trim();
    return token.length >= MIN_TOKEN_LENGTH ? token : null;
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

  if (!token) return null;

  const ora = (await import("ora")).default;
  const spinner = ora("Verifying token with Claude API...").start();
  const valid = await verifyClaudeToken(token);
  if (valid) {
    spinner.succeed("Token verified successfully.");
  } else {
    spinner.warn("Could not verify token — it may still work with Claude Code.");
  }

  return token;
}

export async function verifyClaudeToken(token) {
  try {
    const headers = {
      "content-type": "application/json",
      "anthropic-version": "2023-06-01",
    };
    if (token.startsWith("sk-ant-api")) {
      headers["x-api-key"] = token;
    } else {
      headers["authorization"] = `Bearer ${token}`;
    }
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1,
        messages: [{ role: "user", content: "hi" }],
      }),
    });
    return res.status === 200;
  } catch {
    return false;
  }
}
