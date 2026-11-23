from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from concert_log.google_calendar import event_url


class GoogleCalendarLinkTests(unittest.TestCase):
    def show(self, **overrides):
        data = {
            "band": "Godspeed You! Black Emperor",
            "event": "",
            "date": "2025-06-14",
            "endDate": "",
            "venue": "Barbican",
            "city": "London",
            "place": "Barbican · London",
            "otherBands": [],
            "notes": "",
        }
        data.update(overrides)
        return event_url(data)

    def params(self, url):
        return parse_qs(urlparse(url).query)

    def test_single_day_event_is_all_day(self) -> None:
        url = self.show()
        self.assertTrue(url.startswith("https://calendar.google.com/calendar/render?"))
        params = self.params(url)
        self.assertEqual(params["action"], ["TEMPLATE"])
        self.assertEqual(params["text"], ["Godspeed You! Black Emperor"])
        # Google's end date is exclusive.
        self.assertEqual(params["dates"], ["20250614/20250615"])
        self.assertEqual(params["location"], ["Barbican · London"])
        self.assertNotIn("details", params)

    def test_multi_day_event_includes_exclusive_end(self) -> None:
        params = self.params(self.show(endDate="2025-06-17"))
        self.assertEqual(params["dates"], ["20250614/20250618"])

    def test_event_support_and_notes(self) -> None:
        params = self.params(
            self.show(
                event="Copenhell",
                otherBands=["Mogwai", "Low"],
                notes="Very loud.\nGreat crowd.",
            )
        )
        self.assertEqual(params["text"], ["Godspeed You! Black Emperor (Copenhell)"])
        self.assertEqual(params["details"], ["With Mogwai, Low\nVery loud.\nGreat crowd."])

    def test_location_falls_back_to_venue_and_city(self) -> None:
        params = self.params(self.show(place="", venue="Barbican", city="London"))
        self.assertEqual(params["location"], ["Barbican · London"])

    def test_values_are_url_encoded(self) -> None:
        url = self.show(band="Sigur Rós & friends", city="Reykjavík")
        self.assertIn("Sigur+R%C3%B3s+%26+friends", url)
        self.assertEqual(
            self.params(url)["text"], ["Sigur Rós & friends"]
        )

    def test_invalid_dates_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.show(date="not-a-date")
        with self.assertRaises(ValueError):
            self.show(endDate="2025-06-13")


if __name__ == "__main__":
    unittest.main()
