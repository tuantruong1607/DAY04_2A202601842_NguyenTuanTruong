"""Adapter over AeroDataBox via RapidAPI (https://doc.aerodatabox.com/).

Isolates the tool layer from AeroDataBox's URL/response shape. Endpoints used:

- Flight status by number:  GET /flights/number/{number}[/{dateFrom}/{dateTo}]
- Airport FIDS (arrivals/departures) by ICAO or IATA:
  GET /flights/airports/{icao|iata}/{code}/{fromLocal}/{toLocal}?direction=Arrival|Departure|Both
- Airport search by free-text term: GET /airports/search/term?q=
- Airport lookup by code:           GET /airports/{icao|iata}/{code}

`fromLocal`/`toLocal` are local datetimes without timezone offset, e.g.
"2026-08-15T08:00". Most RapidAPI plans cap the FIDS window at 12 hours per
call, so callers should keep windows within that.
"""
from __future__ import annotations

import os
from typing import Any

import requests

TIMEOUT = 30


class AeroDataBoxError(Exception):
    pass


class AeroDataBoxAdapter:
    def __init__(self, api_key: str | None = None, host: str | None = None) -> None:
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        self.host = host or os.getenv("RAPIDAPI_AERODATABOX_HOST", "aerodatabox.p.rapidapi.com")
        self.base_url = f"https://{self.host}"

    def _require_key(self) -> str:
        if not self.api_key:
            raise AeroDataBoxError("Missing RAPIDAPI_KEY env var")
        return self.api_key

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        key = self._require_key()
        headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": self.host}
        response = requests.get(f"{self.base_url}{path}", headers=headers, params=params, timeout=TIMEOUT)
        if response.status_code in (401, 403):
            raise AeroDataBoxError(f"AeroDataBox auth rejected (HTTP {response.status_code}). Check RAPIDAPI_KEY.")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def search_airports(self, term: str, limit: int = 5) -> Any:
        return self._get("/airports/search/term", params={"q": term, "limit": limit})

    def get_airport(self, code: str, *, code_type: str = "iata") -> Any:
        if code_type not in {"iata", "icao"}:
            raise AeroDataBoxError(f"code_type must be 'iata' or 'icao', got {code_type!r}")
        return self._get(f"/airports/{code_type}/{code}")

    def get_flight_status(
        self,
        flight_number: str,
        date_from: str | None = None,
        date_to: str | None = None,
        *,
        with_aircraft_image: bool = False,
        with_location: bool = False,
    ) -> Any:
        if date_from and date_to:
            path = f"/flights/number/{flight_number}/{date_from}/{date_to}"
        elif date_from:
            path = f"/flights/number/{flight_number}/{date_from}"
        else:
            path = f"/flights/number/{flight_number}"
        return self._get(path, params={
            "withAircraftImage": str(with_aircraft_image).lower(),
            "withLocation": str(with_location).lower(),
        })

    def get_airport_schedule(
        self,
        code: str,
        from_local: str,
        to_local: str,
        *,
        code_type: str = "iata",
        direction: str = "Both",
        with_cancelled: bool = True,
        with_codeshared: bool = True,
    ) -> Any:
        if code_type not in {"iata", "icao"}:
            raise AeroDataBoxError(f"code_type must be 'iata' or 'icao', got {code_type!r}")
        if direction not in {"Both", "Arrival", "Departure"}:
            raise AeroDataBoxError(f"direction must be Both/Arrival/Departure, got {direction!r}")
        path = f"/flights/airports/{code_type}/{code}/{from_local}/{to_local}"
        return self._get(path, params={
            "direction": direction,
            "withLeg": "true",
            "withCancelled": str(with_cancelled).lower(),
            "withCodeshared": str(with_codeshared).lower(),
            "withPrivate": "false",
            "withLocation": "false",
        })
