#!/usr/bin/env python3
"""Import Obsidian concert notes into Concert Log.

Reads the YAML frontmatter of the markdown notes in the Obsidian folder and
writes each attended show into the app's SQLite database. The import is
idempotent: a show already in the database with the same date and headliner is
skipped, so the script can be run again as notes are added.

Usage:
    .venv/bin/python import_obsidian.py --dry-run
    .venv/bin/python import_obsidian.py
    .venv/bin/python import_obsidian.py --include-not-attended
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from concert_log.database import ConcertDB, default_db_path  # noqa: E402

DEFAULT_SOURCE = (
    Path.home()
    / "Nextcloud/Documents/Notes/Obsidian/Tim Notes/2. Areas/Koncerter/Datoer"
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


# --------------------------------------------------------------- frontmatter


def split_frontmatter(text: str) -> str:
    """Return the YAML block without its `---` fences, or an empty string."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return ""


def clean_value(value: str) -> str:
    value = value.strip()
    if value in {"[]", "~", "null", "Null", "NULL"}:
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    value = WIKILINK_RE.sub(r"\1", value)
    return " ".join(value.split())


def split_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    items: list[str] = []
    current: list[str] = []
    quote = ""
    for char in inner:
        if quote:
            if char == quote:
                quote = ""
            else:
                current.append(char)
        elif char in {'"', "'"}:
            quote = char
        elif char == ",":
            items.append("".join(current))
            current = []
        else:
            current.append(char)
    items.append("".join(current))
    return [clean_value(item) for item in items if clean_value(item)]


def parse_frontmatter(text: str) -> dict[str, list[str]]:
    """Parse the simple scalar/list YAML used by these notes.

    Every value is returned as a list so callers can handle both
    `Band: Junkyard Drive` and the block-list form. Flow lists such as
    `[]`, `[concert]` and `["A", "B"]` are supported too.
    """
    fields: dict[str, list[str]] = {}
    current = ""
    for raw in split_frontmatter(text).splitlines():
        stripped = raw.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw != stripped and stripped.startswith("- "):
            if current:
                fields.setdefault(current, []).append(clean_value(stripped[2:]))
            continue
        match = re.match(r"^([^:]+):\s*(.*)$", raw)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        current = key
        if not value:
            fields[key] = []
        elif value.startswith("[") and value.endswith("]"):
            fields[key] = split_inline_list(value)
        else:
            fields[key] = [clean_value(value)]
    return fields


def first(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key) or []
    return values[0] if values else ""


def all_values(fields: dict[str, list[str]], key: str) -> list[str]:
    return [value for value in fields.get(key, []) if value]


# -------------------------------------------------------------------- parsing


def parse_note(
    path: Path,
    include_not_attended: bool = False,
    today: dt.date | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Turn one note into a `save_concert` payload, or a skip reason.

    Only information from inside the file is used: the filename is never a
    fallback for the date or the band.
    """
    fields = parse_frontmatter(path.read_text(encoding="utf-8"))
    today = today or dt.date.today()

    raw_date = first(fields, "Dato")
    if not DATE_RE.match(raw_date):
        return None, "no valid date"
    try:
        show_date = dt.date.fromisoformat(raw_date)
    except ValueError:
        return None, "invalid date"

    raw_end = first(fields, "SlutDato")
    parsed_end: dt.date | None = None
    end_date = ""
    if raw_end:
        if not DATE_RE.match(raw_end):
            return None, "invalid end date"
        try:
            parsed_end = dt.date.fromisoformat(raw_end)
        except ValueError:
            return None, "invalid end date"
        if parsed_end < show_date:
            return None, "end date before start"
        if parsed_end > show_date:
            end_date = parsed_end.isoformat()

    attended_raw = first(fields, "Deltaget").lower()
    attended = attended_raw not in {"false", "no", "0"}
    if not attended and not include_not_attended:
        last_day = parsed_end or show_date
        if last_day < today:
            return None, "not attended"

    band_values = all_values(fields, "Band")
    headliner = band_values[0] if band_values else ""
    if not headliner:
        return None, "no band"
    # If a note lists several bands under `Band`, treat the rest as support.
    other_bands = band_values[1:] + all_values(fields, "Andre Bands")

    return {
        "band": headliner,
        "event": first(fields, "Arrangement"),
        "date": show_date.isoformat(),
        "endDate": end_date,
        "venue": first(fields, "Spillested"),
        "city": "",
        "otherBands": other_bands,
        "notes": "",
    }, ""


def show_key(show: dict[str, Any]) -> tuple[str, str]:
    return (str(show["date"]), str(show["band"]).casefold())


# ---------------------------------------------------------------------- main


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Obsidian concert notes into Concert Log."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=str(DEFAULT_SOURCE),
        help=f"notes folder (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument("--db", help="database path (default: the app's database)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be imported without writing to the database",
    )
    parser.add_argument(
        "--include-not-attended",
        action="store_true",
        help="also import past notes marked Deltaget: False",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print every imported show"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = Path(args.source).expanduser()
    if not source.is_dir():
        print(f"Notes folder not found: {source}", file=sys.stderr)
        return 1

    files = sorted(source.glob("*.md"))
    if not files:
        print(f"No .md notes found in {source}", file=sys.stderr)
        return 1

    db_path = Path(args.db).expanduser() if args.db else default_db_path()
    database = ConcertDB(db_path)
    existing = {show_key(show) for show in database.list_concerts()}

    imported = 0
    skipped: Counter[str] = Counter()
    errors: list[tuple[str, str]] = []

    for path in files:
        try:
            show, reason = parse_note(path, args.include_not_attended)
        except (OSError, UnicodeError) as error:
            errors.append((path.name, str(error)))
            continue

        if show is None:
            skipped[reason] += 1
            if args.verbose:
                print(f"SKIP  {path.name}  ({reason})")
            continue

        key = show_key(show)
        if key in existing:
            skipped["already imported"] += 1
            if args.verbose:
                print(f"SKIP  {path.name}  (already imported)")
            continue

        if args.dry_run:
            imported += 1
            existing.add(key)
            if args.verbose or args.dry_run:
                print(
                    f"ADD   {show['date']}  {show['band']}  "
                    f"@ {show['venue'] or '—'}"
                )
            continue

        try:
            database.save_concert(show)
        except (ValueError, sqlite3.Error) as error:
            errors.append((path.name, str(error)))
            continue

        imported += 1
        existing.add(key)
        if args.verbose:
            print(
                f"ADD   {show['date']}  {show['band']}  "
                f"@ {show['venue'] or '—'}"
            )

    database.close()

    verb = "Would import" if args.dry_run else "Imported"
    print(f"Scanned {len(files)} notes in {source}")
    print(f"{verb} {imported} show{'s' if imported != 1 else ''}")
    if skipped:
        details = ", ".join(f"{count} {reason}" for reason, count in skipped.most_common())
        print(f"Skipped {sum(skipped.values())} ({details})")
    if errors:
        print(f"Errors {len(errors)}", file=sys.stderr)
        for name, message in errors:
            print(f"  {name}: {message}", file=sys.stderr)
    print(f"Database: {db_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
