# ---- Build frontend ----
FROM node:20-slim AS frontend
WORKDIR /build
COPY website/package.json website/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY website/ ./
# Skip preprocess (data comes from the DB); just compile and bundle
RUN npx tsc -b && npx vite build

# ---- Backend ----
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend

# Install dependencies (cache layer)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy backend source + alembic
COPY backend/atlas_backend/ ./atlas_backend/
COPY backend/alembic.ini ./
COPY backend/alembic/ ./alembic/

# Install the project
RUN uv sync --no-dev

# Copy built frontend — resolves to REPO_ROOT / "website" / "dist"
COPY --from=frontend /build/dist /app/website/dist

ENV ATLAS_HOST=0.0.0.0
ENV ATLAS_PORT=8080

EXPOSE 8080

# Run migrations then start the server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run atlas-backend"]
