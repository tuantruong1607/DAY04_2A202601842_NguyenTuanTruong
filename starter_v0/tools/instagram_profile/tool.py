from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


DEFAULT_HOST = "instagram-statistics-api.p.rapidapi.com"


def _normalize_profile_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("profile_url is required")
    if value.startswith("@"):
        value = value[1:]
    if "://" not in value:
        if "/" not in value:
            value = f"https://www.instagram.com/{value}/"
        else:
            value = f"https://{value.lstrip('/')}"
    if domain(value).lower() not in {"instagram.com", "m.instagram.com"}:
        raise ValueError("profile_url must point to instagram.com")
    return value


def _find_first(value: Any, names: tuple[str, ...]) -> Any | None:
    if isinstance(value, dict):
        for name in names:
            candidate = value.get(name)
            if candidate not in (None, "", [], {}):
                return candidate
        for child in value.values():
            candidate = _find_first(child, names)
            if candidate not in (None, "", [], {}):
                return candidate
    elif isinstance(value, list):
        for child in value:
            candidate = _find_first(child, names)
            if candidate not in (None, "", [], {}):
                return candidate
    return None


def _profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if isinstance(data, list):
        return data[0] if data and isinstance(data[0], dict) else {"data": data}
    if isinstance(data, dict):
        return data
    return {"data": data}


def _normalized_profile(profile: dict[str, Any], profile_url: str) -> dict[str, Any]:
    return {
        "username": _find_first(profile, ("username", "screenName", "screen_name", "login")),
        "name": _find_first(profile, ("full_name", "fullname", "name", "title")),
        "followers": _find_first(
            profile,
            (
                "followers",
                "followers_count",
                "follower_count",
                "subscribers",
                "subscribers_count",
                "usersCount",
            ),
        ),
        "engagement_rate": _find_first(
            profile,
            ("engagement_rate", "engagementRate", "engagement", "avgER"),
        ),
        "quality_score": _find_first(profile, ("quality_score", "qualityScore", "quality")),
        "verified": _find_first(profile, ("verified", "is_verified", "isVerified")),
        "average_interactions": _find_first(profile, ("avgInteractions", "average_interactions")),
        "average_views": _find_first(profile, ("avgViews", "average_views")),
        "average_likes": _find_first(profile, ("avgLikes", "average_likes")),
        "average_comments": _find_first(profile, ("avgComments", "average_comments")),
        "fake_followers_percentage": _find_first(
            profile,
            ("pctFakeFollowers", "fake_followers_percentage"),
        ),
        "country": _find_first(profile, ("country", "countryCode")),
        "profile_url": profile_url,
    }


def _summary(profile: dict[str, Any]) -> str:
    parts: list[str] = []
    if profile.get("followers") is not None:
        parts.append(f"Followers: {profile['followers']}")
    if profile.get("engagement_rate") is not None:
        parts.append(f"Engagement: {profile['engagement_rate']}")
    if profile.get("quality_score") is not None:
        parts.append(f"Quality score: {profile['quality_score']}")
    if profile.get("fake_followers_percentage") is not None:
        parts.append(f"Estimated fake followers: {profile['fake_followers_percentage']}")
    if profile.get("verified") is not None:
        parts.append(f"Verified: {profile['verified']}")
    return "; ".join(parts) or "Public Instagram profile analytics retrieved successfully."


def get_instagram_profile(profile_url: str = "") -> dict[str, Any]:
    try:
        normalized_url = _normalize_profile_url(profile_url)
        key = os.getenv("RAPIDAPI_KEY")
        host = os.getenv("RAPIDAPI_INSTAGRAM_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
        if not key:
            raise RuntimeError("Missing RAPIDAPI_KEY env var")

        response = requests.get(
            f"https://{host}/community",
            params={"url": normalized_url},
            headers={
                "x-rapidapi-key": key,
                "x-rapidapi-host": host,
            },
            timeout=max(TIMEOUT, 60),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Instagram API returned a non-object response")

        profile = _normalized_profile(_profile_payload(payload), normalized_url)
        title = profile.get("name") or profile.get("username") or normalized_url
        item = {
            "title": str(title),
            "url": normalized_url,
            "source": "instagram.com",
            "summary": _summary(profile),
        }
        return {
            "tool": "instagram_profile",
            "profile_url": normalized_url,
            "profile": profile,
            "items": [item],
            "meta": payload.get("meta", {}),
        }
    except Exception as exc:
        return err("instagram_profile", exc)
