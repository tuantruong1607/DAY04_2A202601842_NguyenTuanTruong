from __future__ import annotations

from typing import Any

from adapters import AeroDataBoxAdapter
from store import now_iso
from tools._shared import err


def _delay_minutes(scheduled: str | None, revised: str | None) -> int | None:
    if not scheduled or not revised:
        return None
    from datetime import datetime
    try:
        fmt = "%Y-%m-%d %H:%MZ"
        sched = datetime.strptime(scheduled, fmt)
        rev = datetime.strptime(revised, fmt)
        return round((rev - sched).total_seconds() / 60)
    except ValueError:
        return None


def _normalize_leg(flight: dict[str, Any]) -> dict[str, Any]:
    dep = flight.get("departure", {}) or {}
    arr = flight.get("arrival", {}) or {}
    dep_sched = (dep.get("scheduledTime") or {}).get("utc")
    dep_revised = (dep.get("revisedTime") or {}).get("utc")
    arr_sched = (arr.get("scheduledTime") or {}).get("utc")
    arr_revised = (arr.get("revisedTime") or {}).get("utc")
    return {
        "number": flight.get("number"),
        "airline": (flight.get("airline") or {}).get("name"),
        "status": flight.get("status"),
        "departure": {
            "airport_iata": (dep.get("airport") or {}).get("iata"),
            "scheduled_utc": dep_sched,
            "revised_utc": dep_revised,
            "terminal": dep.get("terminal"),
            "gate": dep.get("gate"),
            "delay_minutes": _delay_minutes(dep_sched, dep_revised),
        },
        "arrival": {
            "airport_iata": (arr.get("airport") or {}).get("iata"),
            "scheduled_utc": arr_sched,
            "revised_utc": arr_revised,
            "terminal": arr.get("terminal"),
            "gate": arr.get("gate"),
            "delay_minutes": _delay_minutes(arr_sched, arr_revised),
        },
    }


def get_flight_status(flight_number: str, date: str | None = None) -> dict[str, Any]:
    """Track a flight's real-time status by flight number (e.g. "VN7").

    `date` is optional (YYYY-MM-DD); without it AeroDataBox returns the
    nearest scheduled/active match. A flight number can match more than one
    result (codeshares, multiple days) — all are returned, never collapsed
    into a guess.
    """
    try:
        flight_number = (flight_number or "").strip().upper()
        if not flight_number:
            raise ValueError("flight_number is required")

        adapter = AeroDataBoxAdapter()
        raw = adapter.get_flight_status(flight_number, date_from=date)
        rows = raw if isinstance(raw, list) else ([raw] if raw else [])

        return {
            "tool": "get_flight_status",
            "flight_number": flight_number,
            "date": date,
            "matches": [_normalize_leg(row) for row in rows],
            "match_count": len(rows),
            "source": "AeroDataBox",
            "retrieved_at": now_iso(),
        }
    except Exception as exc:
        return err("get_flight_status", exc)
