---
name: social_search
track: core
kind: live_api
provider: RapidAPI Twitter with Tavily web-index fallback
requires_env: [TAVILY_API_KEY]
inputs: [query, search_type, limit]
outputs: [items]
side_effect: false
---
# social_search

Searches posts by keyword. `search_type` orders results (`Latest` or `Top`).

If `RAPIDAPI_TWITTER_HOST` and `RAPIDAPI_KEY` are configured, the tool tries the
live Twitter provider first. Otherwise it falls back to Tavily-indexed public X
pages and labels the backend in its result.
