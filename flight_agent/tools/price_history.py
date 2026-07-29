from __future__ import annotations

from typing import Any

from store import compute_price_stats, get_price_history, now_iso, price_watch_key
from tools._shared import err


def analyze_price_history(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    cabin_class: str = "ECONOMY",
    currency: str = "VND",
) -> dict[str, Any]:
    """Analyze price fluctuation for a route/date using previously recorded
    price checks (each call to search_flight_prices for the same route/date
    logs a data point). Returns min/max/avg/median/pct-change/best date.

    If no history exists yet, says so explicitly rather than inventing a trend.
    """
    try:
        key = price_watch_key(origin, destination, departure_date, return_date, cabin_class, currency)
        records = get_price_history(key)
        stats = compute_price_stats(records)
        return {
            "tool": "analyze_price_history",
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_date": departure_date,
            "return_date": return_date,
            "cabin_class": cabin_class,
            "currency": currency,
            "stats": stats,
            "has_history": stats.get("count", 0) > 0,
            "note": None if stats.get("count", 0) > 0 else (
                "No price checks recorded yet for this route/date. Call search_flight_prices "
                "for it first (and again later) to build history."
            ),
            "retrieved_at": now_iso(),
        }
    except Exception as exc:
        return err("analyze_price_history", exc)
