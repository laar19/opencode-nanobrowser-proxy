#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if command -v uv >/dev/null 2>&1; then
    exec uv run --with fastapi --with uvicorn --with httpx --with python-dotenv python -m opencode_proxy.main
elif [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python -m opencode_proxy.main
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m opencode_proxy.main
else
    echo "Error: Python or uv is required to run OpenCode Proxy." >&2
    exit 1
fi
