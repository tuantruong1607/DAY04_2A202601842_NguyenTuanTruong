from __future__ import annotations

from typing import Any

import store
from tools._shared import err

VALID_STATUS_EVENTS = {"delay", "cancel", "gate_change", "terminal_change", "departed", "arrived"}


def create_price_watch(
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
    note: str | None = None,
) -> dict[str, Any]:
    """Register a price watch for a route/date. Does not itself check prices —
    run check_watches.py (or ask the agent to re-check) to evaluate it against
    a fresh search_flight_prices call and get an alert only on threshold cross
    or significant change, never a duplicate alert for an unchanged price.
    """
    try:
        if not origin or not destination or not departure_date:
            raise ValueError("origin, destination, departure_date are required")
        watch = store.create_watch({
            "type": "price",
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_date": departure_date,
            "return_date": return_date,
            "cabin_class": cabin_class,
            "adults": adults,
            "children": children,
            "infants": infants,
            "currency": currency,
            "max_price": max_price,
            "note": note,
            "last_alert_price": None,
        })
        return {"tool": "create_price_watch", "watch": watch}
    except Exception as exc:
        return err("create_price_watch", exc)


def create_flight_status_watch(
    flight_number: str,
    date: str | None = None,
    notify_on: list[str] | None = None,
    delay_threshold_minutes: int = 15,
) -> dict[str, Any]:
    """Register a status watch for a flight number (+ optional date).
    `notify_on` restricts which event types trigger an alert; default is all
    of: delay, cancel, gate_change, terminal_change, departed, arrived.
    """
    try:
        flight_number = (flight_number or "").strip().upper()
        if not flight_number:
            raise ValueError("flight_number is required")
        events = set(notify_on) if notify_on else set(VALID_STATUS_EVENTS)
        invalid = events - VALID_STATUS_EVENTS
        if invalid:
            raise ValueError(f"Unknown notify_on events: {sorted(invalid)}")
        watch = store.create_watch({
            "type": "status",
            "flight_number": flight_number,
            "date": date,
            "notify_on": sorted(events),
            "delay_threshold_minutes": delay_threshold_minutes,
            "last_status": None,
            "last_terminal": None,
            "last_gate": None,
        })
        return {"tool": "create_flight_status_watch", "watch": watch}
    except Exception as exc:
        return err("create_flight_status_watch", exc)


def cancel_watch(watch_id: str) -> dict[str, Any]:
    """Cancel a price or status watch by its id."""
    try:
        watch = store.cancel_watch(watch_id)
        if not watch:
            return {"tool": "cancel_watch", "error": "not_found", "message": f"No watch with id {watch_id}"}
        return {"tool": "cancel_watch", "watch": watch}
    except Exception as exc:
        return err("cancel_watch", exc)
