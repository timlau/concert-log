#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
    if ! command -v uv >/dev/null 2>&1; then
        echo "concert-log: uv is required to create the Python environment" >&2
        echo "Install it with: sudo pacman -S uv" >&2
        exit 1
    fi
    uv venv --python python3 "$DIR/.venv"
    uv pip install --python "$PY" "PySide6>=6.6"
fi

exec "$PY" "$DIR/main.py" "$@"
