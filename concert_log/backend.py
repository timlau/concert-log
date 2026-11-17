"""QML-facing backend: read-only properties plus a handful of slots."""

from __future__ import annotations

import sqlite3
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import setlist, transfer
from .database import ConcertDB


class Backend(QObject):
    concertsChanged = Signal()
    bandsChanged = Signal()

    def __init__(self, database: ConcertDB, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = database
        self._search = ""
        self._concerts: list[dict[str, Any]] = []
        self._stats: dict[str, int] = {"shows": 0, "bands": 0, "venues": 0}
        self._bands: list[str] = []
        self._band_rows: list[dict[str, Any]] = []
        self._events: list[str] = []
        self._venues: list[str] = []
        self._cities: list[str] = []
        self.reload()

    # ------------------------------------------------------------- properties

    @Property("QVariantList", notify=concertsChanged)
    def concerts(self) -> list[dict[str, Any]]:
        return self._concerts

    @Property("QVariantMap", notify=concertsChanged)
    def stats(self) -> dict[str, int]:
        return self._stats

    @Property(str, notify=concertsChanged)
    def search(self) -> str:
        return self._search

    @Property("QVariantList", notify=bandsChanged)
    def bands(self) -> list[str]:
        return self._bands

    @Property("QVariantList", notify=bandsChanged)
    def bandRows(self) -> list[dict[str, Any]]:
        return self._band_rows

    @Property("QVariantList", notify=bandsChanged)
    def events(self) -> list[str]:
        return self._events

    @Property("QVariantList", notify=bandsChanged)
    def venues(self) -> list[str]:
        return self._venues

    @Property("QVariantList", notify=bandsChanged)
    def cities(self) -> list[str]:
        return self._cities

    # ------------------------------------------------------------------ slots

    @Slot(str)
    def setSearch(self, text: str) -> None:
        if text == self._search:
            return
        self._search = text
        try:
            self._concerts = self._db.list_concerts(text)
        except sqlite3.Error:
            self._concerts = []
        self.concertsChanged.emit()

    @Slot("QVariantMap", result="QVariantMap")
    def saveConcert(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        setlist_source = str(payload.pop("setlistSource", "") or "")
        clear_setlist = bool(payload.pop("clearSetlist", False))
        try:
            image = setlist.load_scaled(setlist_source) if setlist_source else None
            concert_id = self._db.save_concert(payload)
            if image is not None or clear_setlist:
                previous = self._db.get_setlist_filename(concert_id)
                if image is not None:
                    filename = setlist.save_image(
                        image, self._db.setlist_dir, concert_id
                    )
                    self._db.set_setlist_image(concert_id, filename)
                else:
                    self._db.set_setlist_image(concert_id, "")
                setlist.remove_image(self._db.setlist_dir, previous)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except OSError as error:
            return {"ok": False, "error": f"Setlist photo: {error}"}
        except sqlite3.Error as error:
            return {"ok": False, "error": f"Database error: {error}"}
        self.reload()
        return {"ok": True, "id": concert_id}

    @Slot(int, result="QVariantMap")
    def deleteConcert(self, concert_id: int) -> dict[str, Any]:
        filename = ""
        try:
            filename = self._db.delete_concert(concert_id)
        except sqlite3.Error as error:
            return {"ok": False, "error": f"Database error: {error}"}
        setlist.remove_image(self._db.setlist_dir, filename)
        self.reload()
        return {"ok": True}

    @Slot(str, result="QVariantMap")
    def exportData(self, destination: str) -> dict[str, Any]:
        try:
            result = transfer.export_archive(self._db, destination)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except OSError as error:
            return {"ok": False, "error": f"Could not write the export: {error}"}
        return {"ok": True, **result}

    @Slot(str, result="QVariantMap")
    def importData(self, source: str) -> dict[str, Any]:
        try:
            result = transfer.import_archive(self._db, source)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except OSError as error:
            return {"ok": False, "error": f"Could not read the export: {error}"}
        except sqlite3.Error as error:
            return {"ok": False, "error": f"Database error: {error}"}
        self.reload()
        return {"ok": True, **result}

    @Slot(str, result="QVariantMap")
    def addBand(self, name: str) -> dict[str, Any]:
        try:
            band_id = self._db.add_band(name)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except sqlite3.Error as error:
            return {"ok": False, "error": f"Database error: {error}"}
        self.reload()
        return {"ok": True, "id": band_id}

    @Slot(int, str, result="QVariantMap")
    def renameBand(self, band_id: int, name: str) -> dict[str, Any]:
        try:
            self._db.rename_band(band_id, name)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except sqlite3.Error as error:
            return {"ok": False, "error": f"Database error: {error}"}
        self.reload()
        return {"ok": True}

    @Slot(int, result="QVariantMap")
    def deleteBand(self, band_id: int) -> dict[str, Any]:
        try:
            self._db.delete_band(band_id)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        except sqlite3.Error as error:
            return {"ok": False, "error": f"Database error: {error}"}
        self.reload()
        return {"ok": True}

    # ----------------------------------------------------------------- helpers

    def reload(self) -> None:
        try:
            self._concerts = self._db.list_concerts(self._search)
            self._stats = self._db.stats()
            self._bands = self._db.list_bands()
            self._band_rows = self._db.list_band_rows()
            self._events = self._db.list_events()
            self._venues = self._db.list_places("venue")
            self._cities = self._db.list_places("city")
        except sqlite3.Error:
            self._concerts = []
            self._stats = {"shows": 0, "bands": 0, "venues": 0}
            self._bands = []
            self._band_rows = []
            self._events = []
            self._venues = []
            self._cities = []
        self.concertsChanged.emit()
        self.bandsChanged.emit()
