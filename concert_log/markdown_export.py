"""Export each concert as a single Obsidian-style Markdown note.

The destination folder is configured in ``config.toml`` in the XDG config
directory (``~/.config/concert-log/config.toml`` by default)::

    markdown_export_dir = "~/Nextcloud/Documents/Notes/Concerts"

Every concert is written to its own file named ``YYYY-MM-DD Artist Venue.md``.
Existing files with that name are overwritten, so repeated exports stay in sync
with the database.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from datetime import date as date_type
from pathlib import Path
from typing import Any

CONFIG_NAME = "config.toml"
CONFIG_KEY = "markdown_export_dir"

_INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_MAX_FILENAME_BYTES = 251  # 255 minus room for ".md" and a little headroom


def default_config_path() -> Path:
    """Return the app's TOML settings file, honouring XDG_CONFIG_HOME."""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base / "concert-log" / CONFIG_NAME


def configured_directory(config_path: Path | None = None) -> Path:
    """Read ``markdown_export_dir`` from the config file and expand the path."""
    path = Path(config_path).expanduser() if config_path else default_config_path()
    if not path.is_file():
        raise ValueError(
            f"No Markdown export folder configured. Add {CONFIG_KEY} to {path}, "
            'for example: markdown_export_dir = "~/Notes/Concerts"'
        )
    try:
        with path.open("rb") as handle:
            settings = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"Could not read {path}: {error}") from error

    value = settings.get(CONFIG_KEY)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{path}: set {CONFIG_KEY} to the folder where .md notes should be written"
        )
    return Path(value.strip()).expanduser()


def _scalar(value: Any) -> str:
    """Collapse a field into one YAML line, quoting it when necessary."""
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    needs_quotes = (
        text[0] in "-?:,[]{}#&*!|>'\"%@`"
        or ": " in text
        or " #" in text
        or text.endswith(":")
        or text.casefold() in {"true", "false", "null", "yes", "no", "on", "off"}
    )
    if needs_quotes:
        return json.dumps(text, ensure_ascii=False)
    return text


def _filename_part(value: Any) -> str:
    text = _INVALID_FILENAME.sub(" ", str(value or ""))
    return " ".join(text.split())


def note_filename(concert: dict[str, Any]) -> str:
    """Build ``YYYY-MM-DD Artist Venue.md`` with a filesystem-safe name."""
    parts = [
        _filename_part(concert.get("date")),
        _filename_part(concert.get("band")),
        _filename_part(concert.get("venue")),
    ]
    stem = " ".join(part for part in parts if part).strip()
    encoded = stem.encode("utf-8")
    if len(encoded) > _MAX_FILENAME_BYTES:
        stem = encoded[:_MAX_FILENAME_BYTES].decode("utf-8", "ignore").rstrip()
    return f"{stem}.md"


def frontmatter(concert: dict[str, Any], today: date_type | None = None) -> str:
    """Return the complete note: YAML frontmatter and nothing else."""
    today = today or date_type.today()
    other_bands = ", ".join(
        str(name) for name in concert.get("otherBands") or [] if str(name).strip()
    )
    attended = str(concert.get("date") or "") <= today.isoformat()
    lines = [
        "---",
        f"Date: {_scalar(concert.get('date'))}",
        f"Artist: {_scalar(concert.get('band'))}",
        f"Other Artists: {_scalar(other_bands)}",
        f"Event: {_scalar(concert.get('event'))}",
        f"Venue: {_scalar(concert.get('venue'))}",
        f"Participaed: {attended}",
        "Category: concert",
        "--- ",
    ]
    return "\n".join(lines) + "\n"


def export_notes(
    database: Any,
    destination: str | Path | None = None,
    config_path: str | Path | None = None,
    today: date_type | None = None,
) -> dict[str, Any]:
    """Write one .md note per concert and return a summary for the UI."""
    if destination is None:
        directory = configured_directory(config_path)
    else:
        directory = Path(destination).expanduser()
    directory.mkdir(parents=True, exist_ok=True)

    concerts = database.list_concerts()
    for concert in concerts:
        (directory / note_filename(concert)).write_text(
            frontmatter(concert, today), encoding="utf-8"
        )
    return {"directory": str(directory), "shows": len(concerts)}
