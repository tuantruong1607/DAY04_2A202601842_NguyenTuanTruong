from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err
from tools.lookup.tool import web_search


def _twitter_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    key = os.getenv("RAPIDAPI_KEY")
    host = (os.getenv("RAPIDAPI_TWITTER_HOST") or "").strip()
    if not key or not host:
        raise RuntimeError("RapidAPI Twitter backend is not configured")
    response = requests.get(
        f"https://{host}{path}",
        params=params,
        headers={"x-rapidapi-key": key, "x-rapidapi-host": host},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _tweet_item(raw: dict[str, Any]) -> dict[str, Any]:
    handle = raw.get("screen_name") or (raw.get("author") or {}).get("screen_name") or ""
    tweet_id = raw.get("tweet_id") or raw.get("id") or ""
    text = (raw.get("text") or "").strip()
    return {
        "title": text.split("\n")[0][:120],
        "summary": text,
        "url": f"https://x.com/{handle}/status/{tweet_id}" if handle and tweet_id else "",
        "source": f"@{handle}" if handle else "x.com",
        "date": raw.get("created_at"),
        "metrics": {"favorites": raw.get("favorites"), "retweets": raw.get("retweets"), "views": raw.get("views")},
    }


def _tweets_from(data: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    raw_items = data.get("timeline") or data.get("tweets") or []
    items = [_tweet_item(item) for item in raw_items if item.get("tweet_id") or item.get("id")]
    return items[: int(limit or 5)]


def search_tweets(query: str = "", search_type: str = "Latest", limit: int = 5) -> dict[str, Any]:
    query = (query or "").strip()
    search_type = search_type if search_type in {"Latest", "Top"} else "Latest"
    limit = max(1, min(int(limit or 5), 10))
    if not query:
        return err("search_tweets", ValueError("query is required"))
    try:
        data = _twitter_get("/search.php", {"query": query, "search_type": search_type})
        items = _tweets_from(data, limit)
        if not items:
            raise ValueError("RapidAPI Twitter returned no search items")
        return {
            "tool": "search_tweets",
            "query": query,
            "search_type": search_type,
            "items": items,
            "backend": "rapidapi_twitter",
        }
    except Exception as primary_exc:
        qualifier = "popular" if search_type == "Top" else "latest"
        fallback = web_search(
            query=query,
            intent=f"{qualifier} public X posts about this football topic",
            topic="general",
            timeframe="week",
            strict_timeframe=True,
            max_results=limit,
        )
        if fallback.get("error"):
            return err(
                "search_tweets",
                RuntimeError(
                    "Twitter backend and Tavily fallback both failed: "
                    f"{fallback.get('message') or fallback.get('error')}"
                ),
            )
        x_items = [
            item for item in (fallback.get("items") or [])
            if "x.com/" in str(item.get("url") or "").lower()
            or "twitter.com/" in str(item.get("url") or "").lower()
        ][:limit]
        return {
            "tool": "search_tweets",
            "query": query,
            "search_type": search_type,
            "items": x_items,
            "backend": "tavily_x_index_fallback",
            "fallback_reason": type(primary_exc).__name__,
            "quality": {
                "status": "indexed_fallback" if x_items else "no_relevant_results",
                "relevant_count": len(x_items),
                "live": False,
            },
            "warning": "The RapidAPI X search backend was unavailable. Tavily's public X index can be delayed and is not a live social search.",
        }

