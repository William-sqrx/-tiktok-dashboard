"""Analytics via PostPeer: creator info + per-video metrics for each posting
account. Replaces the TikTok-developer-app OAuth flow entirely."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import PostingAccount

router = APIRouter(prefix="/api/pp", tags=["postpeer"])


async def _pp_get(path: str, params: dict | None = None) -> dict:
    if not settings.postpeer_key:
        raise HTTPException(503, "POSTPEER_KEY is not set on the server")
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(
            settings.postpeer_api + path,
            params=params or {},
            headers={"x-access-key": settings.postpeer_key},
        )
    if r.status_code != 200:
        raise HTTPException(502, f"PostPeer error {r.status_code}: {r.text[:300]}")
    return r.json()


def _integration_id(db: Session, account_id: int) -> str:
    acc = db.query(PostingAccount).get(account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    return acc.upload_post_user  # holds the PostPeer integration id


@router.get("/accounts/{account_id}/info")
async def creator_info(account_id: int, db: Session = Depends(get_db)):
    iid = _integration_id(db, account_id)
    resp = await _pp_get("/tiktok/creator-info", {"accountId": iid})
    return resp.get("data", {})


@router.get("/accounts/{account_id}/posts")
async def account_posts(account_id: int, db: Session = Depends(get_db)):
    """Videos with live metrics, fetched straight from the TikTok account."""
    iid = _integration_id(db, account_id)
    resp = await _pp_get(
        "/analytics/",
        {"platform": "tiktok", "accountId": iid, "source": "platform",
         "limit": 50},
    )
    out = []
    for p in resp.get("posts", []):
        agg = p.get("aggregated") or {}
        plat = (p.get("platforms") or [{}])[0]
        out.append({
            "content": p.get("content"),
            "published_at": p.get("publishedAt"),
            "url": plat.get("platformPostUrl"),
            "views": agg.get("views") or 0,
            "likes": agg.get("likes") or 0,
            "comments": agg.get("comments") or 0,
            "shares": agg.get("shares") or 0,
            "saves": agg.get("saves") or 0,
        })
    return out
