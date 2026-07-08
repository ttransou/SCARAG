#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  if [[ -n "${frontend_pid:-}" ]]; then
    kill "${frontend_pid}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${api_pid:-}" ]]; then
    kill "${api_pid}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -d "${repo_root}/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "${repo_root}/frontend" && npm install)
fi

echo "Starting React UI on http://127.0.0.1:3000..."
(cd "${repo_root}/frontend" && npm run dev) &
frontend_pid=$!

echo "Starting SCARAG API on http://127.0.0.1:8000..."
"${repo_root}/.venv/bin/python" -m uvicorn api_server:app --reload --host 127.0.0.1 --port 8000 &
api_pid=$!

wait -n "${frontend_pid}" "${api_pid}"