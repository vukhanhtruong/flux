- Backup and Restore data
- Auto backup schedule
- DEBUG_LEVEL

  These configs are currently used at startup:
  - TELEGRAM_BOT_TOKEN — needed by TelegramChannel.start() to connect to Telegram API
  - TELEGRAM_ALLOW_FROM — checked on every incoming message for auth
  - CLAUDE_AUTH_TOKEN — needed by ClaudeRunner to authenticate with Claude API
  - CLAUDE_MODEL — passed to Claude SDK

  Breaking changes? Yes, significant:
  - Bot currently won't start without TELEGRAM_BOT_TOKEN in env (checked in entrypoint.sh)
  - Moving to DB-first config means the app must boot without these, then wait for Web UI configuration
  - Requires a new app state: "unconfigured" → user visits Web UI → configures → services start
  - ClaudeRunner and TelegramChannel need to support hot-reload of config (restart with new credentials)
  - Auth flow changes — TELEGRAM_ALLOW_FROM checked per-message, would need to read from DB instead of env

  My recommendation: Separate user story. Reasons:
  - Backup/restore is self-contained and valuable on its own
  - Runtime config management is a foundational change — it touches boot sequence, service lifecycle, and auth
  - Mixing them risks delaying both features
  - Natural order: ship backup/restore first (uses FLUX_SECRET_KEY + encrypted storage pattern), then build runtime config on top of the same encryption infrastructure

The backup feature actually lays the groundwork — it introduces FLUX_SECRET_KEY, encrypted storage in SQLite, and the Settings UI patterns that the runtime config feature will reuse.
