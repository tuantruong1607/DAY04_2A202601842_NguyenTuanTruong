from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err
from tools.lookup.tool import web_search


DISPLAY_NAMES = {
    "sama": "Sam Altman",
    "elonmusk": "Elon Musk",
    "karpathy": "Andrej Karpathy",
}


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


def get_user_tweets(screenname: str = "", limit: int = 5) -> dict[str, Any]:
    screenname = (screenname or "").strip().lstrip("@")
    limit = max(1, min(int(limit or 5), 10))
    if not screenname:
        return err("get_user_tweets", ValueError("screenname is required"))
    try:
        data = _twitter_get("/timeline.php", {"screenname": screenname})
        items = _tweets_from(data, limit)
        if not items:
            raise ValueError("RapidAPI Twitter returned no timeline items")
        return {
            "tool": "get_user_tweets",
            "screenname": screenname,
            "items": items,
            "backend": "rapidapi_twitter",
        }
    except Exception as primary_exc:
        display_name = DISPLAY_NAMES.get(screenname.lower(), f"@{screenname}")
        fallback = web_search(
            query=display_name,
            intent=f"recent public X posts from x.com/{screenname}",
            topic="general",
            timeframe="month",
            strict_timeframe=True,
            max_results=max(limit, 5),
        )
        if fallback.get("error"):
            return err(
                "get_user_tweets",
                RuntimeError(
                    "Twitter backend and Tavily fallback both failed: "
                    f"{fallback.get('message') or fallback.get('error')}"
                ),
            )
        raw_items = fallback.get("items") or []
        status_path = f"/{screenname.lower()}/status/"
        status_items = [
            item
            for item in raw_items
            if status_path in str(item.get("url") or "").lower()
        ]
        output_items = status_items[:limit]
        return {
            "tool": "get_user_tweets",
            "screenname": screenname,
            "items": output_items,
            "backend": "tavily_x_index_fallback",
            "fallback_reason": type(primary_exc).__name__,
            "quality": {
                "status": "indexed_fallback" if output_items else "no_relevant_results",
                "relevant_count": len(output_items),
                "live": False,
            },
            "warning": "The RapidAPI timeline backend was unavailable. Tavily's public X index can be delayed and is not a live timeline.",
        }

