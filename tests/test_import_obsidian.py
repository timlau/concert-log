from __future__ import annotations

import datetime as dt
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from concert_log.database import ConcertDB
from import_obsidian import main, parse_note

NOTE = """---
Dato: 2022-05-21
Band: Junkyard Drive
Andre Bands:
  - Søren Andersen
  - Grumpynators
Arrangement: Canonball Festival
SlutDato: 2022-05-22
Spillested: Næstved
Deltaget: true
Category: concert
---
"""


class ImportNoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_parses_scalars_and_block_lists(self) -> None:
        show, reason = parse_note(self.write("note.md", NOTE))
        self.assertEqual(reason, "")
        self.assertIsNotNone(show)
        self.assertEqual(show["band"], "Junkyard Drive")
        self.assertEqual(show["date"], "2022-05-21")
        self.assertEqual(show["venue"], "Næstved")
        self.assertEqual(show["otherBands"], ["Søren Andersen", "Grumpynators"])
        self.assertEqual(show["event"], "Canonball Festival")
        self.assertEqual(show["endDate"], "2022-05-22")
        self.assertEqual(show["notes"], "")

    def test_uses_file_contents_not_the_filename(self) -> None:
        text = NOTE.replace("2022-05-21", "1999-12-31").replace(
            "Junkyard Drive", "Inside Band"
        )
        show, _ = parse_note(self.write("2099-01-01 Wrong Name.md", text))
        self.assertIsNotNone(show)
        self.assertEqual(show["date"], "1999-12-31")
        self.assertEqual(show["band"], "Inside Band")

    def test_empty_band_is_not_taken_from_filename(self) -> None:
        text = "---\nDato: 2022-05-21\nBand:\nDeltaget: true\n---\n"
        show, reason = parse_note(self.write("2022-05-21 File Band.md", text))
        self.assertIsNone(show)
        self.assertEqual(reason, "no band")

    def test_band_list_keeps_extra_names_as_support(self) -> None:
        text = "---\nDato: 2024-05-10\nBand:\n  - Headliner\n  - Support\n---\n"
        show, _ = parse_note(self.write("note.md", text))
        self.assertIsNotNone(show)
        self.assertEqual(show["band"], "Headliner")
        self.assertEqual(show["otherBands"], ["Support"])

    def test_not_attended_can_be_included(self) -> None:
        text = NOTE.replace("Deltaget: true", "Deltaget: False")
        path = self.write("note.md", text)

        show, reason = parse_note(path)
        self.assertIsNone(show)
        self.assertEqual(reason, "not attended")

        show, _ = parse_note(path, include_not_attended=True)
        self.assertIsNotNone(show)

    def test_future_planned_show_is_imported(self) -> None:
        text = (
            NOTE.replace("2022-05-21", "2026-11-21")
            .replace("SlutDato: 2022-05-22\n", "")
            .replace("Deltaget: true", "Deltaget: False")
        )
        show, reason = parse_note(
            self.write("note.md", text), today=dt.date(2026, 11, 16)
        )
        self.assertEqual(reason, "")
        self.assertIsNotNone(show)
        self.assertEqual(show["date"], "2026-11-21")
        self.assertEqual(show["endDate"], "")

    def test_end_date_must_follow_start_date(self) -> None:
        text = NOTE.replace("SlutDato: 2022-05-22", "SlutDato: 2022-05-20")
        show, reason = parse_note(self.write("note.md", text))
        self.assertIsNone(show)
        self.assertEqual(reason, "end date before start")


class ImportRunTests(unittest.TestCase):
    def test_import_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            notes = root / "notes"
            notes.mkdir()
            (notes / "note.md").write_text(NOTE, encoding="utf-8")
            db_path = root / "concerts.db"

            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(notes), "--db", str(db_path)]), 0)
                self.assertEqual(main([str(notes), "--db", str(db_path)]), 0)

            database = ConcertDB(db_path)
            try:
                self.assertEqual(database.stats()["shows"], 1)
                show = database.list_concerts()[0]
                self.assertEqual(show["band"], "Junkyard Drive")
                self.assertEqual(show["event"], "Canonball Festival")
                self.assertEqual(show["endDate"], "2022-05-22")
                self.assertEqual(show["otherBands"], ["Søren Andersen", "Grumpynators"])
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
