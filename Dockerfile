FROM node:22-alpine AS frontend-build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.8.13 AS uv

FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    CONTINUUM_STATIC_DIR=/app/static
WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN uv sync --project backend --frozen --no-dev
COPY backend/app ./backend/app
COPY --from=frontend-build /src/frontend/dist ./static
EXPOSE 8080
CMD ["sh", "-c", "exec /app/backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8080}"]
