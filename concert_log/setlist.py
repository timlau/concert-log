"""Setlist photo storage: resize imported images and keep them beside the DB."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QImageReader

MAX_HEIGHT = 1024
JPEG_QUALITY = 90


def directory_for(db_path: Path) -> Path:
    return db_path.parent / "setlists"


def local_path(source: str) -> Path:
    """Turn a local path or a `file://` URL from QML into a filesystem path."""
    text = str(source or "").strip()
    if not text:
        raise ValueError("Choose a file first.")
    if text.startswith("file:"):
        local = QUrl(text).toLocalFile()
        if local:
            text = local
    return Path(text).expanduser()


def source_to_path(source: str) -> Path:
    """Resolve a local path or URL and make sure the file exists."""
    if not str(source or "").strip():
        raise ValueError("Choose a setlist photo first.")
    path = local_path(source)
    if not path.is_file():
        raise ValueError("That setlist photo could not be found.")
    return path


def load_scaled(source: str) -> QImage:
    """Load an image, capping its height at MAX_HEIGHT and keeping its ratio."""
    reader = QImageReader(str(source_to_path(source)))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise ValueError("That file could not be read as an image.")
    if image.height() > MAX_HEIGHT:
        image = image.scaledToHeight(MAX_HEIGHT, Qt.SmoothTransformation)
    return image


def save_image(image: QImage, directory: Path, concert_id: int) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"concert-{int(concert_id)}-{uuid4().hex[:8]}.jpg"
    target = directory / filename
    if not image.save(str(target), "JPEG", JPEG_QUALITY):
        raise ValueError("The setlist photo could not be saved.")
    return filename


def remove_image(directory: Path, filename: str) -> None:
    if not filename:
        return
    target = directory / Path(filename).name
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass


def image_url(directory: Path, filename: str) -> str:
    if not filename:
        return ""
    target = directory / Path(filename).name
    return target.as_uri() if target.is_file() else ""
