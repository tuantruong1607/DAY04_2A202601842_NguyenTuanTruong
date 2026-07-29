from __future__ import annotations

from typing import Any

from adapters import AeroDataBoxAdapter, AeroDataBoxError, FlightAPIAdapter, FlightAPIError
from store import now_iso
from tools._shared import err


def search_airports(query: str, limit: int = 5) -> dict[str, Any]:
    """Verify/look up airport IATA/ICAO codes by free-text name or city.

    Never guess an airport code — this is the only source of truth for
    codes used by the other tools. Primary source is AeroDataBox; FlightAPI
    is tried as a secondary enrichment source and silently skipped if it
    errors (its /iata endpoint is plan-gated on some keys).
    """
    try:
        query = (query or "").strip()
        if not query:
            raise ValueError("query is required")

        items: list[dict[str, Any]] = []
        source_parts: list[str] = []

        try:
            aero = AeroDataBoxAdapter()
            raw = aero.search_airports(query, limit=limit)
            for row in (raw or {}).get("items", [])[:limit]:
                items.append({
                    "iata": row.get("iata"),
                    "icao": row.get("icao"),
                    "name": row.get("name"),
                    "city": row.get("municipalityName"),
                    "country": row.get("countryCode"),
                    "timezone": row.get("timeZone"),
                })
            source_parts.append("AeroDataBox")
        except AeroDataBoxError:
            pass

        if not items:
            try:
                fapi = FlightAPIAdapter()
                for row in fapi.lookup_codes(query, "airport")[:limit]:
                    items.append({
                        "iata": row.get("code"),
                        "icao": None,
                        "name": row.get("name"),
                        "city": None,
                        "country": None,
                        "timezone": None,
                    })
                source_parts.append("FlightAPI")
            except FlightAPIError:
                pass

        return {
            "tool": "search_airports",
            "query": query,
            "items": items,
            "source": " + ".join(source_parts) if source_parts else "none (all providers failed)",
            "retrieved_at": now_iso(),
        }
    except Exception as exc:
        return err("search_airports", exc)
