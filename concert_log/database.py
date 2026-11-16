"""SQLite storage for concerts and bands.

Two tables only, as requested:

    bands(id, name, created_at)
    concerts(id, band_id, event, date, end_date, venue, city, other_bands, notes, ...)

`other_bands` is a JSON array of band ids, which keeps supporting acts in the
bands table without needing a third join table.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date as date_type
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS bands (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL COLLATE NOCASE UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS concerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    band_id     INTEGER NOT NULL REFERENCES bands(id) ON DELETE RESTRICT,
    event       TEXT NOT NULL DEFAULT '',
    date        TEXT NOT NULL,
    end_date    TEXT NOT NULL DEFAULT '',
    venue       TEXT NOT NULL DEFAULT '',
    city        TEXT NOT NULL DEFAULT '',
    other_bands TEXT NOT NULL DEFAULT '[]',
    notes       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS concerts_date_idx ON concerts(date DESC);
"""

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def default_db_path() -> Path:
    override = os.environ.get("CONCERT_LOG_DB")
    if override:
        return Path(override).expanduser()
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return data_home / "concert-log" / "concerts.db"


def _clean(value: Any) -> str:
    return " ".join(str(value).strip().split()) if value is not None else ""


def _parse_other_ids(raw: str) -> list[int]:
    try:
        data = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    result: list[int] = []
    for item in data:
        try:
            band_id = int(item)
        except (TypeError, ValueError):
            continue
        if band_id not in result:
            result.append(band_id)
    return result


