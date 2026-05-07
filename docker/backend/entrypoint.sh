#!/bin/sh
set -eu

if [ -n "${CODETEST_NODE_BIN_DIR:-}" ]; then
  export PATH="${CODETEST_NODE_BIN_DIR}:${PATH}"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[fatal] Node.js runtime is missing (node not found on PATH)." >&2
  exit 78
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[fatal] npm runtime is missing (npm not found on PATH)." >&2
  exit 78
fi

node_version="$(node -v 2>/dev/null || true)"
npm_version="$(npm -v 2>/dev/null || true)"
if [ -z "${node_version}" ] || [ -z "${npm_version}" ]; then
  echo "[fatal] Node.js runtime self-check failed (unable to read version)." >&2
  exit 78
fi

echo "[startup] Node.js ${node_version}, npm ${npm_version}"
exec "$@"
