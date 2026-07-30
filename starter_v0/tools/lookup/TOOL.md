---
name: lookup
track: core
kind: live_api
provider: Tavily
requires_env: [TAVILY_API_KEY]
inputs: [query, intent, topic, timeframe, max_results]
outputs: [items]
side_effect: false
---
# lookup

Searches the web via Tavily. It preserves the stable subject in `query`, uses
`intent` to improve the provider query, filters off-topic results, keeps
publication dates, and retries with a broader window only when the user did not
explicitly constrain that window. The runtime guard enforces this distinction.
