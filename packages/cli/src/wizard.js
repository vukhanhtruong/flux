import crypto from "node:crypto";
import chalk from "chalk";
import prompts from "prompts";
import ora from "ora";
import { isDockerRunning, pullImage, startContainer } from "./docker.js";
import { readConfig, writeConfig, getDataDir } from "./config.js";
import { readClaudeToken, isClaudeCliInstalled } from "./claude-auth.js";
import {
  showQR,
  BOTFATHER_URL,
  RAW_DATA_BOT_URL,
  BOTFATHER_INSTRUCTIONS,
  RAW_DATA_BOT_INSTRUCTIONS,
  TOKEN_EXAMPLE,
  USER_ID_EXAMPLE,
} from "./qr.js";

export function validateBotToken(value) {
  if (!value || !value.includes(":")) {
    return `Token must contain a colon. Example: ${TOKEN_EXAMPLE}`;
  }
  const [numPart] = value.split(":");
  if (!/^\d+$/.test(numPart)) {
    return `Token must start with numbers. Example: ${TOKEN_EXAMPLE}`;
  }
  return true;
}

export function validateUserId(value) {
  if (!value || !/^\d+$/.test(value)) {
    return `User ID must be a number. Example: ${USER_ID_EXAMPLE}`;
  }
  return true;
}

export function validatePort(value) {
  const port = parseInt(value, 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    return "Port must be a number between 1 and 65535";
  }
  return true;
}

export function generateSecretKey() {
  return crypto.randomUUID();
}

