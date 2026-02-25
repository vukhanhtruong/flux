FROM python:3.12-slim

WORKDIR /app

# Install core package with embeddings extra (copy source first for editable install)
COPY packages/core/pyproject.toml ./core/pyproject.toml
COPY packages/core/src ./core/src
WORKDIR /app/core
RUN pip install --no-cache-dir -e ".[embeddings]"

# Install API server (copy source first for editable install)
WORKDIR /app/api
COPY packages/api-server/pyproject.toml ./pyproject.toml
COPY packages/api-server/src ./src
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "flux_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
