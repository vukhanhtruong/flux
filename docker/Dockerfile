# =============================================================================
# FluxFinance — Single-container production Dockerfile
#
# Multi-stage build:
#   Stage 1 (node-builder): Build web-ui static files
#   Stage 2 (runtime):      Python 3.12 + Nginx + ngrok
# =============================================================================

# --- Stage 1: Build web-ui ---------------------------------------------------
FROM node:20-slim AS node-builder

WORKDIR /build
COPY packages/web-ui/package*.json ./
RUN npm ci --silent

COPY packages/web-ui/ ./
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


# --- Stage 2: Runtime ---------------------------------------------------------
FROM python:3.12-slim

# Install Nginx + ngrok (for web UI tunnel)
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        curl \
        gosu \
        gnupg \
        procps \
    && curl -fsSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | gpg --dearmor -o /usr/share/keyrings/ngrok.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/ngrok.gpg] https://ngrok-agent.s3.amazonaws.com buster main" > /etc/apt/sources.list.d/ngrok.list \
    && apt-get update && apt-get install -y --no-install-recommends ngrok \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY packages/core/ /app/packages/core/
COPY packages/api-server/ /app/packages/api-server/
COPY packages/mcp-server/ /app/packages/mcp-server/
COPY packages/agent-bot/ /app/packages/agent-bot/

RUN pip install --no-cache-dir \
    /app/packages/core[vector,embeddings,backup] \
    /app/packages/api-server \
    /app/packages/mcp-server \
    /app/packages/agent-bot

# Copy MCP config for agent-bot
COPY packages/agent-bot/src/flux_bot/mcp-config.json /app/mcp-config.json

# Copy web-ui build output
COPY --from=node-builder /build/dist /usr/share/nginx/html

# Copy nginx config
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Non-root user for data directory ownership
RUN useradd -r -m -s /bin/bash flux

# Create data directories (owned by flux user)
RUN mkdir -p /data/sqlite /data/zvec /data/backups && chown -R flux:flux /data

# Entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose HTTP port (Nginx)
EXPOSE 80

# Environment defaults
ENV DATABASE_PATH=/data/sqlite/flux.db
ENV ZVEC_PATH=/data/zvec
ENV CORS_ORIGINS=http://localhost

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
