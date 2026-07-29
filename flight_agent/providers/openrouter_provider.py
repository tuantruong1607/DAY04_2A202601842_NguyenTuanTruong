"""OpenAI-compatible chat-completions client for OpenRouter, via `requests`
(no `openai` SDK dependency). OpenRouter's Chat Completions surface matches
OpenAI's tool-calling shape, so this same client works unmodified against
OpenAI-compatible endpoints in general if OPENROUTER_BASE_URL is repointed.
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

from providers.base import ModelResponse, ToolCall

TIMEOUT = 60


class OpenRouterError(Exception):
    pass


class OpenRouterProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.default_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> ModelResponse:
        if not self.api_key:
            raise OpenRouterError("Missing OPENROUTER_API_KEY env var")

        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            raise OpenRouterError(f"OpenRouter HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError(f"OpenRouter returned no choices: {data}")
        message = choices[0].get("message", {})

        tool_calls: list[ToolCall] = []
        for raw_call in message.get("tool_calls") or []:
            function = raw_call.get("function", {})
            try:
                args = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=raw_call.get("id", ""), name=function.get("name", ""), args=args))

        return ModelResponse(text=message.get("content"), tool_calls=tool_calls, raw=data)
