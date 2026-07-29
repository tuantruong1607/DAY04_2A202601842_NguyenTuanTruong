from __future__ import annotations

from typing import Any

from adapters.flightapi_adapter import FlightAPIAdapter, normalize_offers
from store import append_price_point, now_iso, price_watch_key
from tools._shared import err, to_flightapi_cabin


def search_flight_prices(
    trip_type: str,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    cabin_class: str = "ECONOMY",
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    currency: str = "VND",
    max_price: float | None = None,
) -> dict[str, Any]:
    """Search live one-way or round-trip prices via FlightAPI.io.

    `origin`/`destination` must be verified IATA codes from search_airports,
    never guessed. Every returned item is a real priced itinerary from the
    provider as of `retrieved_at`; nothing here is estimated.
    """
    try:
        trip_type = (trip_type or "ONE_WAY").upper()
        if trip_type not in {"ONE_WAY", "ROUND_TRIP"}:
            raise ValueError("trip_type must be ONE_WAY or ROUND_TRIP")
        if trip_type == "ROUND_TRIP" and not return_date:
            raise ValueError("return_date is required for ROUND_TRIP")

        adapter = FlightAPIAdapter()
        fapi_cabin = to_flightapi_cabin(cabin_class)
        if trip_type == "ONE_WAY":
            raw = adapter.search_one_way(
                origin, destination, departure_date,
                adults=adults, children=children, infants=infants,
                cabin_class=fapi_cabin, currency=currency,
            )
        else:
            raw = adapter.search_round_trip(
                origin, destination, departure_date, return_date,
                adults=adults, children=children, infants=infants,
                cabin_class=fapi_cabin, currency=currency,
            )

        parsed = normalize_offers(raw, currency)
        items = sorted(parsed["items"], key=lambda o: o["price"])
        if max_price is not None:
            items = [o for o in items if o["price"] <= max_price]

        key = price_watch_key(origin, destination, departure_date, return_date, cabin_class, currency)
        if items:
            append_price_point(key, items[0]["price"], currency, "FlightAPI", {
                "origin": origin, "destination": destination,
                "departure_date": departure_date, "return_date": return_date,
            })

        return {
            "tool": "search_flight_prices",
            "trip_type": trip_type,
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_date": departure_date,
            "return_date": return_date,
            "cabin_class": cabin_class,
            "currency": currency,
            "items": items[:20],
            "item_count": len(items),
            "unparsed_count": parsed["unparsed_count"],
            "source": "FlightAPI.io",
            "retrieved_at": now_iso(),
        }
    except Exception as exc:
        return err("search_flight_prices", exc)
