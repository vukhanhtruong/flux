# flux Agent Bot

Telegram bot that processes finance messages via the DeepAgent SDK, using LangGraph-based agents to call finance tools against a SQLite + sqlite-vec database.

## What It Does

Receives Telegram messages from authorized users and passes them to an AI agent with access to flux finance tools (transactions, budgets, analytics). Responses are sent back to the user. Conversation threads are persisted so the agent retains context across messages.

## Architecture

```
Telegram ──▶ Agent Bot (Python orchestrator)
               ├── per-user async queues (parallel across users)
               └── DeepAgentRunner (LangGraph + deepagents SDK)
                     └── flux tools (direct function calls)
                           └── Core Package ──▶ SQLite + sqlite-vec
```

**Message flow:**
1. Telegram message received → stored in `bot_messages` table
2. Poller picks up pending messages → routes to per-user queue
3. `DeepAgentRunner.run()` invokes the LangGraph agent with user LLM config
4. Agent uses finance tools to fulfill the request
5. Result sent back to user via Telegram; thread ID saved for continuity

## Setup

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_PATH` | Yes | SQLite database file path, e.g. `/data/sqlite/flux.db` |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram Bot API token from @BotFather |
| `TELEGRAM_ALLOW_FROM` | No | Comma-separated Telegram usernames to whitelist (empty = all) |
| `CLAUDE_TIMEOUT` | No | Agent query timeout in seconds (default: 300) |

### LLM Configuration

Each user configures their own LLM provider via the `/settings llm` command in the bot (or `flux config llm` CLI). Supported providers: `anthropic`, `openai`, `openrouter`.

## Running Locally

```bash
cd packages/agent-bot
pip install -e ".[dev]"

export DATABASE_PATH="/tmp/flux/flux.db"
export TELEGRAM_BOT_TOKEN="..."

python -m flux_bot.main
```

## CLI (Development Mode)

The `flux` CLI lets you chat with the agent and manage configuration directly from your terminal — no Telegram needed.

**Install (editable):**

```bash
cd packages/agent-bot
pip install -e ".[dev]"
```

**Required env var:**

```bash
export FLUX_SECRET_KEY="any-secret-string-for-local-dev"
# Optional: defaults to /data/sqlite/flux.db
export DATABASE_PATH="/tmp/flux-dev.db"
```

**First-time setup:**

```bash
flux onboard          # set your name, currency, timezone
flux config llm       # set LLM provider, model, and API key
```

**Chat:**

```bash
flux chat "what's my balance?"   # one-shot
flux chat                        # REPL mode (Ctrl-D to exit)
flux chat --reset "fresh start"  # clear conversation history first
```

**Other commands:**

```bash
flux flush            # print and drain pending outbound messages
flux --help           # show all subcommands
```

## Running via Docker

```bash
# From repository root
docker compose up
```

## Running Tests

```bash
cd packages/agent-bot
pytest tests/ -v
```
