#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if command -v uv >/dev/null 2>&1; then
    exec uv run python main.py
elif [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python main.py
elif command -v python3 >/dev/null 2>&1; then
    exec python3 main.py
else
    echo "Error: Python or uv is required to run OpenCode Proxy." >&2
    exit 1
fi
