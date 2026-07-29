"""OpenAI-style function-calling declarations for every tool in TOOL_FUNCTIONS.

Kept as plain Python (not YAML) since this is a standalone project — one
source of truth per tool, close to its implementation's signature.
"""
from __future__ import annotations

from typing import Any

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": (
                "Get the real current date/time in UTC and Vietnam (Asia/Ho_Chi_Minh, "
                "UTC+7), straight from the system clock. Call this before resolving any "
                "relative date/time the user mentions ('hom nay', 'ngay mai', 'tuan sau', "
                "'next Friday', etc.) so dates you pass to other tools are grounded in "
                "the actual current date — never calculate or assume today's date "
                "yourself. A fresh reminder of the current time is also injected "
                "automatically at the start of every turn; call this tool again mid-turn "
                "if you need it re-checked or need another airport's local timezone "
                "(pass its IANA `timezone` from search_airports)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Optional extra IANA timezone to also report, e.g. an airport's timezone field from search_airports"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_airports",
            "description": (
                "Look up / verify airport IATA and ICAO codes by city or airport name. "
                "MUST be called before an airport code from that lookup is used in any "
                "other tool this conversation — including a code the user typed "
                "themselves next to a city/airport name, since the model's own memory "
                "of codes is not trustworthy. The only case that does not need a lookup "
                "is when the user's message contains nothing but a bare, standalone "
                "3-letter code (e.g. just 'HAN') with no city/airport name attached, and "
                "even then you should call this to confirm if you have any doubt. Never "
                "guess a code from memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "City or airport name, e.g. 'Hanoi' or 'Tan Son Nhat'"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flight_prices",
            "description": (
                "Search live one-way or round-trip flight prices between two airport "
                "codes. origin/destination MUST already be verified via search_airports "
                "earlier in this conversation — an unverified code is rejected. Each "
                "returned offer includes flight_numbers (and a per-leg/per-segment "
                "breakdown under legs[].segments) — always surface these to the user, "
                "never omit them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_type": {"type": "string", "enum": ["ONE_WAY", "ROUND_TRIP"]},
                    "origin": {"type": "string", "description": "Origin IATA code, e.g. HAN"},
                    "destination": {"type": "string", "description": "Destination IATA code, e.g. SGN"},
                    "departure_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "return_date": {"type": "string", "description": "YYYY-MM-DD, required for ROUND_TRIP"},
                    "cabin_class": {"type": "string", "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"], "default": "ECONOMY"},
                    "adults": {"type": "integer", "default": 1},
                    "children": {"type": "integer", "default": 0},
                    "infants": {"type": "integer", "default": 0},
                    "currency": {"type": "string", "default": "VND"},
                    "max_price": {"type": "number", "description": "Optional budget ceiling to filter results"},
                },
                "required": ["trip_type", "origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_status",
            "description": "Track the real-time status of a specific flight by flight number (e.g. 'VN7').",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {"type": "string"},
                    "date": {"type": "string", "description": "Optional YYYY-MM-DD"},
                },
                "required": ["flight_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_airport_departures",
            "description": (
                "List scheduled departures at an airport within a local time window "
                "(max 12 hours per call). airport_code MUST already be verified via "
                "search_airports earlier in this conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "airport_code": {"type": "string"},
                    "code_type": {"type": "string", "enum": ["iata", "icao"], "default": "iata"},
                    "from_local": {"type": "string", "description": "Optional ISO local datetime, e.g. 2026-08-15T08:00"},
                    "to_local": {"type": "string", "description": "Optional ISO local datetime"},
                    "hours": {"type": "integer", "default": 6, "description": "Window size if from_local/to_local omitted (max 12)"},
                },
                "required": ["airport_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_airport_arrivals",
            "description": (
                "List scheduled arrivals at an airport within a local time window "
                "(max 12 hours per call). airport_code MUST already be verified via "
                "search_airports earlier in this conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "airport_code": {"type": "string"},
                    "code_type": {"type": "string", "enum": ["iata", "icao"], "default": "iata"},
                    "from_local": {"type": "string", "description": "Optional ISO local datetime, e.g. 2026-08-15T08:00"},
                    "to_local": {"type": "string", "description": "Optional ISO local datetime"},
                    "hours": {"type": "integer", "default": 6, "description": "Window size if from_local/to_local omitted (max 12)"},
                },
                "required": ["airport_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_flight_offers",
            "description": (
                "Rank a list of already-fetched offers (the `items` array from search_flight_prices) "
                "into up to 3 labeled picks: cheapest, most_convenient, balanced. Does not call any API. "
                "Each pick keeps its flight_numbers — always include them when presenting a pick."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "offers": {"type": "array", "items": {"type": "object"}, "description": "The items array from a prior search_flight_prices call"},
                    "max_options": {"type": "integer", "default": 3},
                },
                "required": ["offers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_price_history",
            "description": "Analyze recorded price fluctuation for a route/date (min/max/avg/median/% change/best date). Uses locally logged price checks from prior search_flight_prices calls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "departure_date": {"type": "string"},
                    "return_date": {"type": "string"},
                    "cabin_class": {"type": "string", "default": "ECONOMY"},
                    "currency": {"type": "string", "default": "VND"},
                },
                "required": ["origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_price_watch",
            "description": (
                "Register a price watch for a route/date; alerts when price drops "
                "to/below max_price or changes significantly (checked by re-running "
                "search_flight_prices, e.g. via check_watches.py). origin/destination "
                "MUST already be verified via search_airports earlier in this "
                "conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "departure_date": {"type": "string"},
                    "return_date": {"type": "string"},
                    "cabin_class": {"type": "string", "default": "ECONOMY"},
                    "adults": {"type": "integer", "default": 1},
                    "children": {"type": "integer", "default": 0},
                    "infants": {"type": "integer", "default": 0},
                    "currency": {"type": "string", "default": "VND"},
                    "max_price": {"type": "number"},
                    "note": {"type": "string"},
                },
                "required": ["origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_flight_status_watch",
            "description": "Register a status watch for a flight number; alerts on delay/cancel/gate change/terminal change/departed/arrived.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {"type": "string"},
                    "date": {"type": "string"},
                    "notify_on": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["delay", "cancel", "gate_change", "terminal_change", "departed", "arrived"]},
                    },
                    "delay_threshold_minutes": {"type": "integer", "default": 15},
                },
                "required": ["flight_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_watch",
            "description": "Cancel a previously created price or status watch by its id.",
            "parameters": {
                "type": "object",
                "properties": {"watch_id": {"type": "string"}},
                "required": ["watch_id"],
            },
        },
    },
]
