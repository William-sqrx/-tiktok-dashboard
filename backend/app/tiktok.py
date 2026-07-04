"""Thin client for TikTok's v2 OAuth + Display API.

Docs: https://developers.tiktok.com/doc/login-kit-web
      https://developers.tiktok.com/doc/display-api-get-started
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from .config import settings


# Fields we ask the Display API to return for each video.
VIDEO_FIELDS = [
    "id",
    "title",
    "cover_image_url",
    "share_url",
    "embed_link",
    "duration",
    "create_time",
    "view_count",
    "like_count",
    "comment_count",
    "share_count",
]

USER_FIELDS = [
    "open_id",
    "union_id",
    "avatar_url",
    "display_name",
    "follower_count",
    "following_count",
    "likes_count",
    "video_count",
]


def make_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for the PKCE S256 flow."""
    verifier = secrets.token_urlsafe(64)[:96]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def build_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "client_key": settings.tiktok_client_key,
        "response_type": "code",
        "scope": settings.tiktok_scopes,
        "redirect_uri": settings.tiktok_redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{settings.authorize_url}?{urlencode(params)}"


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    open_id: str


async def exchange_code(code: str, code_verifier: str) -> TokenBundle:
    data = {
        "client_key": settings.tiktok_client_key,
        "client_secret": settings.tiktok_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.tiktok_redirect_uri,
        "code_verifier": code_verifier,
    }
    return await _post_token(data)


async def refresh_access_token(refresh_token: str) -> TokenBundle:
    data = {
        "client_key": settings.tiktok_client_key,
        "client_secret": settings.tiktok_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    return await _post_token(data)


async def _post_token(data: dict) -> TokenBundle:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.token_url, data=data, headers=headers)
    payload = resp.json()
    if resp.status_code != 200 or "access_token" not in payload:
        raise TikTokError(f"Token request failed: {payload}")
    return TokenBundle(
        access_token=payload["access_token"],
        refresh_token=payload["refresh_token"],
        expires_in=payload.get("expires_in", 0),
        refresh_expires_in=payload.get("refresh_expires_in", 0),
        open_id=payload.get("open_id", ""),
    )


async def get_user_info(access_token: str) -> dict:
    params = {"fields": ",".join(USER_FIELDS)}
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            settings.user_info_url, params=params, headers=headers
        )
    payload = resp.json()
    _raise_for_api_error(payload)
    return payload.get("data", {}).get("user", {})


async def list_videos(access_token: str, max_count: int = 20) -> list[dict]:
    """Return the account's videos. Pages through until TikTok says has_more=False."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params = {"fields": ",".join(VIDEO_FIELDS)}
    videos: list[dict] = []
    cursor = None

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            body: dict = {"max_count": max_count}
            if cursor is not None:
                body["cursor"] = cursor
            resp = await client.post(
                settings.video_list_url, params=params, headers=headers, json=body
            )
            payload = resp.json()
            _raise_for_api_error(payload)
            data = payload.get("data", {})
            videos.extend(data.get("videos", []))
            if not data.get("has_more"):
                break
            cursor = data.get("cursor")
    return videos


def _raise_for_api_error(payload: dict) -> None:
    err = payload.get("error", {})
    # TikTok returns error.code == "ok" on success.
    if err and err.get("code") not in (None, "ok"):
        raise TikTokError(f"{err.get('code')}: {err.get('message')}")


class TikTokError(Exception):
    pass
