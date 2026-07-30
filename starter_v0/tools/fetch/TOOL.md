---
name: fetch
track: core
kind: live_api
provider: Firecrawl
requires_env: [FIRECRAWL_API_KEY]
inputs: [url, max_age]
outputs: [items]
side_effect: false
---
# fetch

Reads the content of a single URL via Firecrawl. News fetches default to
`max_age=0` so the response does not silently reuse cached page content.
