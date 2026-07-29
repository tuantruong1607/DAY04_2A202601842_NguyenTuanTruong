from __future__ import annotations

import os

from providers.openai_provider import OpenAIProvider
from providers.openrouter_provider import OpenRouterProvider

__all__ = ["OpenAIProvider", "OpenRouterProvider", "make_provider"]


def make_provider(name: str | None = None) -> OpenAIProvider | OpenRouterProvider:
    """Pick a provider by name, or auto-detect from whichever API key is set
    (OPENAI_API_KEY checked first, then OPENROUTER_API_KEY)."""
    if name == "openai":
        return OpenAIProvider()
    if name == "openrouter":
        return OpenRouterProvider()
    if name:
        raise ValueError(f"Unknown provider: {name}")

    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider()
    if os.getenv("OPENROUTER_API_KEY"):
        return OpenRouterProvider()
    raise RuntimeError("No provider API key set. Fill OPENAI_API_KEY or OPENROUTER_API_KEY in .env")
