from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from concert_log import markdown_export  # noqa: E402
from concert_log.backend import Backend  # noqa: E402
from concert_log.database import ConcertDB  # noqa: E402

TODAY = date(2026, 11, 30)


class MarkdownExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = ConcertDB(self.root / "concerts.db")
        self.db.save_concert(
            {
                "band": "Junkyard Drive",
                "date": "2019-01-26",
                "venue": "gimle",
                "otherBands": [],
            }
        )
        self.db.save_concert(
            {
                "band": "Mogwai",
                "date": "2026-12-05",
                "event": "Nightmare Before Christmas",
                "venue": "Vega",
                "otherBands": ["Low"],
            }
        )

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def show(self, date_string: str) -> dict:
        return next(
            show for show in self.db.list_concerts() if show["date"] == date_string
        )

    def test_frontmatter_matches_expected_note(self) -> None:
        note = markdown_export.frontmatter(self.show("2019-01-26"), TODAY)
        self.assertEqual(
            note,
            "---\n"
            "Date: 2019-01-26\n"
            "Artist: Junkyard Drive\n"
            "Other Artists: \n"
            "Event: \n"
            "Venue: gimle\n"
            "Participaed: True\n"
            "Category: concert\n"
            "--- \n",
        )

    def test_upcoming_shows_are_not_marked_as_participated(self) -> None:
        note = markdown_export.frontmatter(self.show("2026-12-05"), TODAY)
        self.assertIn("Participaed: False\n", note)
        self.assertIn("Other Artists: Low\n", note)
        self.assertIn("Event: Nightmare Before Christmas\n", note)

    def test_filename_uses_date_artist_and_venue(self) -> None:
        self.assertEqual(
            markdown_export.note_filename(self.show("2019-01-26")),
            "2019-01-26 Junkyard Drive gimle.md",
        )

    def test_filename_replaces_unsafe_characters(self) -> None:
        name = markdown_export.note_filename(
            {"date": "2020-02-29", "band": "AC/DC", "venue": "Rock: Club?"}
        )
        self.assertEqual(name, "2020-02-29 AC DC Rock Club.md")

    def test_config_directory_is_read_from_toml(self) -> None:
        config = self.root / "config.toml"
        config.write_text(
            'markdown_export_dir = "~/notes/concerts"\n', encoding="utf-8"
        )
        with patch.dict(os.environ, {"HOME": str(self.root)}):
            directory = markdown_export.configured_directory(config)
        self.assertEqual(directory, self.root / "notes/concerts")

    def test_config_directory_reports_missing_or_empty_setting(self) -> None:
        missing = self.root / "missing.toml"
        with self.assertRaisesRegex(ValueError, "No Markdown export folder configured"):
            markdown_export.configured_directory(missing)

        empty = self.root / "empty.toml"
        empty.write_text('markdown_export_dir = ""\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "markdown_export_dir"):
            markdown_export.configured_directory(empty)

    def test_export_writes_and_overwrites_notes(self) -> None:
        destination = self.root / "notes"
        config = self.root / "config.toml"
        config.write_text(
            f'markdown_export_dir = "{destination}"\n', encoding="utf-8"
        )
        existing = destination / "2019-01-26 Junkyard Drive gimle.md"
        destination.mkdir()
        existing.write_text("old content", encoding="utf-8")

        result = markdown_export.export_notes(
            self.db, config_path=config, today=TODAY
        )

        self.assertEqual(result, {"directory": str(destination), "shows": 2})
        self.assertIn("Artist: Junkyard Drive", existing.read_text(encoding="utf-8"))
        self.assertTrue(
            (destination / "2026-12-05 Mogwai Vega.md").is_file()
        )
        self.assertEqual(len(list(destination.glob("*.md"))), 2)

    def test_backend_slot_reports_missing_config(self) -> None:
        config_home = self.root / "config"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_home)}):
            result = Backend(self.db).exportMarkdown()
        self.assertFalse(result["ok"])
        self.assertIn("config.toml", result["error"])

    def test_backend_slot_exports_notes(self) -> None:
        config_home = self.root / "config"
        config = config_home / "concert-log" / "config.toml"
        config.parent.mkdir(parents=True)
        destination = self.root / "notes"
        config.write_text(
            f'markdown_export_dir = "{destination}"\n', encoding="utf-8"
        )
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_home)}):
            result = Backend(self.db).exportMarkdown()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["shows"], 2)
        self.assertEqual(len(list(destination.glob("*.md"))), 2)


if __name__ == "__main__":
    unittest.main()
