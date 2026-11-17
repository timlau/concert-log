from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from concert_log.database import ConcertDB


class ConcertDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = ConcertDB(Path(self.tmp.name) / "concerts.db")

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def add_show(self, **overrides):
        data = {
            "band": "Godspeed You! Black Emperor",
            "date": "2025-06-14",
            "venue": "Barbican",
            "city": "London",
            "otherBands": ["Mogwai", "Low"],
            "notes": "Very loud.",
        }
        data.update(overrides)
        return self.db.save_concert(data)

    def test_round_trip_and_stats(self) -> None:
        concert_id = self.add_show()
        shows = self.db.list_concerts()
        self.assertEqual(len(shows), 1)
        show = shows[0]
        self.assertEqual(show["id"], concert_id)
        self.assertEqual(show["band"], "Godspeed You! Black Emperor")
        self.assertEqual(show["date"], "2025-06-14")
        self.assertEqual(show["place"], "Barbican · London")
        self.assertEqual(show["otherBands"], ["Mogwai", "Low"])
        self.assertEqual(self.db.stats(), {"shows": 1, "bands": 3, "venues": 1})

    def test_search_covers_support_acts_places_and_events(self) -> None:
        self.add_show(event="Copenhell")
        self.assertEqual(len(self.db.list_concerts("mogwai")), 1)
        self.assertEqual(len(self.db.list_concerts("london")), 1)
        self.assertEqual(len(self.db.list_concerts("copenhell")), 1)
        self.assertEqual(len(self.db.list_concerts("portishead")), 0)

    def test_event_and_multi_day_range(self) -> None:
        self.add_show(event="Copenhell", endDate="2025-06-17")
        show = self.db.list_concerts()[0]
        self.assertEqual(show["event"], "Copenhell")
        self.assertEqual(show["endDate"], "2025-06-17")
        self.assertEqual(show["dateRange"], "2025-06-14 – 2025-06-17")
        self.assertEqual(show["dateLabel"], "Sat, 14 Jun 2025 – Tue, 17 Jun 2025")
        self.assertEqual(self.db.list_events(), ["Copenhell"])

    def test_same_day_end_date_is_normalized(self) -> None:
        self.add_show(endDate="2025-06-14")
        show = self.db.list_concerts()[0]
        self.assertEqual(show["endDate"], "")
        self.assertEqual(show["dateRange"], "2025-06-14")

    def test_future_and_past_status(self) -> None:
        self.add_show(date="2025-06-14")

        upcoming = self.db.list_concerts(today=date(2025, 6, 10))[0]
        self.assertEqual(upcoming["status"], "upcoming")
        self.assertEqual(upcoming["statusLabel"], "UPCOMING")
        self.assertEqual(upcoming["statusHint"], "In 4 days")
        self.assertEqual(upcoming["daysUntil"], 4)
        self.assertTrue(upcoming["isFuture"])

        tomorrow = self.db.list_concerts(today=date(2025, 6, 13))[0]
        self.assertEqual(tomorrow["statusHint"], "Tomorrow")

        today = self.db.list_concerts(today=date(2025, 6, 14))[0]
        self.assertEqual(today["status"], "ongoing")
        self.assertEqual(today["statusLabel"], "TODAY")
        self.assertEqual(today["statusHint"], "Happening now")

        past = self.db.list_concerts(today=date(2025, 6, 15))[0]
        self.assertEqual(past["status"], "past")
        self.assertEqual(past["statusLabel"], "")
        self.assertTrue(past["isPast"])

    def test_multi_day_event_status(self) -> None:
        self.add_show(event="Copenhell", endDate="2025-06-17")

        ongoing = self.db.list_concerts(today=date(2025, 6, 15))[0]
        self.assertEqual(ongoing["statusLabel"], "ONGOING")
        self.assertEqual(ongoing["statusHint"], "Ends 17 Jun")

        last_day = self.db.list_concerts(today=date(2025, 6, 17))[0]
        self.assertEqual(last_day["status"], "ongoing")
        self.assertEqual(last_day["statusHint"], "Ends today")

        day_after = self.db.list_concerts(today=date(2025, 6, 18))[0]
        self.assertEqual(day_after["status"], "past")

    def test_edit_keeps_bands_and_deduplicates(self) -> None:
        concert_id = self.add_show()
        self.db.save_concert(
            {
                "id": concert_id,
                "band": "Godspeed You! Black Emperor",
                "date": "2025-06-15",
                "venue": "Barbican",
                "city": "London",
                "otherBands": ["Low", "low", "Godspeed You! Black Emperor"],
                "notes": "",
            }
        )
        show = self.db.list_concerts()[0]
        self.assertEqual(show["date"], "2025-06-15")
        self.assertEqual(show["otherBands"], ["Low"])

    def test_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "headliner"):
            self.db.save_concert({"band": " ", "date": "2025-01-01"})
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            self.db.save_concert({"band": "Portishead", "date": "next friday"})
        with self.assertRaisesRegex(ValueError, "date is required"):
            self.db.save_concert({"band": "Portishead", "date": ""})
        with self.assertRaisesRegex(ValueError, "end date needs"):
            self.db.save_concert(
                {"band": "Portishead", "date": "2025-01-01", "endDate": "later"}
            )
        with self.assertRaisesRegex(ValueError, "end date cannot be before"):
            self.db.save_concert(
                {"band": "Portishead", "date": "2025-01-02", "endDate": "2025-01-01"}
            )

    def test_band_rename_and_delete_rules(self) -> None:
        self.add_show()
        rows = {row["name"]: row for row in self.db.list_band_rows()}
        self.assertEqual(rows["Mogwai"]["count"], 1)
        self.db.rename_band(rows["Mogwai"]["id"], "Mogwai!")
        self.assertIn("Mogwai!", self.db.list_bands())

        with self.assertRaisesRegex(ValueError, "headlines"):
            self.db.delete_band(rows["Godspeed You! Black Emperor"]["id"])

        self.db.delete_band(rows["Mogwai"]["id"])
        self.assertNotIn("Mogwai!", self.db.list_bands())
        self.assertEqual(self.db.list_concerts()[0]["otherBands"], ["Low"])

    def test_delete_concert(self) -> None:
        concert_id = self.add_show()
        self.db.delete_concert(concert_id)
        self.assertEqual(self.db.list_concerts(), [])
        self.assertEqual(self.db.stats()["shows"], 0)

    def test_setlist_image_round_trip_and_delete(self) -> None:
        concert_id = self.add_show()
        self.assertEqual(self.db.list_concerts()[0]["setlistImage"], "")

        self.db.setlist_dir.mkdir(parents=True, exist_ok=True)
        (self.db.setlist_dir / "concert-1-abc.jpg").write_bytes(b"photo")
        self.db.set_setlist_image(concert_id, "concert-1-abc.jpg")

        show = self.db.list_concerts()[0]
        self.assertTrue(show["setlistImage"].startswith("file://"))
        self.assertTrue(show["setlistImage"].endswith("concert-1-abc.jpg"))

        self.db.save_concert(
            {"id": concert_id, "band": "Godspeed You! Black Emperor", "date": "2025-06-14"}
        )
        self.assertEqual(self.db.get_setlist_filename(concert_id), "concert-1-abc.jpg")
        self.assertEqual(self.db.delete_concert(concert_id), "concert-1-abc.jpg")

    def test_adds_setlist_column_to_existing_database(self) -> None:
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
                INSERT INTO bands(name) VALUES ('Old Band');
                INSERT INTO concerts(band_id, date) VALUES (1, '2024-01-01');
                """
            )
            connection.commit()
            connection.close()

            database = ConcertDB(path)
            try:
                columns = {
                    str(row["name"])
                    for row in database.connection.execute(
                        "PRAGMA table_info(concerts)"
                    )
                }
                self.assertIn("setlist_image", columns)
                self.assertEqual(database.list_concerts()[0]["setlistImage"], "")
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
