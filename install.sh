#!/usr/bin/env bash
set -euo pipefail

# Install a desktop launcher that points at the checkout containing this script.
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
TEMPLATE="$DIR/concert-log.desktop"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET="$DATA_HOME/applications/concert-log.desktop"

if [[ ! -f "$TEMPLATE" ]]; then
    echo "install.sh: missing $TEMPLATE" >&2
    exit 1
fi

if [[ ! -x "$DIR/run.sh" ]]; then
    echo "install.sh: $DIR/run.sh is missing or not executable" >&2
    exit 1
fi

# Rewrite only the paths in the checked-in desktop file, keeping the rest of
# the entry (name, icon, categories, WM class) in one place. Exec values are
# word-split by desktop-entry parsers, so quote the command path.
exec_dir="${DIR//\\/\\\\}"
exec_dir="${exec_dir//\"/\\\"}"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
        Exec=*) printf 'Exec="%s/run.sh"\n' "$exec_dir" ;;
        Icon=*) printf 'Icon=%s/assets/concert-log.svg\n' "$DIR" ;;
        *) printf '%s\n' "$line" ;;
    esac
done < "$TEMPLATE" > "$tmp"

install -Dm644 "$tmp" "$TARGET"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi

echo "Installed $TARGET"
echo "Runs: $DIR/run.sh"
