from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from concert_log.theme import load_theme


class ThemeTests(unittest.TestCase):
    def test_reads_omarchy_style_colors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "colors.toml"
            path.write_text(
                'background = "#101010"\n'
                'foreground = "#eeeeee"\n'
                'accent = "#ff0000"\n'
                'red = "#cc0000"\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"CONCERT_LOG_COLORS": str(path)}):
                theme = load_theme()
        self.assertEqual(theme["background"], "#101010")
        self.assertEqual(theme["accent"], "#ff0000")
        self.assertEqual(theme["red"], "#cc0000")
        self.assertIn("selection", theme)

    def test_falls_back_when_file_is_missing(self) -> None:
        with patch.dict(os.environ, {"CONCERT_LOG_COLORS": "/nonexistent/colors.toml"}):
            with patch("concert_log.theme._theme_candidates", return_value=[]):
                theme = load_theme()
        for key in ("background", "foreground", "accent", "red", "green"):
            self.assertTrue(theme[key].startswith("#"), key)
        for key in ("surface", "foregroundMuted", "onAccent", "dangerSoft"):
            self.assertIn(key, theme)


if __name__ == "__main__":
    unittest.main()
