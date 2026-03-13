# Contributing to Flux

Thanks for your interest in contributing! This guide will help you get started.

## Getting Started

1. Fork the repository
2. Clone your fork and create a branch:
   ```bash
   git clone https://github.com/<your-username>/flux.git
   cd flux
   git checkout -b feat/your-feature
   ```
3. Set up the development environment:
   ```bash
   cp .env.develop .env
   # Edit .env with your tokens
   ./dev.sh
   ```

## Development Workflow

**TDD is mandatory.** For every feature or bugfix:

1. Write the failing test first
2. Run it to confirm it fails
3. Write the minimal implementation
4. Run tests to confirm they pass
5. Lint your code

### Running Tests

```bash
# All packages
./test-all.sh --coverage

# Individual packages
cd packages/core && pytest tests/ -v
cd packages/api-server && pytest tests/ -v
cd packages/mcp-server && pytest tests/ -v
cd packages/agent-bot && pytest tests/ -v
cd packages/web-ui && npm test
cd packages/cli && npm test
```

### Linting

```bash
ruff check packages/*/src/ packages/*/tests/
```

### Minimum 90% Test Coverage

This is non-negotiable. CI will fail below this threshold for all packages.

## Commit Messages

Use [semantic commit messages](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `test:` adding or updating tests
- `refactor:` code restructuring
- `chore:` tooling, CI, dependencies
- `docs:` documentation

Example: `feat: add CSV transaction import`

## Pull Requests

1. Keep PRs focused — one feature or fix per PR
2. Update tests for any changed behavior
3. Ensure all CI checks pass
4. Write a clear PR description explaining *what* and *why*
5. Link related issues if applicable

## Architecture

Read [CLAUDE.md](./CLAUDE.md) for the full architecture guide, including:

- Monorepo structure and package responsibilities
- Design patterns (Use Case, Unit of Work, Repository, EventBus)
- Key design decisions and conventions

## Code Style

- **Python**: ruff (line-length 100), type hints everywhere, Pydantic v2 models
- **TypeScript**: ESLint, strict tsconfig
- **SQL**: parameterized queries only (`?` placeholders), never string interpolation

## Reporting Issues

- Use GitHub Issues
- Include steps to reproduce, expected behavior, and actual behavior
- For security vulnerabilities, see [SECURITY.md](./SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).
