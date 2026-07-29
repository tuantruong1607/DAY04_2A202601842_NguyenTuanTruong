from __future__ import annotations

from typing import Any

from store import now_iso
from tools._shared import err


def _offer_duration(offer: dict[str, Any]) -> int:
    legs = offer.get("legs") or []
    total = 0
    has_value = False
    for leg in legs:
        minutes = leg.get("duration_minutes")
        if minutes:
            total += minutes
            has_value = True
    return total if has_value else 10**9  # unknown duration sorts last


def _offer_carriers(offer: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for leg in offer.get("legs") or []:
        names.extend(leg.get("carriers") or [])
    return sorted(set(names))


def _offer_flight_numbers(offer: dict[str, Any]) -> list[str]:
    if offer.get("flight_numbers"):
        return list(offer["flight_numbers"])
    numbers: list[str] = []
    for leg in offer.get("legs") or []:
        numbers.extend(leg.get("flight_numbers") or [])
    return numbers


def compare_flight_offers(offers: list[dict[str, Any]], max_options: int = 3) -> dict[str, Any]:
    """Rank a list of offers (from search_flight_prices `items`) into up to
    3 labeled picks: cheapest, most convenient (fewest stops/shortest),
    and balanced (normalized price+convenience trade-off).

    This tool only ranks data already fetched by search_flight_prices — it
    does not call any external API and never invents a price or route.
    """
    try:
        if not offers:
            return {
                "tool": "compare_flight_offers",
                "picks": [],
                "message": "No offers provided to compare.",
                "retrieved_at": now_iso(),
            }

        enriched = []
        for offer in offers:
            enriched.append({
                **offer,
                "_duration": _offer_duration(offer),
                "_stops": offer.get("total_stops", 0),
                "_carriers": _offer_carriers(offer),
                "_flight_numbers": _offer_flight_numbers(offer),
            })

        prices = [o["price"] for o in enriched]
        durations = [o["_duration"] for o in enriched]
        min_price, max_price = min(prices), max(prices)
        min_dur, max_dur = min(durations), max(durations)

        def price_score(o: dict[str, Any]) -> float:
            return 0.0 if max_price == min_price else (o["price"] - min_price) / (max_price - min_price)

        def convenience_score(o: dict[str, Any]) -> float:
            dur_score = 0.0 if max_dur == min_dur else (o["_duration"] - min_dur) / (max_dur - min_dur)
            return 0.7 * dur_score + 0.3 * min(o["_stops"], 3) / 3

        cheapest = min(enriched, key=lambda o: o["price"])
        most_convenient = min(enriched, key=lambda o: (o["_stops"], o["_duration"]))
        balanced = min(enriched, key=lambda o: 0.6 * price_score(o) + 0.4 * convenience_score(o))

        picks = []
        seen_ids = set()
        for label, offer, reason in [
            ("cheapest", cheapest, f"Giá thấp nhất trong các lựa chọn: {cheapest['price']} {cheapest.get('currency', '')}."),
            ("most_convenient", most_convenient, f"Ít điểm dừng nhất ({most_convenient['_stops']}) và thời gian bay ngắn nhất trong nhóm."),
            ("balanced", balanced, "Cân bằng giữa giá và mức độ thuận tiện (thời gian bay + số điểm dừng)."),
        ]:
            offer_id = offer.get("itinerary_id") or id(offer)
            if offer_id in seen_ids:
                continue
            seen_ids.add(offer_id)
            picks.append({
                "label": label,
                "reason": reason,
                "itinerary_id": offer.get("itinerary_id"),
                "price": offer.get("price"),
                "currency": offer.get("currency"),
                "total_stops": offer.get("_stops"),
                "total_duration_minutes": offer.get("_duration") if offer.get("_duration", 10**9) < 10**9 else None,
                "carriers": offer.get("_carriers"),
                "flight_numbers": offer.get("_flight_numbers"),
                "legs": offer.get("legs"),
            })
            if len(picks) >= max_options:
                break

        return {
            "tool": "compare_flight_offers",
            "picks": picks,
            "considered_count": len(enriched),
            "retrieved_at": now_iso(),
        }
    except Exception as exc:
        return err("compare_flight_offers", exc)
