"""Render a preview screenshot of the app for development.

Usage:
    QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
        .venv/bin/python tests/render_preview.py output.png [mode]

Modes: list (default), detail, add, bands, date, setlist, sync
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, QTimer, Qt
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from concert_log.backend import Backend  # noqa: E402
from concert_log.database import ConcertDB  # noqa: E402
from concert_log.theme import font_family, load_theme  # noqa: E402
from main import build_palette  # noqa: E402


def invoke(obj: object, method: str) -> None:
    QMetaObject.invokeMethod(obj, method, Qt.DirectConnection)


def main() -> int:
    output = sys.argv[1] if len(sys.argv) > 1 else "/tmp/concert-log-preview.png"
    mode = sys.argv[2] if len(sys.argv) > 2 else "list"

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    theme = load_theme()
    family = font_family(QFontDatabase.families())
    theme["fontFamily"] = family
    theme["monoFamily"] = family
    app.setPalette(build_palette(theme))
    app.setFont(QFont(family, 10))

    database = ConcertDB()
    backend = Backend(database)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)
    engine.addImportPath(str(ROOT / "qml"))
    engine.load(str(ROOT / "qml/Main.qml"))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]

    def prepare() -> None:
        if mode in {"detail", "add", "date", "setlist"}:
            invoke(window, "selectFirst")
        if mode in {"add", "date"}:
            invoke(window, "openAdd")
        if mode == "date":
            dialog = window.findChild(QObject, "concertDialog")
            if dialog is not None:
                invoke(dialog, "openDatePicker")
        if mode == "setlist":
            invoke(window, "openSetlist")
        if mode in {"bands", "sync"}:
            name = "bandsDialog" if mode == "bands" else "syncDialog"
            dialog = window.findChild(QObject, name)
            if dialog is not None:
                invoke(dialog, "open")

    def grab() -> None:
        if isinstance(window, QQuickWindow):
            window.grabWindow().save(output)
        app.quit()

    QTimer.singleShot(400, prepare)
    QTimer.singleShot(1000, grab)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
