import crypto from "node:crypto";
import chalk from "chalk";
import prompts from "prompts";
import ora from "ora";
import { isDockerRunning, pullImage, startContainer } from "./docker.js";
import { readConfig, writeConfig, getDataDir, getConfigPath } from "./config.js";
import { readClaudeToken, isClaudeCliInstalled, runSetupToken } from "./claude-auth.js";
import {
  showQR,
  BOTFATHER_URL,
  RAW_DATA_BOT_URL,
  BOTFATHER_INSTRUCTIONS,
  RAW_DATA_BOT_INSTRUCTIONS,
  TOKEN_EXAMPLE,
  USER_ID_EXAMPLE,
} from "./qr.js";

export async function fetchBotUsername(token) {
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/getMe`);
    const data = await res.json();
    return data.ok ? data.result.username : null;
  } catch {
    return null;
  }
}

export async function verifyUserId(token, userId) {
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${token}/getChat?chat_id=${userId}`
    );
    const data = await res.json();
    return data.ok ? data.result : null;
  } catch {
    return null;
  }
}

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
    if (isClaudeCliInstalled()) {
      console.log(chalk.dim("  Running: claude setup-token\n"));
      claudeToken = runSetupToken();
      if (claudeToken) {
        console.log(chalk.green("  Token captured successfully.\n"));
      } else {
        console.log(
          chalk.yellow("  Auto-setup failed. Please paste token manually.\n")
        );
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

  // Verify token against Telegram API
  const botUsername = await fetchBotUsername(botToken);
  if (!botUsername) {
    console.log(
      chalk.yellow(
        "\n  Warning: Could not verify this token with Telegram.\n" +
          "  The token may be invalid or revoked.\n" +
          "  Tip: Send /revoke to @BotFather to get a fresh token.\n"
      )
    );
    const { continueAnyway } = await prompts({
      type: "confirm",
      name: "continueAnyway",
      message: "Continue with this token anyway?",
      initial: false,
    });
    if (!continueAnyway) {
      process.exit(1);
    }
  } else {
    console.log(
      chalk.green(`\n  Token verified! Your bot is @${botUsername}\n`)
    );
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

  // Verify user ID — requires the bot to have seen this user before
  const chatInfo = await verifyUserId(botToken, userId);
  if (!chatInfo) {
    console.log(
      chalk.yellow(
        "\n  Could not verify this User ID.\n" +
          "  This is normal if you haven't messaged the bot yet.\n" +
          "  Make sure the ID is correct — you can double-check with @raw_data_bot.\n"
      )
    );
  } else {
    const name = chatInfo.first_name || chatInfo.username || userId;
    console.log(chalk.green(`\n  User ID verified! Hello, ${name}\n`));
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

  console.log(chalk.bold.green("\n  ============================================="));
  console.log(chalk.bold.green("    FluxFinance is up and running!"));
  console.log(chalk.bold.green("  =============================================\n"));

  // Show chat link with QR (botUsername already verified in Step 3)
  if (botUsername) {
    const botUrl = `https://t.me/${botUsername}`;
    console.log(chalk.bold("  Chat with your bot:"));
    console.log(`    Open Telegram and message ${chalk.cyan("@" + botUsername)}`);
    console.log(`    Or scan this QR code:\n`);
    await showQR(botUrl);
  }

  // Web UI
  console.log(chalk.bold("  Web UI:"));
  console.log(`    ${chalk.cyan(`http://localhost:${finalPort}`)}\n`);

  // Data location
  console.log(chalk.bold("  Your data:"));
  console.log(`    Config:   ${chalk.dim(getConfigPath())}`);
  console.log(`    Database: ${chalk.dim(getDataDir() + "/sqlite/")}`);
  console.log(`    Backups:  ${chalk.dim(getDataDir() + "/backups/")}\n`);

  // Getting started tips
  console.log(chalk.bold("  Getting started — try sending these to your bot:"));
  console.log(`    ${chalk.cyan('"I spent $12 on lunch today"')}`);
  console.log(`    ${chalk.cyan('"Set a monthly budget of $500 for food"')}`);
  console.log(`    ${chalk.cyan('"Show me my spending this week"')}`);
  if (config.NGROK_AUTHTOKEN) {
    console.log(`    ${chalk.cyan('"Show me the UI"')} — your bot will share the ngrok link`);
  }
  console.log();

  // Management commands
  console.log(chalk.bold("  Management commands:"));
  console.log(`    ${chalk.cyan("npx @flux-finance/cli stop")}      Stop FluxFinance`);
  console.log(`    ${chalk.cyan("npx @flux-finance/cli start")}     Start FluxFinance`);
  console.log(`    ${chalk.cyan("npx @flux-finance/cli status")}    Show status`);
  console.log(`    ${chalk.cyan("npx @flux-finance/cli logs")}      View logs`);
  console.log(`    ${chalk.cyan("npx @flux-finance/cli update")}    Update to latest version`);
  console.log(`    ${chalk.cyan("npx @flux-finance/cli config")}    Show configuration`);
  console.log();
}
