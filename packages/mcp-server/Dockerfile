FROM python:3.12-slim

WORKDIR /app

# Install core package with embeddings extra (copy source first for editable install)
COPY packages/core/pyproject.toml ./core/pyproject.toml
COPY packages/core/src ./core/src
WORKDIR /app/core
RUN pip install --no-cache-dir -e ".[embeddings]"

# Install MCP server (copy source first for editable install)
WORKDIR /app/mcp
COPY packages/mcp-server/pyproject.toml ./pyproject.toml
COPY packages/mcp-server/src ./src
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "flux_mcp.server"]