export async function runWizard() {
  console.log(chalk.bold.cyan("\n  FluxFinance Setup Wizard\n"));

  // Step 1: Check Docker
  console.log(chalk.bold("Step 1: Checking prerequisites...\n"));
  const dockerRunning = await isDockerRunning();
  if (!dockerRunning) {
    console.log(chalk.red("  Docker is not running or not installed.\n"));
    console.log("  Install Docker Desktop from:");
    console.log(chalk.blue("    https://docs.docker.com/get-docker/\n"));
    console.log("  After installing, start Docker and run this command again.");
    process.exit(1);
  }
  console.log(chalk.green("  Docker is running.\n"));

  // Step 2: Claude Authentication
  console.log(chalk.bold("Step 2: Claude Authentication\n"));
  let claudeToken = readClaudeToken();

  if (claudeToken) {
    console.log(chalk.green("  Found existing Claude token.\n"));
    const { useExisting } = await prompts({
      type: "confirm",
      name: "useExisting",
      message: "Use the existing Claude token from Claude CLI?",
      initial: true,
    });
    if (!useExisting) claudeToken = null;
  }

  if (!claudeToken) {
    const hasClaude = isClaudeCliInstalled();
    if (hasClaude) {
      const { method } = await prompts({
        type: "select",
        name: "method",
        message: "How would you like to authenticate with Claude?",
        choices: [
          {
            title: "Auto-setup (recommended) — opens browser to sign in",
            value: "auto",
          },
          { title: "Paste token manually", value: "manual" },
        ],
      });

      if (method === "auto") {
        console.log(chalk.dim("\n  Running: claude setup-token\n"));
        const { execSync } = await import("node:child_process");
        try {
          execSync("claude setup-token", { stdio: "inherit" });
          claudeToken = readClaudeToken();
        } catch {
          console.log(
            chalk.yellow("  Auto-setup failed. Please paste token manually.\n")
          );
        }
      }
    }

    if (!claudeToken) {
      const { token } = await prompts({
        type: "password",
        name: "token",
        message: "Paste your Claude auth token (sk-ant-...)",
      });
      claudeToken = token;
    }
  }

  if (!claudeToken) {
    console.log(chalk.red("\n  Claude token is required. Exiting.\n"));
    process.exit(1);
  }

  // Step 3: Create Telegram Bot
  console.log(chalk.bold("\nStep 3: Create your Telegram Bot\n"));
  await showQR(BOTFATHER_URL);
  console.log(BOTFATHER_INSTRUCTIONS);
  console.log();

  const { botToken } = await prompts({
    type: "text",
    name: "botToken",
    message: "Paste your bot token",
    validate: validateBotToken,
  });

  if (!botToken) {
    console.log(chalk.red("\n  Bot token is required. Exiting.\n"));
    process.exit(1);
  }

  // Step 4: Get Telegram User ID
  console.log(chalk.bold("\nStep 4: Get your Telegram User ID\n"));
  await showQR(RAW_DATA_BOT_URL);
  console.log(RAW_DATA_BOT_INSTRUCTIONS);
  console.log();

  const { userId } = await prompts({
    type: "text",
    name: "userId",
    message: "Paste your Telegram User ID",
    validate: validateUserId,
  });

  if (!userId) {
    console.log(chalk.red("\n  User ID is required. Exiting.\n"));
    process.exit(1);
  }

  // Step 5: Choose Port
  console.log(chalk.bold("\nStep 5: Configuration\n"));
  const { port } = await prompts({
    type: "text",
    name: "port",
    message: "Which port should FluxFinance run on?",
    initial: "5173",
    validate: validatePort,
  });

  // Step 6: Pull & Start
  console.log(chalk.bold("\nStep 6: Installing FluxFinance...\n"));

  const config = {
    TELEGRAM_BOT_TOKEN: botToken,
    TELEGRAM_ALLOW_FROM: userId,
    CLAUDE_AUTH_TOKEN: claudeToken,
    FLUX_SECRET_KEY: generateSecretKey(),
    PORT: port || "5173",
  };

  writeConfig(config);
  console.log(chalk.green("  Configuration saved.\n"));

  const spinner = ora("Pulling FluxFinance image...").start();
  try {
    await pullImage();
    spinner.succeed("Image pulled successfully.");
  } catch (err) {
    spinner.fail("Failed to pull image.");
    console.error(chalk.red(`  ${err.message}`));
    process.exit(1);
  }

  const startSpinner = ora("Starting FluxFinance...").start();
  try {
    await startContainer(config, getDataDir());
    startSpinner.succeed("FluxFinance is running!");
  } catch (err) {
    startSpinner.fail("Failed to start container.");
    console.error(chalk.red(`  ${err.message}`));
    process.exit(1);
  }

  // Step 7: Optional ngrok
  console.log();
  const { setupNgrok } = await prompts({
    type: "confirm",
    name: "setupNgrok",
    message:
      "Set up remote access via ngrok? (lets you access from anywhere)",
    initial: false,
  });

  if (setupNgrok) {
    const { ngrokToken } = await prompts({
      type: "password",
      name: "ngrokToken",
      message: "Paste your ngrok authtoken (from https://dashboard.ngrok.com)",
    });
    if (ngrokToken) {
      config.NGROK_AUTHTOKEN = ngrokToken;
      writeConfig(config);
      const restartSpinner = ora("Restarting with ngrok...").start();
      try {
        await startContainer(config, getDataDir());
        restartSpinner.succeed("Restarted with ngrok enabled.");
      } catch (err) {
        restartSpinner.fail("Failed to restart.");
        console.error(chalk.red(`  ${err.message}`));
      }
    }
  }

  // Step 8: Done!
  const finalPort = config.PORT || "5173";
  console.log(chalk.bold.green(`\n  FluxFinance is running!\n`));
  console.log(`  Web UI: ${chalk.cyan(`http://localhost:${finalPort}`)}\n`);
  console.log(chalk.dim("  Management commands:"));
  console.log(chalk.dim("    npx @flux-finance/cli stop      Stop FluxFinance"));
  console.log(chalk.dim("    npx @flux-finance/cli start     Start FluxFinance"));
  console.log(chalk.dim("    npx @flux-finance/cli status    Show status"));
  console.log(chalk.dim("    npx @flux-finance/cli logs      View logs"));
  console.log(chalk.dim("    npx @flux-finance/cli update    Update to latest version"));
  console.log();
}
