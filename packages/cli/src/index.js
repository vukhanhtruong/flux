#!/usr/bin/env node

import { Command } from "commander";

const program = new Command();

program
  .name("flux-finance")
  .description("Install and manage FluxFinance — personal finance AI agent")
  .version("0.1.0");

program.parse();
