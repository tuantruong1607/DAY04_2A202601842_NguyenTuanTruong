"""Local JSON-file persistence for price history and watches.

No database needed for this lab-scale agent: two flat JSON files under
`data/`, read-modify-write on each call. Not safe for concurrent writers,
which is fine for a single-user CLI agent.
"""
from __future__ import annotations

import json
import statistics
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PRICE_HISTORY_PATH = DATA_DIR / "price_history.json"
WATCHES_PATH = DATA_DIR / "watches.json"


def _load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _save(path: Path, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def price_watch_key(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    cabin_class: str,
    currency: str,
) -> str:
    return "|".join([origin.upper(), destination.upper(), departure_date, return_date or "oneway", cabin_class, currency])


# --------------------------------------------------------------------- price history
def append_price_point(key: str, price: float, currency: str, source: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    history = _load(PRICE_HISTORY_PATH, {})
    record = {"price": price, "currency": currency, "source": source, "checked_at": now_iso(), **(extra or {})}
    history.setdefault(key, []).append(record)
    _save(PRICE_HISTORY_PATH, history)
    return record


def get_price_history(key: str) -> list[dict[str, Any]]:
    history = _load(PRICE_HISTORY_PATH, {})
    return history.get(key, [])


def compute_price_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    prices = [r["price"] for r in records]
    lowest = min(records, key=lambda r: r["price"])
    first, last = prices[0], prices[-1]
    pct_change = ((last - first) / first * 100) if first else None
    return {
        "count": len(records),
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": round(statistics.fmean(prices), 2),
        "median_price": statistics.median(prices),
        "pct_change_first_to_last": round(pct_change, 2) if pct_change is not None else None,
        "best_price_date": lowest.get("checked_at"),
        "currency": records[0].get("currency"),
    }


# --------------------------------------------------------------------- watches
def _all_watches() -> dict[str, Any]:
    return _load(WATCHES_PATH, {})


def create_watch(watch: dict[str, Any]) -> dict[str, Any]:
    watches = _all_watches()
    watch_id = uuid.uuid4().hex[:10]
    watch = {"id": watch_id, "status": "active", "created_at": now_iso(), **watch}
    watches[watch_id] = watch
    _save(WATCHES_PATH, watches)
    return watch


def list_watches(*, active_only: bool = True, watch_type: str | None = None) -> list[dict[str, Any]]:
    watches = list(_all_watches().values())
    if active_only:
        watches = [w for w in watches if w.get("status") == "active"]
    if watch_type:
        watches = [w for w in watches if w.get("type") == watch_type]
    return watches


def get_watch(watch_id: str) -> dict[str, Any] | None:
    return _all_watches().get(watch_id)


def update_watch(watch_id: str, **fields: Any) -> dict[str, Any] | None:
    watches = _all_watches()
    watch = watches.get(watch_id)
    if not watch:
        return None
    watch.update(fields)
    watch["updated_at"] = now_iso()
    watches[watch_id] = watch
    _save(WATCHES_PATH, watches)
    return watch


def cancel_watch(watch_id: str) -> dict[str, Any] | None:
    return update_watch(watch_id, status="cancelled")
