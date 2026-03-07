# =============================================================================
# FluxFinance — Single-container production Dockerfile
#
# Multi-stage build:
#   Stage 1 (node-builder): Build web-ui static files
#   Stage 2 (runtime):      Python 3.12 + Nginx + Node.js (for Claude CLI)
# =============================================================================

# --- Stage 1: Build web-ui ---------------------------------------------------
FROM node:20-slim AS node-builder

WORKDIR /build
COPY packages/web-ui/package*.json ./
RUN npm ci --silent

COPY packages/web-ui/ ./
ARG VITE_API_BASE_URL=/api
ARG VITE_USER_ID=demo-user
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_USER_ID=${VITE_USER_ID}
RUN npm run build


# --- Stage 2: Runtime ---------------------------------------------------------
FROM python:3.12-slim

# Install Nginx + Node.js (for Claude CLI used by agent-bot)
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code@latest \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY packages/core/ /app/packages/core/
COPY packages/api-server/ /app/packages/api-server/
COPY packages/mcp-server/ /app/packages/mcp-server/
COPY packages/agent-bot/ /app/packages/agent-bot/

RUN pip install --no-cache-dir \
    /app/packages/core[vector,embeddings] \
    /app/packages/api-server \
    /app/packages/mcp-server \
    /app/packages/agent-bot

# Copy web-ui build output
COPY --from=node-builder /build/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Create data directories
RUN mkdir -p /data/sqlite /data/zvec

# Entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose HTTP port (Nginx)
EXPOSE 80

# Environment defaults
ENV DATABASE_PATH=/data/sqlite/flux.db
ENV ZVEC_PATH=/data/zvec
ENV CORS_ORIGINS=http://localhost

ENTRYPOINT ["/app/entrypoint.sh"]
