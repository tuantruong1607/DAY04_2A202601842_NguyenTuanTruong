from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import requests

from tools._shared import TIMEOUT, err


DEFAULT_HOST = "facebook-scraper3.p.rapidapi.com"


def _event_time(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(value), tz=UTC).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _admin_countries(info: dict[str, Any]) -> list[dict[str, Any]]:
    locations = info.get("admin_locations") or {}
    rows = locations.get("admin_country_counts") or [] if isinstance(locations, dict) else []
    countries: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        country = row.get("country")
        if isinstance(country, dict):
            name = country.get("name") or country.get("label") or country.get("code")
        else:
            name = country
        countries.append({"country": name, "count": row.get("count")})
    return countries


def _history(info: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in info.get("history_items") or []:
        if not isinstance(row, dict):
            continue
        events.append({
            "event_type": row.get("item_type"),
            "event_time": _event_time(row.get("event_time")),
            "target_name": row.get("target_name"),
        })
    return events


def _summary(transparency: dict[str, Any]) -> str:
    parts = [f"Verification: {transparency.get('verification_status') or 'unknown'}"]
    countries = transparency.get("admin_countries") or []
    if countries:
        labels = [
            f"{row.get('country') or 'unknown'} ({row.get('count')})"
            for row in countries[:5]
        ]
        parts.append("Admin locations: " + ", ".join(labels))
    parts.append(f"Active ads: {transparency.get('has_active_ads')}")
    parts.append(f"Political ads: {transparency.get('has_run_political_ads')}")
    if transparency.get("history"):
        parts.append(f"Transparency history events: {len(transparency['history'])}")
    return "; ".join(parts)


def get_facebook_page_transparency(page_id: str = "") -> dict[str, Any]:
    try:
        normalized_id = str(page_id or "").strip()
        if not normalized_id or not normalized_id.isdigit():
            raise ValueError("page_id must be a numeric Facebook Page ID")

        key = os.getenv("RAPIDAPI_KEY")
        host = os.getenv("RAPIDAPI_FACEBOOK_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
        if not key:
            raise RuntimeError("Missing RAPIDAPI_KEY env var")

        response = requests.get(
            f"https://{host}/page/transparency",
            params={"page_id": normalized_id},
            headers={
                "Content-Type": "application/json",
                "x-rapidapi-key": key,
                "x-rapidapi-host": host,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, dict):
            raise ValueError("Facebook API returned no transparency result")

        info = results.get("pages_transparency_info") or {}
        if not isinstance(info, dict):
            info = {}
        owner = results.get("confirmed_page_owner_consumer") or {}
        transparency = {
            "page_id": normalized_id,
            "name": results.get("name"),
            "page_type": results.get("page_type_name_for_content"),
            "verification_status": results.get("verification_status"),
            "owner_type": owner.get("type") if isinstance(owner, dict) else None,
            "admin_countries": _admin_countries(info),
            "unknown_admin_count": (info.get("admin_locations") or {}).get("num_unknown")
            if isinstance(info.get("admin_locations"), dict)
            else None,
            "has_active_ads": info.get("has_active_ads"),
            "has_run_political_ads": info.get("has_run_political_ads"),
            "history": _history(info),
        }
        item = {
            "title": transparency.get("name") or f"Facebook Page {normalized_id}",
            "url": f"https://www.facebook.com/{normalized_id}",
            "source": "facebook.com",
            "summary": _summary(transparency),
        }
        return {
            "tool": "facebook_page_transparency",
            "page_id": normalized_id,
            "transparency": transparency,
            "items": [item],
        }
    except Exception as exc:
        return err("facebook_page_transparency", exc)

