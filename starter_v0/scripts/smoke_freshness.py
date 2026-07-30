from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from env_loader import load_lab_env
from tools.lookup.tool import web_search


CASES = [
    {
        "id": "contract_status",
        "query": "Bernardo Silva",
        "intent": "signed contract new club",
        "topic": "news",
        "timeframe": "year",
        "strict_timeframe": False,
    },
    {
        "id": "explicit_today",
        "query": "Liverpool",
        "intent": "football news today",
        "topic": "news",
        "timeframe": "day",
        "strict_timeframe": True,
    },
    {
        "id": "injury_update",
        "query": "Rodri",
        "intent": "injury fitness update",
        "topic": "news",
        "timeframe": "month",
        "strict_timeframe": False,
    },
    {
        "id": "match_result",
        "query": "Real Madrid",
        "intent": "latest match result score",
        "topic": "news",
        "timeframe": "week",
        "strict_timeframe": False,
    },
]


def main() -> None:
    load_lab_env(ROOT)
    output = []
    for case in CASES:
        params = {key: value for key, value in case.items() if key != "id"}
        result = web_search(**params, max_results=3)
        output.append({
            "id": case["id"],
            "quality": result.get("quality"),
            "warning": result.get("warning"),
            "attempts": result.get("attempts"),
            "error": result.get("error"),
            "items": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published_date": item.get("published_date"),
                    "score": item.get("score"),
                }
                for item in result.get("items") or []
            ],
        })
    # ASCII-safe output keeps the smoke script usable in Windows PowerShell
    # sessions that still use a legacy code page.
    print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
