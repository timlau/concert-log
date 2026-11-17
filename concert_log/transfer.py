"""Export and import the whole log as a portable zip archive.

The archive contains a JSON manifest plus the setlist photos:

    concert-log.json
    setlists/<photo>.jpg

Import merges the archive into the local database. Shows are matched by their
stable `uid` (or by band/date/event/venue/city for logs created before sync
IDs existed); the most recently edited copy wins. Setlist photos travel with
the archive and deletions of shows are intentionally not propagated.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import setlist
from .database import ConcertDB, _clean

FORMAT = "concert-log"
VERSION = 1
MANIFEST = "concert-log.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _zip_path(destination: str | Path) -> Path:
    path = setlist.local_path(str(destination))
    if path.suffix.lower() != ".zip":
        path = path.with_name(path.name + ".zip")
    return path


def export_archive(db: ConcertDB, destination: str | Path) -> dict[str, Any]:
    """Write every band, show, and setlist photo to a zip file."""
    path = _zip_path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)

    band_rows = db.connection.execute(
        "SELECT id, uid, name FROM bands ORDER BY name COLLATE NOCASE"
    ).fetchall()
    band_names: dict[int, str] = {}
    band_uids: dict[int, str] = {}
    bands: list[dict[str, str]] = []
    for row in band_rows:
        band_id = int(row["id"])
        band_names[band_id] = str(row["name"])
        band_uids[band_id] = str(row["uid"] or "")
        bands.append({"uid": band_uids[band_id], "name": band_names[band_id]})

    rows = db.connection.execute(
        """
        SELECT id, uid, band_id, event, date, end_date, venue, city,
               other_bands, notes, setlist_image, created_at, updated_at
        FROM concerts
        ORDER BY date, id
        """
    ).fetchall()

    concerts: list[dict[str, Any]] = []
    photos = 0

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            setlist_name = Path(str(row["setlist_image"] or "")).name
            member = ""
            source = db.setlist_dir / setlist_name
            if setlist_name and source.is_file():
                member = f"setlists/{setlist_name}"
                archive.write(source, member)
                photos += 1

            supporting = []
            try:
                other_ids = json.loads(str(row["other_bands"] or "[]"))
            except (TypeError, ValueError):
                other_ids = []
            for item in other_ids:
                try:
                    other_id = int(item)
                except (TypeError, ValueError):
                    continue
                if other_id in band_names:
                    supporting.append(
                        {
                            "uid": band_uids.get(other_id, ""),
                            "name": band_names[other_id],
                        }
                    )

            concerts.append(
                {
                    "uid": str(row["uid"] or ""),
                    "bandUid": band_uids.get(int(row["band_id"]), ""),
                    "band": band_names.get(int(row["band_id"]), ""),
                    "event": str(row["event"]),
                    "date": str(row["date"]),
                    "endDate": str(row["end_date"]),
                    "venue": str(row["venue"]),
                    "city": str(row["city"]),
                    "otherBands": supporting,
                    "notes": str(row["notes"]),
                    "createdAt": str(row["created_at"]),
                    "updatedAt": str(row["updated_at"]),
                    "setlist": member,
                }
            )

        manifest = {
            "format": FORMAT,
            "version": VERSION,
            "exportedAt": _now(),
            "bands": bands,
            "concerts": concerts,
        }
        archive.writestr(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False))

    return {
        "path": str(path),
        "shows": len(concerts),
        "bands": len(bands),
        "photos": photos,
    }


def import_archive(db: ConcertDB, source: str | Path) -> dict[str, Any]:
    """Merge a zip made by :func:`export_archive` into this database."""
    path = setlist.local_path(str(source))
    if not path.is_file():
        raise ValueError("That export file could not be found.")

    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as error:
        raise ValueError("That file isn't a Concert Log export.") from error

    with archive:
        try:
            raw = archive.read(MANIFEST)
        except KeyError as error:
            raise ValueError("That file isn't a Concert Log export.") from error
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("That export file is damaged.") from error
        if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
            raise ValueError("That file isn't a Concert Log export.")
        try:
            version = int(manifest.get("version") or 0)
        except (TypeError, ValueError):
            version = 0
        if version > VERSION:
            raise ValueError(
                "This export was made by a newer version of Concert Log."
            )

        with db.connection:
            return _merge(db, archive, manifest)


def _merge(
    db: ConcertDB, archive: zipfile.ZipFile, manifest: dict[str, Any]
) -> dict[str, Any]:
    added = 0
    updated = 0
    unchanged = 0
    photos = 0

    members = set(archive.namelist())
    band_name_by_id: dict[int, str] = {}
    band_uid_by_id: dict[int, str] = {}
    band_ids_by_uid: dict[str, int] = {}
    band_ids_by_name: dict[str, int] = {}

    for row in db.connection.execute("SELECT id, uid, name FROM bands"):
        band_id = int(row["id"])
        name = str(row["name"])
        uid = str(row["uid"] or "")
        band_name_by_id[band_id] = name
        band_uid_by_id[band_id] = uid
        band_ids_by_name[name.casefold()] = band_id
        if uid:
            band_ids_by_uid[uid] = band_id

    for entry in manifest.get("bands") or []:
        if not isinstance(entry, dict):
            continue
        name = _clean(entry.get("name"))
        uid = str(entry.get("uid") or "").strip()
        if not name:
            continue

        local_id = band_ids_by_uid.get(uid) if uid else None
        if local_id is not None:
            # A rename made on the exporting computer wins.
            if band_name_by_id[local_id] != name:
                try:
                    db.connection.execute(
                        "UPDATE bands SET name = ? WHERE id = ?", (name, local_id)
                    )
                except sqlite3.IntegrityError:
                    name = band_name_by_id[local_id]
                else:
                    band_ids_by_name.pop(band_name_by_id[local_id].casefold(), None)
                    band_name_by_id[local_id] = name
                    band_ids_by_name[name.casefold()] = local_id
        else:
            local_id = band_ids_by_name.get(name.casefold())
            if local_id is None:
                cursor = db.connection.execute(
                    "INSERT INTO bands(uid, name) VALUES (?, ?)",
                    (uid or uuid4().hex, name),
                )
                local_id = int(cursor.lastrowid)
                band_name_by_id[local_id] = name
                band_uid_by_id[local_id] = uid or ""
                band_ids_by_name[name.casefold()] = local_id
            else:
                # Same artist already exists under another sync ID. Adopt the
                # incoming ID when the local one is still unset.
                if uid and not band_uid_by_id.get(local_id):
                    try:
                        db.connection.execute(
                            "UPDATE bands SET uid = ? WHERE id = ?", (uid, local_id)
                        )
                    except sqlite3.IntegrityError:
                        pass
                    else:
                        band_uid_by_id[local_id] = uid
                        band_ids_by_uid[uid] = local_id

        band_name_by_id[local_id] = name
        band_ids_by_name[name.casefold()] = local_id
        if uid:
            band_ids_by_uid[uid] = local_id

    def resolve_band(uid_value: Any, name_value: Any) -> int | None:
        uid = str(uid_value or "").strip()
        name = _clean(name_value)
        if uid and uid in band_ids_by_uid:
            return band_ids_by_uid[uid]
        if not name:
            return None
        local = band_ids_by_name.get(name.casefold())
        if local is not None:
            if uid and not band_uid_by_id.get(local):
                try:
                    db.connection.execute(
                        "UPDATE bands SET uid = ? WHERE id = ?", (uid, local)
                    )
                except sqlite3.IntegrityError:
                    pass
                else:
                    band_uid_by_id[local] = uid
                    band_ids_by_uid[uid] = local
            return local
        cursor = db.connection.execute(
            "INSERT INTO bands(uid, name) VALUES (?, ?)",
            (uid or uuid4().hex, name),
        )
        local = int(cursor.lastrowid)
        band_name_by_id[local] = name
        band_uid_by_id[local] = uid or ""
        band_ids_by_name[name.casefold()] = local
        if uid:
            band_ids_by_uid[uid] = local
        return local

    for entry in manifest.get("concerts") or []:
        if not isinstance(entry, dict):
            continue

        raw_date = _clean(entry.get("date"))
        try:
            show_date = date_type.fromisoformat(raw_date)
        except (TypeError, ValueError):
            continue

        raw_end = _clean(entry.get("endDate"))
        show_end: date_type | None = None
        if raw_end:
            try:
                show_end = date_type.fromisoformat(raw_end)
            except ValueError:
                show_end = None
            if show_end is not None and show_end <= show_date:
                show_end = None

        band_id = resolve_band(entry.get("bandUid"), entry.get("band"))
        if band_id is None:
            continue

        event = _clean(entry.get("event"))
        venue = _clean(entry.get("venue"))
        city = _clean(entry.get("city"))
        notes = _clean(entry.get("notes"))

        supporting: list[int] = []
        seen = {band_id}
        for item in entry.get("otherBands") or []:
            if isinstance(item, dict):
                other = resolve_band(item.get("uid"), item.get("name"))
            else:
                other = resolve_band("", item)
            if other is not None and other not in seen:
                seen.add(other)
                supporting.append(other)

        uid = str(entry.get("uid") or "").strip()
        created = str(entry.get("createdAt") or "").strip() or _now()
        incoming_updated = str(entry.get("updatedAt") or "").strip() or created
        setlist_member = str(entry.get("setlist") or "").strip()
        if setlist_member:
            setlist_member = f"setlists/{Path(setlist_member).name}"
        end_iso = show_end.isoformat() if show_end else ""
        other_json = json.dumps(supporting, separators=(",", ":"))

        local = None
        if uid:
            local = db.connection.execute(
                "SELECT id, uid, setlist_image, updated_at FROM concerts WHERE uid = ?",
                (uid,),
            ).fetchone()
        if local is None:
            local = db.connection.execute(
                """
                SELECT id, uid, setlist_image, updated_at FROM concerts
                WHERE band_id = ? AND date = ? AND end_date = ?
                  AND event = ? COLLATE NOCASE
                  AND venue = ? COLLATE NOCASE
                  AND city = ? COLLATE NOCASE
                ORDER BY id
                LIMIT 1
                """,
                (band_id, show_date.isoformat(), end_iso, event, venue, city),
            ).fetchone()

        if local is None:
            cursor = db.connection.execute(
                """
                INSERT INTO concerts(
                    uid, band_id, event, date, end_date, venue, city,
                    other_bands, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid or uuid4().hex,
                    band_id,
                    event,
                    show_date.isoformat(),
                    end_iso,
                    venue,
                    city,
                    other_json,
                    notes,
                    created,
                    incoming_updated,
                ),
            )
            local_id = int(cursor.lastrowid)
            local_image = ""
            local_updated = ""
            newer = True
            added += 1
        else:
            local_id = int(local["id"])
            local_updated = str(local["updated_at"] or "")
            newer = (
                not local_updated
                or not incoming_updated
                or incoming_updated > local_updated
            )
            local_image = str(local["setlist_image"] or "")

            if newer:
                db.connection.execute(
                    """
                    UPDATE concerts
                    SET band_id = ?, event = ?, date = ?, end_date = ?,
                        venue = ?, city = ?, other_bands = ?, notes = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        band_id,
                        event,
                        show_date.isoformat(),
                        end_iso,
                        venue,
                        city,
                        other_json,
                        notes,
                        incoming_updated,
                        local_id,
                    ),
                )
                updated += 1
            else:
                unchanged += 1

            if uid and str(local["uid"] or "") != uid:
                try:
                    db.connection.execute(
                        "UPDATE concerts SET uid = ? WHERE id = ?", (uid, local_id)
                    )
                except sqlite3.IntegrityError:
                    pass

        if setlist_member and setlist_member in members:
            if newer or not local_image:
                image = _read_image(archive, setlist_member)
                if image is not None:
                    filename = setlist.save_image(image, db.setlist_dir, local_id)
                    db.connection.execute(
                        "UPDATE concerts SET setlist_image = ?, updated_at = ? "
                        "WHERE id = ?",
                        (
                            filename,
                            max(local_updated, incoming_updated),
                            local_id,
                        ),
                    )
                    setlist.remove_image(db.setlist_dir, local_image)
                    photos += 1
        elif newer and local_image:
            db.connection.execute(
                "UPDATE concerts SET setlist_image = '' WHERE id = ?", (local_id,)
            )
            setlist.remove_image(db.setlist_dir, local_image)

    return {
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "photos": photos,
    }


def _read_image(archive: zipfile.ZipFile, member: str):
    suffix = Path(member).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}:
        suffix = ".jpg"
    try:
        with tempfile.TemporaryDirectory(prefix="concert-log-import-") as tmp:
            path = Path(tmp) / f"photo{suffix}"
            path.write_bytes(archive.read(member))
            return setlist.load_scaled(str(path))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile):
        return None
