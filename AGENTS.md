# Repository Guidelines

## Project Structure & Module Organization
flux is a monorepo centered on `packages/`:
- `packages/core`: shared domain models, business tools, DB repositories, and migrations.
- `packages/api-server`: FastAPI REST layer over `core`.
- `packages/mcp-server`: FastMCP server exposing finance tools.
- `packages/agent-bot`: Telegram/agent orchestrator and bridge integration.
- `packages/web-ui`: React + TypeScript frontend (Vite).

Supporting folders:
- `docs/`: design and implementation plans.
- `firebase/` and `finbot/`: legacy/reference code; do not treat as primary runtime path.

## Build, Test, and Development Commands
Run from repo root unless noted.
- `docker compose up`: start full local stack (Postgres, API, MCP, UI, bot).
- `docker compose up -d postgres`: start DB only for local package development.
- `cd packages/api-server && pip install -e ".[dev]" && uvicorn flux_api.app:app --reload`: run API on `:8000`.
- `cd packages/web-ui && npm install && npm run dev`: run UI on `:5173`.
- `cd packages/<core|api-server|mcp-server|agent-bot> && pytest -v`: run Python tests.
- `cd packages/web-ui && npm run build`: type-check and produce production build.

## Coding Style & Naming Conventions
- Python: 4-space indentation, type hints preferred, `ruff` line length 100 (`pyproject.toml`).
- TypeScript/React: follow ESLint config in `packages/web-ui/eslint.config.js`.
- Naming: snake_case for Python modules/functions, PascalCase for React components, kebab-case for docs/plans files.
- Keep interfaces thin in `api-server`/`mcp-server`; business logic belongs in `packages/core/src/flux_core/tools/`.

## Testing Guidelines
- Framework: `pytest` with `pytest-asyncio` (`asyncio_mode = auto` in package configs).
- Place tests in each package’s `tests/` folder and name files `test_*.py`.
- Prefer unit tests for models/tools and integration tests for DB repos/migrations.
- For bug fixes, add a regression test in the same package before or with the fix.

## Commit & Pull Request Guidelines
- Follow Conventional Commits, consistent with history: `feat(scope): ...`, `fix: ...`, `test: ...`, `docs: ...`, `chore: ...`, `refactor: ...`.
- Keep commits focused by package (example: `fix(agent-bot): handle empty queue poll`).
- PRs should include:
1. clear summary and affected packages,
2. linked issue/task,
3. test evidence (command + result),
4. screenshots/video for `web-ui` changes,
5. notes for env/config or migration changes.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit real secrets.
- Treat `packages/agent-bot/bridge/auth/` as sensitive runtime data; do not include credentials in commits.
