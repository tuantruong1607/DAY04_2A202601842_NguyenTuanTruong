from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from chat import evidence_items, normalize_runtime_tool_call, tool_usage_counts
from providers.base import ToolCall
from tools.fetch.tool import read_url
from tools.lookup.tool import web_search
from tools.social_search.tool import search_tweets


def response(payload: dict) -> Mock:
    item = Mock()
    item.raise_for_status.return_value = None
    item.json.return_value = payload
    return item


class LookupFreshnessTests(unittest.TestCase):
    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"})
    @patch("tools.lookup.tool.requests.post")
    def test_broadens_and_keeps_only_relevant_dated_results(self, post: Mock) -> None:
        irrelevant = {
            "results": [{
                "title": "Rodri undergoes surgery",
                "url": "https://example.com/rodri",
                "content": "A Manchester City update about Rodri.",
                "score": 0.08,
                "published_date": "Tue, 28 Jul 2026 10:00:00 GMT",
            }]
        }
        relevant = {
            "results": [
                {
                    "title": "Bernardo Silva signs for Real Madrid",
                    "url": "https://example.com/bernardo-official",
                    "content": "Bernardo Silva joined Real Madrid on a two-year contract.",
                    "score": 0.91,
                    "published_date": "Wed, 17 Jun 2026 09:51:57 GMT",
                },
                {
                    "title": "Real Madrid confirm Bernardo Silva deal",
                    "url": "https://example.net/bernardo-confirmed",
                    "content": "The club confirmed the Bernardo Silva signing and contract.",
                    "score": 0.84,
                    "published_date": "Wed, 17 Jun 2026 10:10:00 GMT",
                },
            ]
        }

        def fake_post(*_args, **kwargs):
            payload = relevant if kwargs["json"].get("time_range") == "year" else irrelevant
            return response(payload)

        post.side_effect = fake_post
        result = web_search(
            "Bernardo Silva",
            topic="news",
            timeframe="day",
            intent="signed contract new club",
            strict_timeframe=False,
        )

        self.assertEqual(result["quality"]["status"], "sufficient")
        self.assertTrue(result["quality"]["timeframe_broadened"])
        self.assertEqual(len(result["items"]), 2)
        self.assertTrue(all("Bernardo" in item["title"] for item in result["items"]))
        self.assertEqual(result["items"][0]["published_date"], "Wed, 17 Jun 2026 09:51:57 GMT")
        self.assertEqual(result["attempts"][-1]["timeframe"], "year")

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"})
    @patch("tools.lookup.tool.requests.post")
    def test_explicit_day_window_is_never_broadened(self, post: Mock) -> None:
        post.return_value = response({"results": []})
        result = web_search(
            "Liverpool",
            topic="news",
            timeframe="day",
            intent="football news today",
            strict_timeframe=True,
        )

        self.assertEqual(result["quality"]["status"], "no_relevant_results")
        self.assertFalse(result["quality"]["timeframe_broadened"])
        self.assertEqual({attempt["timeframe"] for attempt in result["attempts"]}, {"day"})


class FetchFreshnessTests(unittest.TestCase):
    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("tools.fetch.tool.requests.post")
    def test_fetch_forces_fresh_scrape_and_preserves_dates(self, post: Mock) -> None:
        post.return_value = response({
            "data": {
                "markdown": "Latest club announcement",
                "metadata": {
                    "title": "Club announcement",
                    "sourceURL": "https://club.example/news/1",
                    "publishedTime": "2026-07-29T08:00:00Z",
                    "modifiedTime": "2026-07-29T09:00:00Z",
                    "cacheState": "miss",
                },
            }
        })

        result = read_url("https://club.example/news/1")

        self.assertEqual(post.call_args.kwargs["json"]["maxAge"], 0)
        self.assertEqual(result["cache_state"], "miss")
        self.assertEqual(result["items"][0]["published_date"], "2026-07-29T08:00:00Z")


class EvidenceAndFallbackTests(unittest.TestCase):
    def test_tool_usage_counts_preserves_order_and_counts_retries(self) -> None:
        usage = tool_usage_counts([
            {"tool": "lookup"},
            {"tool": "fetch"},
            {"tool": "lookup"},
            {"tool": ""},
        ])

        self.assertEqual(usage, [("lookup", 2), ("fetch", 1)])

    def test_runtime_guard_enforces_confirmation_shape_for_external_action(self) -> None:
        call = ToolCall("clarify", {
            "question": "Bạn muốn đăng nội dung nào?",
            "response_type": "text",
        })

        normalized = normalize_runtime_tool_call(
            call,
            "Đăng bản tin này lên Telegram giúp mình",
        )

        self.assertEqual(normalized.args["response_type"], "yes_no")

    def test_runtime_guard_rewrites_unstated_day_for_completed_transfer(self) -> None:
        call = ToolCall("lookup", {
            "query": "Bernardo Silva",
            "topic": "news",
            "timeframe": "day",
        })

        normalized = normalize_runtime_tool_call(
            call,
            "Bernardo Silva đã ký hợp đồng với câu lạc bộ nào?",
        )

        self.assertEqual(normalized.args["timeframe"], "year")
        self.assertFalse(normalized.args["strict_timeframe"])
        self.assertIn("Bernardo Silva", normalized.args["intent"])

    def test_runtime_guard_preserves_explicit_today(self) -> None:
        call = ToolCall("lookup", {
            "query": "Liverpool",
            "intent": "football news",
            "topic": "news",
            "timeframe": "week",
        })

        normalized = normalize_runtime_tool_call(call, "Cho tôi tin Liverpool hôm nay")

        self.assertEqual(normalized.args["timeframe"], "day")
        self.assertTrue(normalized.args["strict_timeframe"])

    def test_evidence_index_keeps_freshness_and_backend(self) -> None:
        items = evidence_items([{
            "tool": "lookup",
            "result": {
                "retrieved_at": "2026-07-29T10:00:00+00:00",
                "backend": "test_backend",
                "items": [{
                    "title": "A football update",
                    "url": "https://example.com/update",
                    "source": "example.com",
                    "summary": "Summary",
                    "published_date": "2026-07-29T09:00:00Z",
                }],
            },
        }])

        self.assertEqual(items[0]["published_date"], "2026-07-29T09:00:00Z")
        self.assertEqual(items[0]["backend"], "test_backend")

    @patch.dict(os.environ, {}, clear=True)
    @patch("tools.social_search.tool.web_search")
    def test_social_fallback_does_not_return_non_x_pages(self, lookup: Mock) -> None:
        lookup.return_value = {
            "items": [{
                "title": "News page",
                "url": "https://example.com/not-x",
                "source": "example.com",
                "summary": "A news article",
            }]
        }

        result = search_tweets("Champions League")

        self.assertEqual(result["backend"], "tavily_x_index_fallback")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["quality"]["status"], "no_relevant_results")
        self.assertFalse(result["quality"]["live"])


if __name__ == "__main__":
    unittest.main()
