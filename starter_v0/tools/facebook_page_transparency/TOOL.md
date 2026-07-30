---
name: facebook_page_transparency
track: core
kind: live_api
provider: Facebook Scraper API via RapidAPI
requires_env: [RAPIDAPI_KEY, RAPIDAPI_FACEBOOK_HOST]
inputs: [page_id]
outputs: [items, transparency]
side_effect: false
---

# Facebook Page Transparency

Retrieves public Facebook Page transparency metadata by numeric Page ID.

Use this tool to check whether a football club, league, journalist, media
outlet, or fan page is verified and to review aggregated administrator
locations, rename history, and advertising flags. This data is supporting
evidence about page identity; it does not prove that an individual football
claim is true or false.

Do not use it to access private accounts, identify individual administrators,
read Facebook posts, or publish content.

