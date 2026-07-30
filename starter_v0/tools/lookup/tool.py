from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from tools._shared import TIMEOUT, domain, fold_text, terms, utc_now_iso, err


TIMEFRAMES = ("day", "week", "month", "year")
GENERIC_SUBJECT_TERMS = {
    "bong", "da", "football", "soccer", "news", "tin", "moi", "nhat", "latest", "today",
    "hom", "nay", "update", "cap", "nhat",
}
INTENT_MARKERS: dict[str, set[str]] = {
    "transfer": {
        "chuyen", "nhuong", "ky", "ki", "hop", "dong", "gia", "nhap", "clb", "club", "contract",
        "deal", "join", "joins", "joined", "sign", "signs", "signed", "signing", "transfer", "transfers",
    },
    "injury": {
        "chan", "thuong", "injury", "injured", "fitness", "surgery", "rehab", "recovery", "return",
    },
    "fixture": {
        "lich", "tran", "dau", "gap", "fixture", "fixtures", "schedule", "match", "matches", "kickoff",
    },
    "result": {
        "ty", "so", "ket", "qua", "score", "scores", "result", "results", "won", "win", "draw", "lost",
    },
    "lineup": {
        "doi", "hinh", "lineup", "squad", "starting", "xi", "formation",
    },
}
INTENT_SUFFIX = {
    "transfer": "football transfer signing contract club",
    "injury": "football injury fitness update",
    "fixture": "football fixture schedule match",
    "result": "football match result score",
    "lineup": "football lineup squad team news",
    "general": "football news",
}


def _intent_kind(query: str, intent: str) -> str:
    haystack = terms(f"{query} {intent}")
    for kind, markers in INTENT_MARKERS.items():
        if haystack & markers:
            return kind
    return "general"


def _search_query(query: str, intent: str, *, enriched: bool) -> str:
    parts = [query.strip()]
    if intent.strip() and fold_text(intent.strip()) not in fold_text(query):
        parts.append(intent.strip())
    if enriched:
        kind = _intent_kind(query, intent)
        parts.extend([INTENT_SUFFIX[kind], str(datetime.now(timezone.utc).year)])
    return " ".join(part for part in parts if part).strip()


def _canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
    except Exception:
        return url.strip().lower()


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    published_date = item.get("published_date")
    return {
        "title": item.get("title"),
        "url": item.get("url"),
        "source": domain(item.get("url", "")),
        "summary": item.get("content"),
        "score": item.get("score"),
        "published_date": published_date,
        "date": published_date,
    }


def _is_relevant(item: dict[str, Any], query: str, intent: str) -> bool:
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or "")
    haystack = fold_text(f"{title} {summary}")
    score = float(item.get("score") or 0.0)

    subject_terms = terms(query) - GENERIC_SUBJECT_TERMS
    if not subject_terms:
        subject_ok = score >= 0.12
    else:
        overlap = subject_terms & terms(haystack)
        coverage = len(overlap) / len(subject_terms)
        phrase_match = fold_text(query.strip()) in haystack
        required_coverage = 1.0 if len(subject_terms) <= 3 else 0.4
        subject_ok = phrase_match or (score >= 0.12 and coverage >= required_coverage) or (score >= 0.55 and bool(overlap))

    kind = _intent_kind(query, intent)
    if kind == "general" or not intent.strip():
        intent_ok = True
    else:
        intent_ok = bool(terms(haystack) & INTENT_MARKERS[kind])

    return subject_ok and intent_ok


def _wider_timeframes(timeframe: str) -> list[str]:
    try:
        start = TIMEFRAMES.index(timeframe)
    except ValueError:
        return []
    return list(TIMEFRAMES[start + 1 :])


def _tavily_search(
    key: str,
    provider_query: str,
    topic: str,
    timeframe: str,
    max_results: int,
    search_depth: str,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "query": provider_query,
        "topic": topic,
        "max_results": max_results,
        "search_depth": search_depth,
    }
    if timeframe:
        body["time_range"] = timeframe
    response = requests.post(
        "https://api.tavily.com/search",
        json=body,
        headers={"Authorization": f"Bearer {key}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return [_normalize_item(item) for item in response.json().get("results", [])]


def web_search(
    query: str = "",
    topic: str = "general",
    timeframe: str | None = "week",
    max_results: int = 5,
    intent: str = "",
    strict_timeframe: bool = False,
) -> dict[str, Any]:
    """Search Tavily with deterministic relevance and freshness safeguards.

    `query` remains the stable subject used by routing evaluations. `intent`
    carries the action or claim being investigated and is used only to make the
    provider query more precise.
    """
    try:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("Missing TAVILY_API_KEY env var")

        query = (query or "").strip()
        intent = (intent or "").strip()
        if not query:
            raise ValueError("query is required")
        topic = topic if topic in {"general", "news"} else "general"
        requested_timeframe = timeframe if timeframe in TIMEFRAMES else "week"
        limit = max(1, min(int(max_results or 5), 10))
        provider_limit = min(10, max(limit + 3, 8))

        specs: list[tuple[str, str, str]] = [
            (_search_query(query, intent, enriched=False), requested_timeframe, "basic"),
            (_search_query(query, intent, enriched=True), requested_timeframe, "advanced"),
        ]
        if not strict_timeframe:
            enriched_query = _search_query(query, intent, enriched=True)
            specs.extend((enriched_query, wider, "advanced") for wider in _wider_timeframes(requested_timeframe))

        accepted: list[dict[str, Any]] = []
        seen: set[str] = set()
        attempts: list[dict[str, Any]] = []
        discarded_count = 0

        for provider_query, attempt_timeframe, search_depth in specs:
            raw_items = _tavily_search(
                key,
                provider_query,
                topic,
                attempt_timeframe,
                provider_limit,
                search_depth,
            )
            relevant_items = [item for item in raw_items if _is_relevant(item, query, intent)]
            discarded_count += len(raw_items) - len(relevant_items)
            attempts.append({
                "query": provider_query,
                "timeframe": attempt_timeframe,
                "search_depth": search_depth,
                "returned": len(raw_items),
                "accepted": len(relevant_items),
            })
            for item in relevant_items:
                identity = _canonical_url(str(item.get("url") or "")) or fold_text(str(item.get("title") or ""))
                if identity in seen:
                    continue
                seen.add(identity)
                accepted.append(item)
            accepted.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
            if len(accepted) >= max(2, min(limit, 3)):
                break

        output_items = accepted[:limit]
        broadened = any(attempt["timeframe"] != requested_timeframe for attempt in attempts)
        if len(output_items) >= 2:
            quality_status = "sufficient"
        elif output_items:
            quality_status = "limited"
        else:
            quality_status = "no_relevant_results"

        result: dict[str, Any] = {
            "tool": "web_search",
            "query": query,
            "intent": intent,
            "topic": topic,
            "timeframe": requested_timeframe,
            "strict_timeframe": bool(strict_timeframe),
            "retrieved_at": utc_now_iso(),
            "items": output_items,
            "quality": {
                "status": quality_status,
                "relevant_count": len(output_items),
                "discarded_count": discarded_count,
                "timeframe_broadened": broadened,
            },
            "attempts": attempts,
        }
        if not output_items:
            result["warning"] = "No sufficiently relevant result was found. This is inconclusive, not proof that the event did not happen."
        elif broadened:
            result["warning"] = "The requested window had insufficient relevant evidence, so a broader window was also searched. Check published_date before answering."
        return result
    except Exception as exc:
        return err("web_search", exc)
