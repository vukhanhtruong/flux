# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-03-15

### Added

- Claude authentication token refresh command (`npx @flux-finance/cli refresh-token`)
- OAuth / API key selection in CLI setup wizard with `setup-token` TUI integration
- Claude model selection in CLI setup wizard (default, sonnet, haiku, or custom model ID)
- Auth error detection in agent bot — notifies admin via Telegram with throttled alerts
- Backup notification now hints users to manage backups and configure S3 via web UI

### Changed

- Onboard backup frequency options changed from daily/weekly to weekly/biweekly
- Simplified CLI token flow — runs `setup-token` TUI directly, user pastes token
- Extracted `acquireClaudeToken()` for reusable token acquisition across CLI commands

### Fixed

- Latent bug: backup confirm fallback defaulted to removed "daily" option (would KeyError)

### Refactored

- Extracted shared error-matching helper and `_safe_send` in message handler
- Concurrent profile + session fetch via `asyncio.gather()` in message handler
- Unified duplicate prompt blocks in CLI auth module
- Single source of truth for backup cron expressions (`_BACKUP_CRON_MAP`)

## [1.3.1] - 2026-03-14

### Fixed

- Default `compound_frequency` to `at_maturity` when user does not specify; agent confirms all details before saving

## [1.3.0] - 2026-03-14

### Added

- `at_maturity` compound frequency for fixed-term savings deposits — interest applied once at maturity
- SQLite migration 004 for existing databases to support `at_maturity` CHECK constraint
- E2E tests verifying scheduled task cleanup on close, withdraw, and delete savings

### Changed

- Moved `periods` lookup in ProcessInterest to avoid unused variable when frequency is `at_maturity`
- Extracted shared test helpers for task assertions and at_maturity mock setup

## [1.2.0] - 2026-03-14

### Added

- Budget monitoring — `check_budgets` MCP tool for monthly budget status in one call
- CheckBudgets use case — budget limits with current-month spending summary

### Changed

- Phase 2: deduplicate infrastructure, analytics use cases, helpers, and test fixtures
- Phase 4: replace raw strings with StrEnums, fix S3 async, fix frontend types, remove dead code
- Prepared repository for open-source publication

### Fixed

- Phase 1: correctness bugs across all packages
- Resolved ruff lint errors across core, api-server, and agent-bot

### Performance

- Phase 3: RETURNING clause, caching, indexes, bounded queries, worker cleanup

## [1.1.0] - 2026-03-13

### Added

- Backup & restore feature with local and S3 storage support
- Savings accounts with interest rate tracking
- Subscription management (pause/resume)
- Scheduled tasks via Telegram bot
- Receipt scanning for auto-creating transactions
- Profile preferences and settings management
- Web UI asset optimization and read-only performance improvements

### Changed

- Migrated from PostgreSQL + pgvector to SQLite (WAL) + zvec for simpler self-hosted deployment
- Replaced PostgreSQL LISTEN/NOTIFY with in-process EventBus (pub/sub)
- Agent Bot now uses Python `claude-agent-sdk` instead of Node.js sidecar
- Single Docker container deployment (Python + Nginx + Node.js)

### Fixed

- SQLite+zvec critical dual-write fixes in Unit of Work
- CLI made executable with proper npm publish configuration

## [1.0.0] - 2026-03-07

### Added

- Initial release
- Telegram bot with Claude AI agent (natural language finance management)
- Web UI (React 19 + TypeScript + Tailwind CSS)
- REST API (FastAPI with OpenAPI documentation)
- MCP Server (FastMCP for Claude Desktop integration)
- Core business logic: transactions, budgets, goals, analytics, memory
- Semantic vector search via zvec + fastembed
- Unit of Work pattern for atomic dual-write (SQLite + zvec)
- CLI installer (`npx @flux-finance/cli`) with guided setup wizard
- CI/CD with GitHub Actions (tests, security scanning, Docker Hub, npm publish)
- 90%+ test coverage across all packages
