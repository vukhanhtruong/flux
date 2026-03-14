# Flux

Flux is a self-hosted personal finance AI agent. Chat naturally to track spending, manage budgets, set savings goals, and get insights — all running locally on your machine. Your financial data never leaves your infrastructure.

## Table of Contents

- [What It Does](#what-it-does)
- [Usage Examples](#usage-examples)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Development](#development)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [License](#license)

## What It Does

### Interfaces

- **Telegram Bot** — chat with your finance agent via Telegram (powered by claude-agent-sdk)
- **Web UI** — modern React dashboard for managing everything visually
- **REST API** — full OpenAPI-documented API for integrations
- **MCP Server** — connect via Claude Desktop or any MCP-compatible client

### Finance Features

- **Transactions** — add, update, delete, list, and search transactions with semantic vector search ("coffee last week", "that uber ride")
- **Receipt scanning** — snap a photo of a receipt to auto-create transactions
- **Subscriptions** — track recurring payments, pause/resume them
- **Budgets** — set monthly spending limits per category, track usage
- **Savings** — create savings accounts with interest rate tracking, deposit and withdraw
- **Goals** — set financial goals with target amounts, deposit and withdraw toward them
- **Analytics** — spending summaries, category breakdowns, trend analysis over time

### AI & Platform

- **Memory** — the agent remembers your preferences and context across conversations (semantic recall)
- **Scheduled tasks** — set up recurring reminders or automated actions via the bot
- **Backup & restore** — automated backups to local storage or S3, with restore support
- **Self-hosted & private** — single Docker container, all data stays on your machine

## Usage Examples

### Natural Language Chat

After setup, just chat naturally — no commands needed:

```
You: spent 50k on groceries today
Bot: Added transaction: -50,000 VND (Groceries) on Mar 11

You: how much did I spend last week?
Bot: Last week you spent 1,250,000 VND across 12 transactions.
     Top categories: Food (450k), Transport (320k), Shopping (280k)

You: set budget 2M for food this month
Bot: Budget set: Food — 2,000,000 VND/month (currently used: 450,000 VND)

You: remind me to check subscriptions every Monday
Bot: Scheduled weekly task: "check subscriptions" every Monday at 9:00 AM

You: save 500k to vacation fund
Bot: Deposited 500,000 VND to "Vacation Fund" (total: 3,500,000 / 10,000,000 VND)

You: show UI
Bot: Dashboard is ready! URL: http://nnnn-nnn-nn.ngrok-free.app

```

### Slash Commands

| Command     | Description                                               |
| ----------- | --------------------------------------------------------- |
| `/onboard`  | Walk through setup (currency, timezone, username, backup) |
| `/settings` | Update your preferences                                   |
| `/reset`    | Start a fresh conversation (financial data is unchanged)  |
| `/tasks`    | View your scheduled tasks                                 |
| `/backup`   | Backup your data (download or upload to S3)               |
| `/restore`  | Restore from a backup file                                |
| `/help`     | Show available commands and example queries               |

## Quick Start

### Install via CLI (recommended)

The easiest way to get started — a guided wizard handles everything:

```bash
npx @flux-finance/cli@latest
```

Prerequisites: [Node.js 18+](https://nodejs.org/) and [Docker](https://docs.docker.com/get-docker/)

The wizard will:

1. Detect or prompt for your Claude auth token
2. Walk you through creating a Telegram bot via @BotFather
3. Verify your bot token and user ID
4. Pull the Docker image and start the container

After setup, manage your instance with:

```bash
npx @flux-finance/cli status   # Check if running
npx @flux-finance/cli stop     # Stop the container
npx @flux-finance/cli start    # Start again
npx @flux-finance/cli update   # Pull latest image and restart
npx @flux-finance/cli logs     # View container logs
npx @flux-finance/cli config   # Show current configuration
npx @flux-finance/cli reset    # Remove config and container
```

### Local Development

```bash
# Prerequisites: Python 3.12+, Node.js 20+, uv (https://docs.astral.sh/uv/)

# 1. Configure environment
cp .env.develop .env
# Edit .env with your tokens (Telegram, Claude, etc.)

# 2. Start all services with hot reload
./dev.sh

# Services start at:
#   API:    http://localhost:8000
#   Docs:   http://localhost:8000/docs
#   Web UI: http://localhost:5173
```

#### Docker

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your tokens

# 2. Build and run
docker compose up --build

# Access at http://localhost
```

## Architecture

```
Single Container
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Nginx (:80)                                            │
│    ├── /         →  static web-ui files                 │
│    └── /api/     →  proxy to uvicorn :8000              │
│                                                         │
│  FastAPI (:8000)                                        │
│    └── Routes → Use Cases → UoW → SQLite + zvec         │
│                                                         │
│  Agent Bot (optional)                                   │
│    └── claude-agent-sdk → MCP Server (stdio)            │
│         └── MCP Tools → Use Cases → UoW → SQLite + zvec │
│                                                         │
│  Storage                                                │
│    ├── /data/sqlite/flux.db   (SQLite, WAL mode)        │
│    └── /data/zvec/            (vector embeddings)       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Every write goes through the **Unit of Work**, which coordinates SQLite transactions, vector writes, and event emission as a single atomic operation.

```
Interface (API / MCP)
    ↓
Use Case (business logic)
    ↓
Unit of Work (atomic dual-write + events)
    ↓                    ↓
SQLite + zvec        EventBus (pub/sub)
```

### Telegram Message Flow

```
┌──────────┐    ┌─────────────────┐    ┌────────────────┐    ┌────────────┐
│ Telegram │───▶│ TelegramChannel │───▶│  EventBus      │───▶│ Dispatcher │
│   User   │    │  (bot_messages) │    │ MessageCreated │    │            │
└──────────┘    └─────────────────┘    └────────────────┘    └─────┬──────┘
                                                                   │
                                                                   ▼
┌──────────┐    ┌─────────────────┐    ┌──────────────┐    ┌────────────┐
│ Telegram │◀───│  Save session   │◀───│ ClaudeRunner │◀───│ User Queue │
│   Reply  │    │  Mark processed │    │ agent-sdk    │    │ (per-user) │
└──────────┘    └─────────────────┘    │  MCP tools   │    └────────────┘
                                       └──────────────┘
```

## Project Structure

```
packages/
  core/              # Shared business logic, models, repos, use cases
  api-server/        # FastAPI REST API
  mcp-server/        # FastMCP protocol server (stdio)
  agent-bot/         # Telegram bot — claude-agent-sdk orchestrator
  web-ui/            # React 19 + Vite + Tailwind CSS

dev.sh               # Local dev with hot reload
docker-compose.yml   # Production single-container deploy
test-all.sh          # Run all tests across packages
```

## Tech Stack

| Layer    | Technology                                         |
| -------- | -------------------------------------------------- |
| Backend  | Python 3.12, FastAPI, FastMCP 3.0, Pydantic v2     |
| Storage  | SQLite (WAL) + zvec 0.2.1b0 (vector embeddings)    |
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS v4      |
| AI       | fastembed (all-MiniLM-L6-v2), claude-agent-sdk     |
| Deploy   | Single Docker container (Python + Nginx + Node.js) |

## Development

### Running Tests

```bash
./test-all.sh              # all tests
./test-all.sh --coverage   # with coverage (90% minimum)
```

### Linting

```bash
ruff check packages/*/src/ packages/*/tests/
```

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** — Full architecture, design patterns, and development guidelines
- **[STATE-MACHINES.md](./docs/STATE-MACHINES.md)** — State machine diagrams for all stateful components
- **[USECASES.md](./docs/USECASES.md)** — Complete use case inventory

## Roadmap

- [ ] **CSV/bank import** — import transaction history from bank exports or financial apps
- [ ] **WhatsApp channel** — connect via WhatsApp as an alternative to Telegram

## License

MIT