class ConcertDB:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    # ------------------------------------------------------------------ reads

    def _band_lookup(self) -> dict[int, str]:
        rows = self.connection.execute("SELECT id, name FROM bands").fetchall()
        return {int(row["id"]): str(row["name"]) for row in rows}

    def list_concerts(
        self, search: str = "", today: date_type | None = None
    ) -> list[dict[str, Any]]:
        today = today or date_type.today()
        bands = self._band_lookup()
        rows = self.connection.execute(
            """
            SELECT id, band_id, event, date, end_date, venue, city,
                   other_bands, notes, created_at
            FROM concerts
            ORDER BY date DESC, id DESC
            """
        ).fetchall()

        needle = search.strip().lower()
        concerts: list[dict[str, Any]] = []
        for row in rows:
            try:
                show_date = date_type.fromisoformat(str(row["date"]))
            except ValueError:
                continue

            supporting = [
                bands[band_id]
                for band_id in _parse_other_ids(str(row["other_bands"]))
                if band_id in bands
            ]
            headliner = bands.get(int(row["band_id"]), "")
            event = str(row["event"])
            venue = str(row["venue"])
            city = str(row["city"])
            notes = str(row["notes"])

            end_date = ""
            raw_end = str(row["end_date"] or "")
            if raw_end:
                try:
                    parsed_end = date_type.fromisoformat(raw_end)
                except ValueError:
                    parsed_end = None
                if parsed_end and parsed_end >= show_date:
                    end_date = parsed_end.isoformat()

            if needle:
                haystack = " ".join(
                    [headliner, event, venue, city, notes, *supporting]
                ).lower()
                if needle not in haystack:
                    continue

            place = " · ".join(part for part in (venue, city) if part)
            start_label = (
                f"{WEEKDAYS[show_date.weekday()]}, "
                f"{show_date.day} {MONTHS[show_date.month - 1]} {show_date.year}"
            )
            if end_date:
                end = date_type.fromisoformat(end_date)
                date_label = (
                    f"{start_label} – "
                    f"{WEEKDAYS[end.weekday()]}, "
                    f"{end.day} {MONTHS[end.month - 1]} {end.year}"
                )
                date_range = f"{show_date.isoformat()} – {end_date}"
            else:
                end = show_date
                date_label = start_label
                date_range = show_date.isoformat()

            if show_date > today:
                status = "upcoming"
                status_label = "UPCOMING"
                days = (show_date - today).days
                status_hint = "Tomorrow" if days == 1 else f"In {days} days"
            elif today <= end:
                status = "ongoing"
                status_label = "TODAY" if show_date == today else "ONGOING"
                if end > today:
                    status_hint = f"Ends {end.day} {MONTHS[end.month - 1]}"
                elif show_date < today:
                    status_hint = "Ends today"
                else:
                    status_hint = "Happening now"
            else:
                status = "past"
                status_label = ""
                status_hint = ""

            concerts.append(
                {
                    "id": int(row["id"]),
                    "bandId": int(row["band_id"]),
                    "band": headliner,
                    "event": event,
                    "date": show_date.isoformat(),
                    "endDate": end_date,
                    "dateRange": date_range,
                    "dateLabel": date_label,
                    "status": status,
                    "statusLabel": status_label,
                    "statusHint": status_hint,
                    "daysUntil": (show_date - today).days,
                    "isFuture": show_date > today,
                    "isOngoing": status == "ongoing",
                    "isPast": status == "past",
                    "day": f"{show_date.day:02d}",
                    "month": MONTHS[show_date.month - 1],
                    "year": str(show_date.year),
                    "weekday": WEEKDAYS[show_date.weekday()],
                    "venue": venue,
                    "city": city,
                    "place": place,
                    "otherBands": supporting,
                    "otherLabel": ", ".join(supporting),
                    "notes": notes,
                    "createdAt": str(row["created_at"]),
                }
            )
        return concerts

    def list_bands(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT name FROM bands ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [str(row["name"]) for row in rows]

    def list_band_rows(self) -> list[dict[str, Any]]:
        counts: dict[int, int] = {}
        for row in self.connection.execute("SELECT band_id, other_bands FROM concerts"):
            headliner = int(row["band_id"])
            counts[headliner] = counts.get(headliner, 0) + 1
            for band_id in _parse_other_ids(str(row["other_bands"])):
                counts[band_id] = counts.get(band_id, 0) + 1

        rows = self.connection.execute(
            "SELECT id, name FROM bands ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "count": counts.get(int(row["id"]), 0),
            }
            for row in rows
        ]

    def list_events(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT DISTINCT event AS value FROM concerts "
            "WHERE event <> '' ORDER BY event COLLATE NOCASE"
        ).fetchall()
        return [str(row["value"]) for row in rows]

    def list_places(self, column: str) -> list[str]:
        if column not in {"venue", "city"}:
            raise ValueError("unknown place column")
        rows = self.connection.execute(
            f"SELECT DISTINCT {column} AS value FROM concerts "
            f"WHERE {column} <> '' ORDER BY {column} COLLATE NOCASE"
        ).fetchall()
        return [str(row["value"]) for row in rows]

    def stats(self) -> dict[str, int]:
        shows = int(
            self.connection.execute("SELECT COUNT(*) FROM concerts").fetchone()[0]
        )
        venues = int(
            self.connection.execute(
                "SELECT COUNT(*) FROM ("
                "  SELECT DISTINCT venue, city FROM concerts WHERE venue <> ''"
                ")"
            ).fetchone()[0]
        )
        used: set[int] = set()
        for row in self.connection.execute("SELECT band_id, other_bands FROM concerts"):
            used.add(int(row["band_id"]))
            used.update(_parse_other_ids(str(row["other_bands"])))
        return {"shows": shows, "bands": len(used), "venues": venues}

    # ----------------------------------------------------------------- writes

    def _band_id(self, name: str) -> int:
        row = self.connection.execute(
            "SELECT id FROM bands WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            return int(row["id"])
        cursor = self.connection.execute("INSERT INTO bands(name) VALUES (?)", (name,))
        return int(cursor.lastrowid)

    def _resolve_band_names(self, names: Iterable[Any], headliner: str) -> list[int]:
        ids: list[int] = []
        seen = {headliner.casefold()}
        for raw in names:
            name = _clean(raw)
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            ids.append(self._band_id(name))
        return ids

    def save_concert(self, data: dict[str, Any]) -> int:
        headliner = _clean(data.get("band"))
        if not headliner:
            raise ValueError("A headliner is required.")

        raw_date = _clean(data.get("date"))
        if not raw_date:
            raise ValueError("A date is required (YYYY-MM-DD).")
        try:
            parsed_date = date_type.fromisoformat(raw_date)
        except ValueError as error:
            raise ValueError("The date needs to look like YYYY-MM-DD.") from error

        raw_end = _clean(data.get("endDate"))
        parsed_end: date_type | None = None
        if raw_end:
            try:
                parsed_end = date_type.fromisoformat(raw_end)
            except ValueError as error:
                raise ValueError("The end date needs to look like YYYY-MM-DD.") from error
            if parsed_end < parsed_date:
                raise ValueError("The end date cannot be before the start date.")
            if parsed_end == parsed_date:
                parsed_end = None

        event = _clean(data.get("event"))
        venue = _clean(data.get("venue"))
        city = _clean(data.get("city"))
        notes = _clean(data.get("notes"))

        other_bands = data.get("otherBands") or []
        if isinstance(other_bands, str):
            other_bands = other_bands.split(",")
        if not isinstance(other_bands, (list, tuple)):
            other_bands = [other_bands]

        concert_id = int(data.get("id") or 0)

        try:
            with self.connection:
                band_id = self._band_id(headliner)
                supporting_ids = self._resolve_band_names(other_bands, headliner)
                payload = json.dumps(supporting_ids, separators=(",", ":"))
                if concert_id:
                    cursor = self.connection.execute(
                        """
                        UPDATE concerts
                        SET band_id = ?, event = ?, date = ?, end_date = ?,
                            venue = ?, city = ?, other_bands = ?, notes = ?,
                            updated_at = datetime('now')
                        WHERE id = ?
                        """,
                        (
                            band_id,
                            event,
                            parsed_date.isoformat(),
                            parsed_end.isoformat() if parsed_end else "",
                            venue,
                            city,
                            payload,
                            notes,
                            concert_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        raise ValueError("That show no longer exists.")
                else:
                    cursor = self.connection.execute(
                        """
                        INSERT INTO concerts(
                            band_id, event, date, end_date, venue, city,
                            other_bands, notes
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            band_id,
                            event,
                            parsed_date.isoformat(),
                            parsed_end.isoformat() if parsed_end else "",
                            venue,
                            city,
                            payload,
                            notes,
                        ),
                    )
                    concert_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise ValueError("That band name is already in use.") from error
        return concert_id

    def delete_concert(self, concert_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM concerts WHERE id = ?", (concert_id,))

    def add_band(self, name: str) -> int:
        clean = _clean(name)
        if not clean:
            raise ValueError("Enter a band name.")
        try:
            with self.connection:
                return self._band_id(clean)
        except sqlite3.IntegrityError as error:
            raise ValueError("That band already exists.") from error

    def rename_band(self, band_id: int, name: str) -> None:
        clean = _clean(name)
        if not clean:
            raise ValueError("A band name cannot be empty.")
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "UPDATE bands SET name = ? WHERE id = ?", (clean, int(band_id))
                )
                if cursor.rowcount == 0:
                    raise ValueError("That band no longer exists.")
        except sqlite3.IntegrityError as error:
            raise ValueError("Another band already uses that name.") from error

    def delete_band(self, band_id: int) -> None:
        band_id = int(band_id)
        headliner_count = int(
            self.connection.execute(
                "SELECT COUNT(*) FROM concerts WHERE band_id = ?", (band_id,)
            ).fetchone()[0]
        )
        if headliner_count:
            raise ValueError(
                f"This band headlines {headliner_count} "
                f"show{'s' if headliner_count != 1 else ''}; reassign those first."
            )

        with self.connection:
            rows = self.connection.execute(
                "SELECT id, other_bands FROM concerts"
            ).fetchall()
            for row in rows:
                ids = _parse_other_ids(str(row["other_bands"]))
                if band_id in ids:
                    remaining = [item for item in ids if item != band_id]
                    self.connection.execute(
                        "UPDATE concerts SET other_bands = ? WHERE id = ?",
                        (json.dumps(remaining, separators=(",", ":")), int(row["id"])),
                    )
            self.connection.execute("DELETE FROM bands WHERE id = ?", (band_id,))
