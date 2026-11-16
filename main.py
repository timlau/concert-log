#!/usr/bin/env python3
"""Concert Log entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QPalette
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle

from concert_log.backend import Backend
from concert_log.database import ConcertDB
from concert_log.theme import font_family, load_theme

BASE_DIR = Path(__file__).resolve().parent
QML_DIR = BASE_DIR / "qml"
ASSET_DIR = BASE_DIR / "assets"


def build_palette(theme: dict[str, str]) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(theme["background"]))
    palette.setColor(QPalette.WindowText, QColor(theme["foreground"]))
    palette.setColor(QPalette.Base, QColor(theme["inputBackground"]))
    palette.setColor(QPalette.AlternateBase, QColor(theme["surface"]))
    palette.setColor(QPalette.Text, QColor(theme["foreground"]))
    palette.setColor(QPalette.PlaceholderText, QColor(theme["foregroundDim"]))
    palette.setColor(QPalette.Button, QColor(theme["surfaceRaised"]))
    palette.setColor(QPalette.ButtonText, QColor(theme["foreground"]))
    palette.setColor(QPalette.BrightText, QColor(theme["red"]))
    palette.setColor(QPalette.Highlight, QColor(theme["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor(theme["onAccent"]))
    palette.setColor(QPalette.ToolTipBase, QColor(theme["surfaceRaised"]))
    palette.setColor(QPalette.ToolTipText, QColor(theme["foreground"]))
    palette.setColor(QPalette.Link, QColor(theme["accent"]))
    palette.setColor(QPalette.LinkVisited, QColor(theme["magenta"]))
    return palette


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concert Log")
    parser.add_argument("--db", help="path to the SQLite database (or set CONCERT_LOG_DB)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="load the QML, report warnings/errors, then exit",
    )
    parser.add_argument("--screenshot", metavar="FILE", help="render a screenshot and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))

    QQuickStyle.setStyle("Basic")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Concert Log")
    app.setApplicationDisplayName("Concert Log")
    app.setOrganizationName("Concert Log")
    app.setDesktopFileName("concert-log")

    theme = load_theme()
    family = font_family(QFontDatabase.families())
    theme["fontFamily"] = family
    theme["monoFamily"] = family

    app.setPalette(build_palette(theme))
    app.setFont(QFont(family, 10))

    icon_path = ASSET_DIR / "concert-log.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    database = ConcertDB(args.db)
    backend = Backend(database)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("theme", theme)
    engine.addImportPath(str(QML_DIR))

    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(str(item) for item in items))

    engine.load(str(QML_DIR / "Main.qml"))
    if not engine.rootObjects():
        for warning in warnings:
            print(warning, file=sys.stderr)
        return 1

    window = engine.rootObjects()[0]
    if isinstance(window, QQuickWindow):
        window.setIcon(QIcon(str(icon_path))) if icon_path.exists() else None

    if args.screenshot:
        def grab() -> None:
            if isinstance(window, QQuickWindow):
                window.grabWindow().save(args.screenshot)
            app.quit()

        QTimer.singleShot(900, grab)
    elif args.check:
        def finish() -> None:
            for warning in warnings:
                print(warning, file=sys.stderr)
            if warnings:
                print(f"{len(warnings)} QML warning(s)", file=sys.stderr)
            app.quit()

        QTimer.singleShot(700, finish)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
