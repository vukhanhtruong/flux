FROM python:3.12-slim

# Install Node.js for Claude Code CLI (required by claude-agent-sdk Python package)
RUN apt-get update && apt-get install -y curl && \
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
  apt-get install -y nodejs && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create a dedicated non-root runtime user for Claude CLI + bot process.
RUN useradd -m -u 1000 -s /bin/bash bot

WORKDIR /app

# Install core package with embeddings extra (needed by MCP tools)
COPY packages/core/pyproject.toml /app/core/pyproject.toml
COPY packages/core/src /app/core/src
WORKDIR /app/core
RUN pip install --no-cache-dir -e ".[embeddings]"

# Install MCP server package (spawned via stdio by claude-agent-sdk)
COPY packages/mcp-server/pyproject.toml /app/mcp-server/pyproject.toml
COPY packages/mcp-server/src /app/mcp-server/src
WORKDIR /app/mcp-server
RUN pip install --no-cache-dir -e .

# Install agent-bot (+ watchfiles for dev hot-reload)
WORKDIR /app/bot
COPY packages/agent-bot/pyproject.toml /app/bot/pyproject.toml
COPY packages/agent-bot/src /app/bot/src
COPY packages/agent-bot/migrations /app/bot/migrations
RUN pip install --no-cache-dir -e . watchfiles

# Copy MCP config
COPY packages/agent-bot/src/flux_bot/mcp-config.json /app/mcp-config.json

# Prepare runtime-writable directories before switching users.
RUN mkdir -p /home/bot/.claude /tmp/flux-images && \
  chown -R bot:bot /home/bot /app /tmp/flux-images

ENV HOME=/home/bot

USER bot

WORKDIR /app/bot/src
CMD ["python", "-m", "flux_bot.main"]
