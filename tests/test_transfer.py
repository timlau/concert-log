from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage  # noqa: E402

from concert_log import setlist, transfer  # noqa: E402
from concert_log.database import ConcertDB  # noqa: E402


class TransferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_a = ConcertDB(self.root / "a" / "concerts.db")
        self.db_b = ConcertDB(self.root / "b" / "concerts.db")
        self.archive = self.root / "export.zip"

    def tearDown(self) -> None:
        self.db_a.close()
        self.db_b.close()
        self.tmp.cleanup()

    def add_show(self, db: ConcertDB, **overrides) -> int:
        data = {
            "band": "Godspeed You! Black Emperor",
            "date": "2025-06-14",
            "venue": "Barbican",
            "city": "London",
            "otherBands": [],
            "notes": "Very loud.",
        }
        data.update(overrides)
        return db.save_concert(data)

    def export(self) -> dict:
        return transfer.export_archive(self.db_a, self.archive)

    def import_to_b(self) -> dict:
        return transfer.import_archive(self.db_b, self.archive)

    def set_timestamp(self, db: ConcertDB, concert_id: int, notes: str, stamp: str) -> None:
        with db.connection:
            db.connection.execute(
                "UPDATE concerts SET notes = ?, updated_at = ? WHERE id = ?",
                (notes, stamp, concert_id),
            )

    def photo(self) -> Path:
        image = QImage(200, 800, QImage.Format_RGB32)
        image.fill(0xFF445566)
        path = self.root / "source.png"
        self.assertTrue(image.save(str(path), "PNG"))
        return path

    def attach_photo(self, db: ConcertDB, concert_id: int, source: Path) -> Path:
        image = setlist.load_scaled(str(source))
        filename = setlist.save_image(image, db.setlist_dir, concert_id)
        db.set_setlist_image(concert_id, filename)
        return db.setlist_dir / filename

    def test_export_then_import_with_support_and_photo(self) -> None:
        concert_id = self.add_show(
            self.db_a,
            event="Roskilde",
            endDate="2025-06-16",
            otherBands=["Mogwai", "Low"],
        )
        source = self.attach_photo(self.db_a, concert_id, self.photo())

        result = self.export()
        self.assertEqual(result["shows"], 1)
        self.assertEqual(result["photos"], 1)

        stats = self.import_to_b()
        self.assertEqual(stats, {"added": 1, "updated": 0, "unchanged": 0, "photos": 1})

        show = self.db_b.list_concerts()[0]
        self.assertEqual(show["band"], "Godspeed You! Black Emperor")
        self.assertEqual(show["event"], "Roskilde")
        self.assertEqual(show["endDate"], "2025-06-16")
        self.assertEqual(show["otherBands"], ["Mogwai", "Low"])
        self.assertEqual(show["notes"], "Very loud.")

        imported = Path(show["setlistImage"].removeprefix("file://"))
        self.assertTrue(imported.is_file())
        self.assertNotEqual(imported.name, source.name)
        self.assertEqual(QImage(str(imported)).height(), 800)
        self.assertEqual(self.db_b.stats()["shows"], 1)

    def test_import_is_idempotent(self) -> None:
        concert_id = self.add_show(self.db_a)
        self.attach_photo(self.db_a, concert_id, self.photo())
        self.export()

        self.import_to_b()
        again = self.import_to_b()
        self.assertEqual(again, {"added": 0, "updated": 0, "unchanged": 1, "photos": 0})
        self.assertEqual(len(self.db_b.list_concerts()), 1)
        self.assertEqual(len(list(self.db_b.setlist_dir.iterdir())), 1)

    def test_newer_edit_wins_in_both_directions(self) -> None:
        concert_id = self.add_show(self.db_a)
        self.export()
        self.import_to_b()
        local_id = self.db_b.list_concerts()[0]["id"]

        self.set_timestamp(self.db_b, local_id, "local edit", "2099-01-01 00:00:00")
        stats = self.import_to_b()
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(self.db_b.list_concerts()[0]["notes"], "local edit")

        self.set_timestamp(self.db_a, concert_id, "remote edit", "2099-01-02 00:00:00")
        self.export()
        stats = self.import_to_b()
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(self.db_b.list_concerts()[0]["notes"], "remote edit")

    def test_same_show_with_different_ids_is_not_duplicated(self) -> None:
        remote_id = self.add_show(
            self.db_a, band="Shared Band", date="2025-03-03", venue="Vega"
        )
        local_id = self.add_show(
            self.db_b, band="Shared Band", date="2025-03-03", venue="Vega"
        )
        self.export()

        stats = self.import_to_b()
        self.assertEqual(stats["added"], 0)
        self.assertEqual(self.db_b.stats()["shows"], 1)

        remote_uid = self.db_a.connection.execute(
            "SELECT uid FROM concerts WHERE id = ?", (remote_id,)
        ).fetchone()[0]
        local_uid = self.db_b.connection.execute(
            "SELECT uid FROM concerts WHERE id = ?", (local_id,)
        ).fetchone()[0]
        self.assertEqual(local_uid, remote_uid)

        self.set_timestamp(self.db_a, remote_id, "edited remotely", "2099-01-01 00:00:00")
        self.export()
        self.assertEqual(self.import_to_b()["updated"], 1)
        self.assertEqual(self.db_b.list_concerts()[0]["notes"], "edited remotely")

    def test_band_rename_follows_the_sync_id(self) -> None:
        concert_id = self.add_show(self.db_a, band="Old Name")
        band_id = self.db_a.connection.execute(
            "SELECT id FROM bands WHERE name = ?", ("Old Name",)
        ).fetchone()[0]
        self.export()
        self.import_to_b()

        self.db_a.rename_band(band_id, "New Name")
        self.export()
        self.import_to_b()

        self.assertEqual(self.db_b.list_concerts()[0]["band"], "New Name")
        self.assertEqual(self.db_b.list_bands(), ["New Name"])

    def test_removed_photo_follows_the_export(self) -> None:
        concert_id = self.add_show(self.db_a)
        self.attach_photo(self.db_a, concert_id, self.photo())
        self.export()
        self.import_to_b()
        old_file = Path(
            self.db_b.list_concerts()[0]["setlistImage"].removeprefix("file://")
        )

        with self.db_a.connection:
            self.db_a.connection.execute(
                "UPDATE concerts SET setlist_image = '', updated_at = ? WHERE id = ?",
                ("2099-01-01 00:00:00", concert_id),
            )
        old_file.unlink()
        self.export()
        self.import_to_b()

        self.assertEqual(self.db_b.list_concerts()[0]["setlistImage"], "")
        self.assertFalse(old_file.exists())

    def test_rejects_files_that_are_not_exports(self) -> None:
        plain = self.root / "notes.txt"
        plain.write_text("not an export", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "isn't a Concert Log export"):
            transfer.import_archive(self.db_b, plain)

        other_zip = self.root / "other.zip"
        with zipfile.ZipFile(other_zip, "w") as archive:
            archive.writestr("readme.txt", "hello")
        with self.assertRaisesRegex(ValueError, "isn't a Concert Log export"):
            transfer.import_archive(self.db_b, other_zip)

        future = self.root / "future.zip"
        with zipfile.ZipFile(future, "w") as archive:
            archive.writestr(
                transfer.MANIFEST,
                json.dumps({"format": transfer.FORMAT, "version": 99}),
            )
        with self.assertRaisesRegex(ValueError, "newer version"):
            transfer.import_archive(self.db_b, future)

        self.assertEqual(self.db_b.stats()["shows"], 0)

    def test_sync_ids_are_created_and_backfilled(self) -> None:
        concert_id = self.add_show(self.db_a)
        uid = self.db_a.connection.execute(
            "SELECT uid FROM concerts WHERE id = ?", (concert_id,)
        ).fetchone()[0]
        self.assertTrue(uid)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.db"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE bands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE concerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    band_id INTEGER NOT NULL REFERENCES bands(id),
                    date TEXT NOT NULL,
                    venue TEXT NOT NULL DEFAULT '',
                    city TEXT NOT NULL DEFAULT '',
                    other_bands TEXT NOT NULL DEFAULT '[]',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                INSERT INTO bands(name) VALUES ('Legacy Band');
                INSERT INTO concerts(band_id, date) VALUES (1, '2020-01-01');
                """
            )
            connection.commit()
            connection.close()

            legacy = ConcertDB(path)
            try:
                uids = [
                    row[0]
                    for row in legacy.connection.execute("SELECT uid FROM concerts")
                ]
                self.assertEqual(len(uids), 1)
                self.assertTrue(uids[0])
            finally:
                legacy.close()


if __name__ == "__main__":
    unittest.main()
