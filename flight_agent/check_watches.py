"""Evaluate all active watches against fresh live data and print alerts.

This is a standalone script — run it manually or wire it into a scheduler
(cron / Windows Task Scheduler) to get periodic checks. There is no push
notification channel configured (no email/SMS/Telegram credentials were
part of this project's scope), so "alerting" here means: print to stdout
and leave a record on the watch of the last alert, so nothing repeats.

Debouncing rule (CLAUDE.md §6): only alert on a genuine threshold cross or
a real state transition — never on an unchanged price/status.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
from env_loader import load_env  # noqa: E402

load_env(ROOT)

import store  # noqa: E402
from tools import TOOL_FUNCTIONS  # noqa: E402

SIGNIFICANT_DROP_PCT = 10.0


def check_price_watch(watch: dict[str, Any]) -> list[str]:
    alerts: list[str] = []
    result = TOOL_FUNCTIONS["search_flight_prices"](
        trip_type="ROUND_TRIP" if watch.get("return_date") else "ONE_WAY",
        origin=watch["origin"],
        destination=watch["destination"],
        departure_date=watch["departure_date"],
        return_date=watch.get("return_date"),
        cabin_class=watch.get("cabin_class", "ECONOMY"),
        adults=watch.get("adults", 1),
        children=watch.get("children", 0),
        infants=watch.get("infants", 0),
        currency=watch.get("currency", "VND"),
    )
    if result.get("error"):
        alerts.append(f"[watch {watch['id']}] search failed: {result.get('message')}")
        return alerts

    items = result.get("items") or []
    if not items:
        store.update_watch(watch["id"], last_checked_at=store.now_iso())
        return alerts

    lowest = items[0]["price"]
    currency = items[0]["currency"]
    max_price = watch.get("max_price")
    last_price = watch.get("last_price")
    last_alert_price = watch.get("last_alert_price")

    threshold_crossed = max_price is not None and lowest <= max_price
    already_alerted_this_price = last_alert_price is not None and lowest >= last_alert_price
    if threshold_crossed and not already_alerted_this_price:
        alerts.append(
            f"[watch {watch['id']}] {watch['origin']}->{watch['destination']} "
            f"{watch['departure_date']}: giá {lowest} {currency} <= ngưỡng {max_price} {currency}."
        )
        store.update_watch(watch["id"], last_alert_price=lowest)

    elif last_price is not None and lowest < last_price:
        drop_pct = (last_price - lowest) / last_price * 100
        if drop_pct >= SIGNIFICANT_DROP_PCT:
            alerts.append(
                f"[watch {watch['id']}] {watch['origin']}->{watch['destination']} "
                f"{watch['departure_date']}: giá giảm {drop_pct:.1f}% ({last_price} -> {lowest} {currency})."
            )

    store.update_watch(watch["id"], last_price=lowest, last_checked_at=store.now_iso())
    return alerts


def check_status_watch(watch: dict[str, Any]) -> list[str]:
    alerts: list[str] = []
    result = TOOL_FUNCTIONS["get_flight_status"](flight_number=watch["flight_number"], date=watch.get("date"))
    if result.get("error"):
        alerts.append(f"[watch {watch['id']}] status check failed: {result.get('message')}")
        return alerts

    matches = result.get("matches") or []
    if not matches:
        store.update_watch(watch["id"], last_checked_at=store.now_iso())
        return alerts

    match = matches[0]
    notify_on = set(watch.get("notify_on") or [])
    threshold = watch.get("delay_threshold_minutes", 15)

    new_status = match.get("status")
    dep = match.get("departure", {})
    arr = match.get("arrival", {})

    prev_status = watch.get("last_status")
    if new_status != prev_status:
        if new_status and new_status.lower() == "cancelled" and "cancel" in notify_on:
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: chuyến bay đã bị HỦY.")
        elif new_status and new_status.lower() in {"departed", "enroute", "airborne"} and "departed" in notify_on:
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: đã khởi hành.")
        elif new_status and new_status.lower() in {"arrived", "landed"} and "arrived" in notify_on:
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: đã đến nơi.")

    if "delay" in notify_on:
        dep_delay = dep.get("delay_minutes")
        prev_dep_delay = watch.get("last_departure_delay") or 0
        if dep_delay is not None and dep_delay >= threshold and prev_dep_delay < threshold:
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: trễ giờ khởi hành {dep_delay} phút.")

    if "terminal_change" in notify_on:
        if watch.get("last_departure_terminal") not in (None, dep.get("terminal")) :
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: đổi nhà ga đi -> {dep.get('terminal')}.")
        if watch.get("last_arrival_terminal") not in (None, arr.get("terminal")):
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: đổi nhà ga đến -> {arr.get('terminal')}.")

    if "gate_change" in notify_on:
        if watch.get("last_departure_gate") not in (None, dep.get("gate")):
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: đổi cửa ra đi -> {dep.get('gate')}.")
        if watch.get("last_arrival_gate") not in (None, arr.get("gate")):
            alerts.append(f"[watch {watch['id']}] {watch['flight_number']}: đổi cửa ra đến -> {arr.get('gate')}.")

    store.update_watch(
        watch["id"],
        last_status=new_status,
        last_departure_terminal=dep.get("terminal"),
        last_departure_gate=dep.get("gate"),
        last_arrival_terminal=arr.get("terminal"),
        last_arrival_gate=arr.get("gate"),
        last_departure_delay=dep.get("delay_minutes") or 0,
        last_checked_at=store.now_iso(),
    )
    return alerts


def main() -> None:
    parser = argparse.ArgumentParser(description="Check all active price/status watches for alerts.")
    parser.add_argument("--watch-id", default=None, help="Only check this watch id")
    args = parser.parse_args()

    watches = store.list_watches(active_only=True)
    if args.watch_id:
        watches = [w for w in watches if w["id"] == args.watch_id]

    if not watches:
        print("No active watches.")
        return

    total_alerts = 0
    for watch in watches:
        checker = check_price_watch if watch.get("type") == "price" else check_status_watch
        alerts = checker(watch)
        for alert in alerts:
            print(f"ALERT {alert}")
            total_alerts += 1

    print(f"Checked {len(watches)} watch(es), {total_alerts} alert(s).")


if __name__ == "__main__":
    main()
