# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
