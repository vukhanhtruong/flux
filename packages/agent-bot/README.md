# flux Agent Bot

Telegram bot that processes finance messages via Claude, using the Python Agent SDK to call MCP tools against a SQLite + zvec database.

## What It Does

Receives Telegram messages from authorized users and passes them to Claude with access to the `flux` MCP server (finance tools: transactions, budgets, analytics). Responses are sent back to the user. Conversation sessions are persisted so Claude retains context across messages.

## Architecture

```
Telegram ──▶ Agent Bot (Python orchestrator)
               ├── EventBus (MessageCreated → Dispatcher)
               ├── per-user async queues (parallel across users)
               └── claude-agent-sdk (Python)
                     └── flux MCP server (stdio)
                           └── Core Package ──▶ SQLite + zvec
```

**Message flow:**
1. Telegram message received → stored in `bot_messages` table
2. EventBus emits `MessageCreated` → Dispatcher routes to per-user queue
3. `ClaudeRunner.run()` calls `claude_agent_sdk.query()` with MCP config
4. Claude uses finance tools (via MCP) to fulfill the request
5. Result sent back to user via Telegram; session ID saved for continuity

## Setup

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_PATH` | Yes | SQLite database file path, e.g. `/data/sqlite/flux.db` |
| `ZVEC_PATH` | No | zvec data directory (default: `/data/zvec`) |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram Bot API token from @BotFather |
| `CLAUDE_AUTH_TOKEN` | Yes | Auth token — OAuth token (`sk-ant-oat…`) or API key (`sk-ant-api…`) |
| `TELEGRAM_ALLOW_FROM` | No | Comma-separated Telegram usernames to whitelist (empty = all) |
| `CLAUDE_MODEL` | No | Override Claude model (default: determined by CLI) |
| `CLAUDE_TIMEOUT` | No | Query timeout in seconds (default: 300) |
| `CLAUDE_MAX_TURNS` | No | Max agent turns per query (default: 10) |
| `MCP_CONFIG_PATH` | No | Path to MCP config JSON (default: `/app/mcp-config.json`) |
| `SYSTEM_PROMPT_PATH` | No | Path to system prompt text file |

### MCP Config

The MCP config at `src/flux_bot/mcp-config.json` defines the `flux` MCP server:

```json
{
  "mcpServers": {
    "flux": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "flux_mcp.server"],
      "env": {
        "DATABASE_PATH": "${DATABASE_PATH}",
        "ZVEC_PATH": "${ZVEC_PATH}"
      }
    }
  }
}
```

The `--user-id` argument is injected per-request so Claude's tools operate in the correct user's data scope.

## Running Locally

```bash
cd packages/agent-bot
pip install -e ".[dev]"

export DATABASE_PATH="/tmp/flux/flux.db"
export ZVEC_PATH="/tmp/flux/zvec"
export TELEGRAM_BOT_TOKEN="..."
export CLAUDE_AUTH_TOKEN="sk-ant-..."
export MCP_CONFIG_PATH="src/flux_bot/mcp-config.json"

python -m flux_bot.main
```

## Running via Docker

```bash
# From repository root
docker compose up
```

The Docker image includes Node.js and the Claude Code CLI binary (required by `claude-agent-sdk`), plus all Python dependencies.

## Running Tests

```bash
cd packages/agent-bot
pytest tests/ -v
```
