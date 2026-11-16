#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
    echo "concert-log: uv is required to run the app" >&2
    echo "Install it with: sudo pacman -S uv" >&2
    exit 1
fi

cd "$DIR"
exec uv run main.py "$@"
