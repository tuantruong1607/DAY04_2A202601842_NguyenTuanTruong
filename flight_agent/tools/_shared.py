from __future__ import annotations

from typing import Any


def err(tool: str, exc: Exception) -> dict[str, Any]:
    return {"tool": tool, "error": type(exc).__name__, "message": str(exc)}


CABIN_CLASS_MAP = {
    "ECONOMY": "Economy",
    "PREMIUM_ECONOMY": "Premium_Economy",
    "BUSINESS": "Business",
    "FIRST": "First",
}


def to_flightapi_cabin(cabin_class: str) -> str:
    return CABIN_CLASS_MAP.get((cabin_class or "ECONOMY").upper(), "Economy")
