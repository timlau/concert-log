"""Build "add event" links for Google Calendar.

Shows in the log have only dates, no clock times, so events are created as
all-day events. Google treats the end date in ``dates`` as exclusive, hence the
logged end date is advanced by one day.
"""

from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any
from urllib.parse import urlencode

BASE_URL = "https://calendar.google.com/calendar/render"


def event_url(concert: dict[str, Any]) -> str:
    """Return a Google Calendar template URL for a concert from ``list_concerts``."""
    start = date_type.fromisoformat(str(concert["date"]))
    raw_end = str(concert.get("endDate") or "")
    end = date_type.fromisoformat(raw_end) if raw_end else start
    if end < start:
        raise ValueError("End date cannot be before the start date.")
    end += timedelta(days=1)

    band = str(concert.get("band") or "").strip()
    event = str(concert.get("event") or "").strip()
    title = f"{band} ({event})" if band and event else band or event or "Concert"

    details: list[str] = []
    support = concert.get("otherBands") or []
    if not isinstance(support, (list, tuple)):
        support = []
    other_bands = ", ".join(
        name for name in (str(item).strip() for item in support) if name
    )
    if other_bands:
        details.append(f"With {other_bands}")
    notes = str(concert.get("notes") or "").strip()
    if notes:
        details.append(notes)

    location = str(concert.get("place") or "").strip()
    if not location:
        venue = str(concert.get("venue") or "").strip()
        city = str(concert.get("city") or "").strip()
        location = " · ".join(part for part in (venue, city) if part)

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{start:%Y%m%d}/{end:%Y%m%d}",
    }
    if details:
        params["details"] = "\n".join(details)
    if location:
        params["location"] = location
    return f"{BASE_URL}?{urlencode(params)}"
