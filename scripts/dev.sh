#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
backend_port="${CONTINUUM_BACKEND_PORT:-8000}"
frontend_port="${CONTINUUM_FRONTEND_PORT:-5173}"
backend_pid=""
frontend_pid=""

cleanup() {
  if [[ -n "$backend_pid" ]]; then kill "$backend_pid" 2>/dev/null || true; fi
  if [[ -n "$frontend_pid" ]]; then kill "$frontend_pid" 2>/dev/null || true; fi
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

(
  cd "$repository_root"
  uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "$backend_port"
) &
backend_pid=$!

(
  cd "$repository_root/frontend"
  CONTINUUM_API_TARGET="http://127.0.0.1:$backend_port" npm run dev -- --host 127.0.0.1 --port "$frontend_port"
) &
frontend_pid=$!

echo "Continuum backend: http://127.0.0.1:$backend_port"
echo "Continuum UI:      http://127.0.0.1:$frontend_port"
wait "$backend_pid" "$frontend_pid"
