"""Adapter over FlightAPI.io (https://docs.flightapi.io/).

Isolates the tool layer from FlightAPI's URL/response shape so the rest of
the agent never depends on it directly. Endpoints used:

- Airport/airline code lookup: GET /iata/{api_key}?name=&type=airport|airline
- One-way price search:        GET /onewaytrip/{api_key}/{origin}/{destination}/{date}/{adults}/{children}/{infants}/{cabin_class}/{currency}
- Round-trip price search:     GET /roundtrip/{api_key}/{origin}/{destination}/{depart_date}/{return_date}/{adults}/{children}/{infants}/{cabin_class}/{currency}

The price-search response follows a Skyscanner-style itineraries/legs/
segments/carriers shape. That shape is not fully documented publicly, so
`normalize_offers` parses it defensively: any itinerary it cannot confidently
parse is dropped from `items` but its count is reported in `unparsed_count`
rather than guessed at.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

TIMEOUT = 30


class FlightAPIError(Exception):
    pass


class FlightAPIAdapter:
    BASE_URL = "https://api.flightapi.io"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("FLIGHTAPI_KEY")

    def _require_key(self) -> str:
        if not self.api_key:
            raise FlightAPIError("Missing FLIGHTAPI_KEY env var")
        return self.api_key

    def _get(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        if response.status_code == 401 or response.status_code == 403:
            raise FlightAPIError(f"FlightAPI auth rejected (HTTP {response.status_code}). Check FLIGHTAPI_KEY.")
        response.raise_for_status()
        return response.json()

    # ---------------------------------------------------------------- IATA lookup
    def lookup_codes(self, name: str, kind: str = "airport") -> list[dict[str, str]]:
        key = self._require_key()
        if kind not in {"airport", "airline"}:
            raise FlightAPIError(f"kind must be 'airport' or 'airline', got {kind!r}")
        data = self._get(f"{self.BASE_URL}/iata/{key}", params={"name": name, "type": kind})
        rows = data.get("data", data if isinstance(data, list) else [])
        results = []
        for row in rows:
            code = row.get("fs") or row.get("iata") or row.get("code")
            display_name = row.get("name")
            if code and display_name:
                results.append({"code": code, "name": display_name, "type": kind})
        return results

    # ---------------------------------------------------------------- price search
    def search_one_way(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        *,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "Economy",
        currency: str = "USD",
    ) -> dict[str, Any]:
        key = self._require_key()
        url = (
            f"{self.BASE_URL}/onewaytrip/{key}/{origin}/{destination}/{departure_date}"
            f"/{adults}/{children}/{infants}/{cabin_class}/{currency}"
        )
        return self._get(url)

    def search_round_trip(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        *,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "Economy",
        currency: str = "USD",
    ) -> dict[str, Any]:
        key = self._require_key()
        url = (
            f"{self.BASE_URL}/roundtrip/{key}/{origin}/{destination}/{departure_date}/{return_date}"
            f"/{adults}/{children}/{infants}/{cabin_class}/{currency}"
        )
        return self._get(url)


def _segment_summary(
    segment: dict[str, Any],
    carriers_by_id: dict[int, dict[str, str | None]],
    places_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    origin = places_by_id.get(segment.get("origin_place_id"), {})
    destination = places_by_id.get(segment.get("destination_place_id"), {})
    marketing = carriers_by_id.get(segment.get("marketing_carrier_id"), {})
    operating = carriers_by_id.get(segment.get("operating_carrier_id"), {})
    flight_no = segment.get("marketing_flight_number")
    carrier_code = marketing.get("code")
    return {
        # The flight number as it would be booked/searched (IATA carrier code
        # + the number FlightAPI returns), e.g. "VN5351". Falls back to just
        # the bare number if the carrier's IATA code isn't in `carriers`.
        "flight_number": f"{carrier_code}{flight_no}" if carrier_code and flight_no else flight_no,
        "airline": marketing.get("name"),
        "operating_airline": operating.get("name") if operating.get("name") != marketing.get("name") else None,
        "origin": origin.get("display_code"),
        "destination": destination.get("display_code"),
        "departure": segment.get("departure"),
        "arrival": segment.get("arrival"),
    }


def _leg_summary(
    leg: dict[str, Any],
    carriers_by_id: dict[int, dict[str, str | None]],
    places_by_id: dict[int, dict[str, Any]],
    segments_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        origin = places_by_id.get(leg.get("origin_place_id"), {})
        destination = places_by_id.get(leg.get("destination_place_id"), {})
        carrier_ids = leg.get("marketing_carrier_ids") or []
        segment_ids = leg.get("segment_ids") or []
        segments = [
            _segment_summary(segments_by_id[sid], carriers_by_id, places_by_id)
            for sid in segment_ids
            if sid in segments_by_id
        ]
        return {
            "origin": origin.get("display_code"),
            "destination": destination.get("display_code"),
            "departure": leg.get("departure"),
            "arrival": leg.get("arrival"),
            "duration_minutes": leg.get("duration"),
            "stop_count": leg.get("stop_count"),
            "carriers": [carriers_by_id[cid]["name"] for cid in carrier_ids if cid in carriers_by_id and carriers_by_id[cid].get("name")],
            # One entry per segment (a leg with a stop has 2+ segments, each
            # its own flight number) — the actual ticketed flight number(s),
            # never invented: read straight from FlightAPI's segment data.
            "segments": segments,
            "flight_numbers": [s["flight_number"] for s in segments if s.get("flight_number")],
        }
    except AttributeError:
        return None


def normalize_offers(raw: dict[str, Any], currency: str) -> dict[str, Any]:
    """Best-effort parse of a FlightAPI price-search response (Skyscanner-style
    itineraries/legs/places/carriers shape) into flat offers.

    Never invents a price or route: an itinerary that cannot be matched to a
    price and at least one leg is skipped and counted in `unparsed_count`
    instead of appearing in `items`.
    """
    itineraries = raw.get("itineraries") or []
    legs_by_id = {leg.get("id"): leg for leg in (raw.get("legs") or []) if leg.get("id")}
    segments_by_id = {s.get("id"): s for s in (raw.get("segments") or []) if s.get("id")}
    carriers_by_id = {
        c.get("id"): {"name": c.get("name"), "code": c.get("display_code")}
        for c in (raw.get("carriers") or [])
        if c.get("id") is not None
    }
    places_by_id = {p.get("id"): p for p in (raw.get("places") or []) if p.get("id") is not None}

    items: list[dict[str, Any]] = []
    unparsed = 0
    for itinerary in itineraries:
        pricing_options = itinerary.get("pricing_options") or itinerary.get("pricingOptions") or []
        if not pricing_options:
            unparsed += 1
            continue
        price_info = pricing_options[0].get("price", {})
        amount = price_info.get("amount")
        if amount is None:
            unparsed += 1
            continue

        leg_ids = itinerary.get("leg_ids") or itinerary.get("legIds") or []
        legs = [
            _leg_summary(legs_by_id[lid], carriers_by_id, places_by_id, segments_by_id)
            for lid in leg_ids
            if lid in legs_by_id
        ]
        legs = [leg for leg in legs if leg]
        if not legs:
            unparsed += 1
            continue

        flight_numbers = [fn for leg in legs for fn in (leg.get("flight_numbers") or [])]
        items.append({
            "itinerary_id": itinerary.get("id"),
            "price": amount,
            "currency": currency,
            "legs": legs,
            "total_stops": sum(leg.get("stop_count") or 0 for leg in legs),
            # Flattened across all legs/segments for quick display; the
            # per-segment breakdown with airline/route is under legs[].segments.
            "flight_numbers": flight_numbers,
        })

    return {"items": items, "unparsed_count": unparsed, "raw_itinerary_count": len(itineraries)}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
