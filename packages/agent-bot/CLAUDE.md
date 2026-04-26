# Agent Bot

Telegram bot orchestrator using DeepAgentRunner (LangGraph deepagents SDK).

## Message Flow

1. Telegram receives message → stores in `bot_messages` table
2. EventBus emits `MessageCreated` → Dispatcher routes to per-user queue
3. Queue processes one message at a time per user (parallel across users)
4. DeepAgentRunner runs agent with direct flux tool access
5. Response sent back via Telegram, thread ID saved for continuity

## claude-agent-sdk Patterns (v0.1.44)

```python
# SystemMessage — session_id in data dict
SystemMessage(subtype="init", data={"session_id": "..."})

# ResultMessage — session_id directly on object
ResultMessage(
    subtype="result",
    duration_ms=123,
    is_error=False,
    session_id="...",
    result="..."
)

# ClaudeAgentOptions
ClaudeAgentOptions(
    resume=session_id,           # Resume existing session
    mcp_servers=[...],           # MCP server configs
    system_prompt="...",
    permission_mode="bypassPermissions",  # NOT allow_dangerously_skip_permissions
    max_turns=10,
    model="claude-sonnet-4-5-20250514"
)
```

## Bot-Specific Tables

All prefixed with `bot_`:
- `bot_messages` — incoming/outgoing messages
- `bot_llm_configs` — per-user LLM configuration

## MCP Config Injection

MCP config at `src/flux_bot/mcp-config.json` is injected with `--user-id` per request.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
TELEGRAM_BOT_TOKEN=... DATABASE_PATH=... python -m main
```
