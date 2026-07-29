from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from adapters import AeroDataBoxAdapter
from store import now_iso
from tools._shared import err

MAX_WINDOW_HOURS = 12


def _resolve_window(adapter: AeroDataBoxAdapter, code: str, code_type: str, from_local: str | None, to_local: str | None, hours: int) -> tuple[str, str, str | None]:
    if from_local and to_local:
        return from_local, to_local, None
    hours = max(1, min(hours, MAX_WINDOW_HOURS))
    airport = adapter.get_airport(code, code_type=code_type) or {}
    tz_name = airport.get("timeZone") or "UTC"
    start = datetime.now(ZoneInfo(tz_name)).replace(second=0, microsecond=0)
    end = start + timedelta(hours=hours)
    fmt = "%Y-%m-%dT%H:%M"
    return start.strftime(fmt), end.strftime(fmt), tz_name


def _normalize_row(row: dict[str, Any], direction: str) -> dict[str, Any]:
    other_side = row.get("arrival" if direction == "Departure" else "departure", {}) or {}
    own_side = row.get(direction.lower(), {}) or {}
    return {
        "number": row.get("number"),
        "airline": (row.get("airline") or {}).get("name"),
        "status": row.get("status"),
        "other_airport_iata": (other_side.get("airport") or {}).get("iata"),
        "scheduled_local": (own_side.get("scheduledTime") or {}).get("local"),
        "revised_local": (own_side.get("revisedTime") or {}).get("local"),
        "terminal": own_side.get("terminal"),
        "gate": own_side.get("gate"),
    }


def _get_schedule(code: str, code_type: str, from_local: str | None, to_local: str | None, hours: int, direction: str) -> dict[str, Any]:
    adapter = AeroDataBoxAdapter()
    resolved_from, resolved_to, tz_name = _resolve_window(adapter, code, code_type, from_local, to_local, hours)
    raw = adapter.get_airport_schedule(code, resolved_from, resolved_to, code_type=code_type, direction=direction) or {}
    key = "departures" if direction == "Departure" else "arrivals"
    rows = raw.get(key, []) if isinstance(raw, dict) else []
    return {
        "airport": code.upper(),
        "window_local": {"from": resolved_from, "to": resolved_to, "timezone": tz_name},
        "flights": [_normalize_row(row, direction) for row in rows],
        "flight_count": len(rows),
        "source": "AeroDataBox",
        "retrieved_at": now_iso(),
    }


def get_airport_departures(airport_code: str, code_type: str = "iata", from_local: str | None = None, to_local: str | None = None, hours: int = 6) -> dict[str, Any]:
    """List scheduled departures at an airport within a local time window (max 12h/call)."""
    try:
        result = _get_schedule(airport_code, code_type, from_local, to_local, hours, "Departure")
        return {"tool": "get_airport_departures", **result}
    except Exception as exc:
        return err("get_airport_departures", exc)


def get_airport_arrivals(airport_code: str, code_type: str = "iata", from_local: str | None = None, to_local: str | None = None, hours: int = 6) -> dict[str, Any]:
    """List scheduled arrivals at an airport within a local time window (max 12h/call)."""
    try:
        result = _get_schedule(airport_code, code_type, from_local, to_local, hours, "Arrival")
        return {"tool": "get_airport_arrivals", **result}
    except Exception as exc:
        return err("get_airport_arrivals", exc)
