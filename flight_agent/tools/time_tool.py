from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tools._shared import err

VIETNAM_TZ = "Asia/Ho_Chi_Minh"


def _zone_snapshot(tz_name: str) -> dict[str, Any]:
    now = datetime.now(ZoneInfo(tz_name))
    return {
        "timezone": tz_name,
        "iso": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "utc_offset": now.strftime("%z"),
    }


def get_current_time(timezone: str | None = None) -> dict[str, Any]:
    """Return the real current date/time — the only source of truth for
    "today"/"now", never the model's own belief.

    Always includes UTC and Vietnam (Asia/Ho_Chi_Minh, UTC+7). An optional
    extra IANA `timezone` (e.g. an airport's `timezone` field returned by
    search_airports) is included too, useful for converting a local
    departure/arrival time. Call this before resolving any relative
    date/time the user mentions ("hom nay", "ngay mai", "tuan sau", "next
    Friday", etc.) so dates passed to other tools are grounded in the
    actual current date, not a guess. No external API call — read straight
    from the system clock.
    """
    try:
        result: dict[str, Any] = {
            "tool": "get_current_time",
            "utc": _zone_snapshot("UTC"),
            "vietnam": _zone_snapshot(VIETNAM_TZ),
            "source": "system_clock",
        }
        if timezone and timezone.upper() != "UTC" and timezone != VIETNAM_TZ:
            try:
                result["requested_timezone"] = _zone_snapshot(timezone)
            except ZoneInfoNotFoundError:
                result["requested_timezone_error"] = f"Unknown IANA timezone: {timezone}"
        return result
    except Exception as exc:
        return err("get_current_time", exc)
