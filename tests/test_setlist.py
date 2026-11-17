from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage

from concert_log import setlist


class SetlistImageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_image(self, width: int, height: int) -> Path:
        image = QImage(width, height, QImage.Format_RGB32)
        image.fill(0xFF336699)
        path = self.dir / "photo.png"
        self.assertTrue(image.save(str(path), "PNG"))
        return path

    def test_tall_image_is_capped_at_1024(self) -> None:
        image = setlist.load_scaled(str(self.make_image(600, 2048)))
        self.assertEqual(image.height(), 1024)
        self.assertEqual(image.width(), 300)

    def test_small_image_keeps_its_size(self) -> None:
        image = setlist.load_scaled(str(self.make_image(320, 480)))
        self.assertEqual((image.width(), image.height()), (320, 480))

    def test_round_trip_and_removal(self) -> None:
        image = setlist.load_scaled(str(self.make_image(400, 800)))
        directory = self.dir / "setlists"
        filename = setlist.save_image(image, directory, 7)
        self.assertTrue(filename.startswith("concert-7-"))
        self.assertTrue(setlist.image_url(directory, filename).startswith("file://"))
        setlist.remove_image(directory, filename)
        self.assertEqual(setlist.image_url(directory, filename), "")

    def test_rejects_non_image(self) -> None:
        path = self.dir / "note.txt"
        path.write_text("not a photo", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "could not be read"):
            setlist.load_scaled(str(path))


if __name__ == "__main__":
    unittest.main()
