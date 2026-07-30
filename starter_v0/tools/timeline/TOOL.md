---
name: timeline
track: core
kind: live_api
provider: RapidAPI Twitter with Tavily web-index fallback
requires_env: [TAVILY_API_KEY]
inputs: [screenname, limit]
outputs: [items]
side_effect: false
---
# timeline

Fetches recent posts from a single account. `screenname` is an account handle
without `@`.

If `RAPIDAPI_TWITTER_HOST` and `RAPIDAPI_KEY` are configured, the tool tries the
live Twitter provider first. Otherwise it falls back to Tavily-indexed public X
pages and labels the backend in its result.
