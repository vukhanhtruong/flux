#!/usr/bin/env node

import { Command } from "commander";
import chalk from "chalk";
import ora from "ora";
import { readConfig, writeConfig, getDataDir, getFluxDir } from "./config.js";
import {
  isDockerRunning,
  pullImage,
  startContainer,
  stopContainer,
  removeContainer,
  getContainerStatus,
  containerLogs,
  CONTAINER_NAME,
} from "./docker.js";
import { runWizard } from "./wizard.js";
import fs from "node:fs";

export const program = new Command();

program
  .name("flux-finance")
  .description("Install and manage FluxFinance — personal finance AI agent")
  .version("0.1.0")
  .action(async () => {
    const config = readConfig();
    if (Object.keys(config).length === 0) {
      await runWizard();
    } else {
      const status = await getContainerStatus();
      if (status.running) {
        const port = config.PORT || "5173";
        console.log(chalk.green(`\n  FluxFinance is already running.`));
        console.log(`  Web UI: ${chalk.cyan(`http://localhost:${port}`)}\n`);
      } else {
        const spinner = ora("Starting FluxFinance...").start();
        try {
          await startContainer(config, getDataDir());
          spinner.succeed("FluxFinance is running!");
          const port = config.PORT || "5173";
          console.log(`  Web UI: ${chalk.cyan(`http://localhost:${port}`)}\n`);
        } catch (err) {
          spinner.fail(`Failed to start: ${err.message}`);
          process.exit(1);
        }
      }
    }
  });

program
  .command("start")
  .description("Start FluxFinance")
  .action(async () => {
    const config = readConfig();
    if (Object.keys(config).length === 0) {
      console.log(chalk.yellow("  No configuration found. Running setup wizard...\n"));
      await runWizard();
      return;
    }
    const spinner = ora("Starting FluxFinance...").start();
    try {
      await startContainer(config, getDataDir());
      spinner.succeed("FluxFinance is running!");
      const port = config.PORT || "5173";
      console.log(`  Web UI: ${chalk.cyan(`http://localhost:${port}`)}\n`);
    } catch (err) {
      spinner.fail(`Failed to start: ${err.message}`);
      process.exit(1);
    }
  });

program
  .command("stop")
  .description("Stop FluxFinance")
  .action(async () => {
    const spinner = ora("Stopping FluxFinance...").start();
    try {
      const stopped = await stopContainer();
      if (stopped) {
        spinner.succeed("FluxFinance stopped.");
      } else {
        spinner.info("FluxFinance is not running.");
      }
    } catch (err) {
      spinner.fail(`Failed to stop: ${err.message}`);
      process.exit(1);
    }
  });

program
  .command("status")
  .description("Show FluxFinance status")
  .action(async () => {
    const status = await getContainerStatus();
    const config = readConfig();
    const port = config.PORT || "5173";
    if (!status.exists) {
      console.log(chalk.yellow("\n  FluxFinance is not installed.\n"));
      console.log(`  Run ${chalk.cyan("npx @flux-finance/cli")} to set up.\n`);
    } else if (status.running) {
      console.log(chalk.green("\n  FluxFinance is running."));
      console.log(`  Web UI: ${chalk.cyan(`http://localhost:${port}`)}`);
      console.log(`  Container: ${CONTAINER_NAME}`);
      console.log(`  Status: ${status.status}\n`);
    } else {
      console.log(chalk.yellow("\n  FluxFinance is stopped."));
      console.log(`  Run ${chalk.cyan("npx @flux-finance/cli start")} to start.\n`);
    }
  });

program
  .command("logs")
  .description("View FluxFinance logs")
  .action(async () => {
    const stream = await containerLogs(true);
    if (!stream) {
      console.log(chalk.yellow("  FluxFinance is not running.\n"));
      process.exit(1);
    }
    stream.pipe(process.stdout);
  });

program
  .command("update")
  .description("Update FluxFinance to the latest version")
  .action(async () => {
    const config = readConfig();
    if (Object.keys(config).length === 0) {
      console.log(chalk.yellow("  No configuration found. Run setup first.\n"));
      process.exit(1);
    }
    const spinner = ora("Pulling latest image...").start();
    try {
      await pullImage();
      spinner.succeed("Latest image pulled.");
    } catch (err) {
      spinner.fail(`Failed to pull: ${err.message}`);
      process.exit(1);
    }
    const restartSpinner = ora("Restarting with new image...").start();
    try {
      await startContainer(config, getDataDir());
      restartSpinner.succeed("FluxFinance updated and running!");
      const port = config.PORT || "5173";
      console.log(`  Web UI: ${chalk.cyan(`http://localhost:${port}`)}\n`);
    } catch (err) {
      restartSpinner.fail(`Failed to restart: ${err.message}`);
      process.exit(1);
    }
  });

program
  .command("ngrok")
  .description("Configure ngrok remote access")
  .action(async () => {
    const config = readConfig();
    const prompts = (await import("prompts")).default;
    const { ngrokToken } = await prompts({
      type: "password",
      name: "ngrokToken",
      message: "Paste your ngrok authtoken (from https://dashboard.ngrok.com)",
    });
    if (ngrokToken) {
      config.NGROK_AUTHTOKEN = ngrokToken;
      writeConfig(config);
      console.log(chalk.green("  Ngrok token saved.\n"));
      const status = await getContainerStatus();
      if (status.running) {
        const spinner = ora("Restarting with ngrok...").start();
        try {
          await startContainer(config, getDataDir());
          spinner.succeed("Restarted with ngrok enabled.");
        } catch (err) {
          spinner.fail(`Failed to restart: ${err.message}`);
        }
      }
    }
  });

program
  .command("reset")
  .description("Wipe configuration and start fresh")
  .action(async () => {
    const prompts = (await import("prompts")).default;
    const { confirm } = await prompts({
      type: "confirm",
      name: "confirm",
      message:
        "This will remove your configuration and stop FluxFinance. Your data in ~/.flux-finance/data/ will be kept. Continue?",
      initial: false,
    });
    if (!confirm) {
      console.log("  Cancelled.\n");
      return;
    }
    await removeContainer();
    const fluxDir = getFluxDir();
    const envPath = `${fluxDir}/.env`;
    if (fs.existsSync(envPath)) {
      fs.unlinkSync(envPath);
    }
    console.log(chalk.green("  Configuration removed. Data preserved.\n"));
    console.log(`  Run ${chalk.cyan("npx @flux-finance/cli")} to set up again.\n`);
  });

program
  .command("config")
  .description("Show current configuration")
  .action(() => {
    const config = readConfig();
    if (Object.keys(config).length === 0) {
      console.log(chalk.yellow("\n  No configuration found.\n"));
      return;
    }
    console.log(chalk.bold("\n  FluxFinance Configuration:\n"));
    for (const [key, value] of Object.entries(config)) {
      const masked =
        key.includes("TOKEN") || key.includes("SECRET") || key.includes("AUTH")
          ? value.slice(0, 10) + "..."
          : value;
      console.log(`  ${chalk.dim(key)}: ${masked}`);
    }
    console.log();
  });

// Only parse when run directly (not when imported for testing)
const isDirectRun =
  process.argv[1] &&
  (process.argv[1].endsWith("/index.js") ||
    process.argv[1].endsWith("flux-finance"));

if (isDirectRun) {
  program.parse();
}
