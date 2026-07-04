"""Content scheduler: posting accounts, the calendar of scheduled posts, and
the worker endpoints that the local/cloud generator polls."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PostingAccount, ScheduledPost

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class AccountIn(BaseModel):
    name: str
    upload_post_user: str
    color: Optional[str] = None


class PostIn(BaseModel):
    posting_account_id: int
    song_query: str
    title: Optional[str] = None
    artist: Optional[str] = None
    caption: Optional[str] = None
    scheduled_at: datetime


class PostPatch(BaseModel):
    posting_account_id: Optional[int] = None
    song_query: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    caption: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None


class StatusIn(BaseModel):
    status: str
    video_path: Optional[str] = None
    post_result: Optional[str] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Serializers
# --------------------------------------------------------------------------- #
def _acc(a: PostingAccount) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "upload_post_user": a.upload_post_user,
        "color": a.color,
    }


def _post(p: ScheduledPost) -> dict:
    return {
        "id": p.id,
        "posting_account_id": p.posting_account_id,
        "account_name": p.account.name if p.account else None,
        "account_color": p.account.color if p.account else None,
        "upload_post_user": p.account.upload_post_user if p.account else None,
        "song_query": p.song_query,
        "title": p.title,
        "artist": p.artist,
        "caption": p.caption,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "status": p.status,
        "video_path": p.video_path,
        "post_result": p.post_result,
        "error": p.error,
    }


# --------------------------------------------------------------------------- #
# Posting accounts
# --------------------------------------------------------------------------- #
@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    rows = db.query(PostingAccount).order_by(PostingAccount.name).all()
    return [_acc(a) for a in rows]


@router.post("/accounts")
def create_account(body: AccountIn, db: Session = Depends(get_db)):
    a = PostingAccount(
        name=body.name, upload_post_user=body.upload_post_user, color=body.color
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _acc(a)


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    a = db.query(PostingAccount).get(account_id)
    if not a:
        raise HTTPException(404, "Account not found")
    db.delete(a)
    db.commit()
    return {"deleted": account_id}


# --------------------------------------------------------------------------- #
# Scheduled posts (calendar)
# --------------------------------------------------------------------------- #
@router.get("/posts")
def list_posts(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ScheduledPost)
    if start:
        q = q.filter(ScheduledPost.scheduled_at >= start)
    if end:
        q = q.filter(ScheduledPost.scheduled_at <= end)
    rows = q.order_by(ScheduledPost.scheduled_at).all()
    return [_post(p) for p in rows]


@router.post("/posts")
def create_post(body: PostIn, db: Session = Depends(get_db)):
    if not db.query(PostingAccount).get(body.posting_account_id):
        raise HTTPException(400, "Unknown posting account")
    p = ScheduledPost(
        posting_account_id=body.posting_account_id,
        song_query=body.song_query,
        title=body.title,
        artist=body.artist,
        caption=body.caption,
        scheduled_at=body.scheduled_at,
        status="pending",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _post(p)


@router.patch("/posts/{post_id}")
def update_post(post_id: int, body: PostPatch, db: Session = Depends(get_db)):
    p = db.query(ScheduledPost).get(post_id)
    if not p:
        raise HTTPException(404, "Post not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _post(p)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    p = db.query(ScheduledPost).get(post_id)
    if not p:
        raise HTTPException(404, "Post not found")
    db.delete(p)
    db.commit()
    return {"deleted": post_id}


# --------------------------------------------------------------------------- #
# Worker endpoints (the generator polls these; auth via X-Worker-Token gate)
# --------------------------------------------------------------------------- #
@router.get("/due")
def due_posts(db: Session = Depends(get_db)):
    """Posts whose time has arrived and still need to be generated/posted."""
    rows = (
        db.query(ScheduledPost)
        .filter(ScheduledPost.status == "pending")
        .filter(ScheduledPost.scheduled_at <= _now())
        .order_by(ScheduledPost.scheduled_at)
        .all()
    )
    return [_post(p) for p in rows]


@router.post("/posts/{post_id}/status")
def set_status(post_id: int, body: StatusIn, db: Session = Depends(get_db)):
    p = db.query(ScheduledPost).get(post_id)
    if not p:
        raise HTTPException(404, "Post not found")
    p.status = body.status
    if body.video_path is not None:
        p.video_path = body.video_path
    if body.post_result is not None:
        p.post_result = body.post_result
    if body.error is not None:
        p.error = body.error
    db.commit()
    return _post(p)
