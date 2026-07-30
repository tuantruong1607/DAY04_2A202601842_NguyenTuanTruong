from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import domain, err, utc_now_iso


def read_url(url: str = "", max_age: int = 0) -> dict[str, Any]:
    try:
        key = os.getenv("FIRECRAWL_API_KEY")
        if not key:
            raise RuntimeError("Missing FIRECRAWL_API_KEY env var")
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            # News pages change frequently. Firecrawl v1 supports maxAge=0 to
            # force a fresh scrape instead of serving a cached copy.
            json={"url": url, "formats": ["markdown"], "maxAge": max(0, int(max_age or 0))},
            headers={"Authorization": f"Bearer {key}"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        meta = data.get("metadata", {}) or {}
        published_date = (
            meta.get("publishedTime")
            or meta.get("published_date")
            or meta.get("article:published_time")
            or meta.get("datePublished")
        )
        modified_date = (
            meta.get("modifiedTime")
            or meta.get("modified_date")
            or meta.get("article:modified_time")
            or meta.get("dateModified")
        )
        return {
            "tool": "read_url",
            "url": url,
            "retrieved_at": utc_now_iso(),
            "max_age": max(0, int(max_age or 0)),
            "cache_state": meta.get("cacheState"),
            "items": [{
                "title": meta.get("title") or url,
                "url": meta.get("sourceURL") or url,
                "source": domain(url),
                "summary": (data.get("markdown") or "")[:4000],
                "published_date": published_date,
                "modified_date": modified_date,
                "date": published_date or modified_date,
            }],
        }
    except Exception as exc:
        return err("read_url", exc)

