---
name: instagram_profile
track: core
kind: live_api
provider: Instagram Statistics API via RapidAPI
requires_env: [RAPIDAPI_KEY, RAPIDAPI_INSTAGRAM_HOST]
inputs: [profile_url]
outputs: [items, profile, meta]
side_effect: false
---

# Instagram Profile Analytics

Looks up public Instagram profile analytics from a profile URL or handle.

Use this tool when the user asks for public Instagram profile statistics such
as follower count, engagement, quality score, verification status, or audience
metadata. Do not use it for recent X/Twitter posts, topic search, private
profiles, posting content, or account authentication.

`profile_url` accepts a full Instagram profile URL, `@handle`, or a bare handle.
The implementation normalizes handles to `https://www.instagram.com/<handle>/`.

