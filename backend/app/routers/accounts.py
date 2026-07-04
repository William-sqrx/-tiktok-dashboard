"""Read endpoints for the dashboard + manual sync triggers."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import sync as sync_service
from .. import tiktok
from ..database import get_db
from ..models import Account, StatSnapshot, Video

router = APIRouter(prefix="/api", tags=["accounts"])


def _account_summary(a: Account) -> dict:
    return {
        "id": a.id,
        "open_id": a.open_id,
        "display_name": a.display_name,
        "avatar_url": a.avatar_url,
        "follower_count": a.follower_count,
        "following_count": a.following_count,
        "likes_count": a.likes_count,
        "video_count": a.video_count,
        "last_synced_at": a.last_synced_at.isoformat() if a.last_synced_at else None,
    }


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).order_by(Account.created_at).all()
    return [_account_summary(a) for a in accounts]


def _get_account(db: Session, account_id: int) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/accounts/{account_id}/videos")
def account_videos(account_id: int, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    videos = (
        db.query(Video)
        .filter(Video.account_id == account_id)
        .order_by(Video.create_time.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "video_id": v.video_id,
            "title": v.title,
            "cover_image_url": v.cover_image_url,
            "share_url": v.share_url,
            "embed_link": v.embed_link,
            "duration": v.duration,
            "create_time": v.create_time.isoformat() if v.create_time else None,
            "view_count": v.view_count,
            "like_count": v.like_count,
            "comment_count": v.comment_count,
            "share_count": v.share_count,
        }
        for v in videos
    ]


@router.get("/accounts/{account_id}/history")
def account_history(account_id: int, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    rows = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.account_id == account_id)
        .order_by(StatSnapshot.captured_at)
        .all()
    )
    return [
        {
            "captured_at": r.captured_at.isoformat() if r.captured_at else None,
            "follower_count": r.follower_count,
            "likes_count": r.likes_count,
            "video_count": r.video_count,
        }
        for r in rows
    ]


@router.post("/accounts/{account_id}/sync")
async def sync_one(account_id: int, db: Session = Depends(get_db)):
    account = _get_account(db, account_id)
    try:
        await sync_service.sync_account(db, account)
    except tiktok.TikTokError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _account_summary(account)


@router.post("/sync")
async def sync_all(db: Session = Depends(get_db)):
    results = []
    for account in db.query(Account).all():
        try:
            await sync_service.sync_account(db, account)
            results.append({"id": account.id, "ok": True})
        except tiktok.TikTokError as e:
            results.append({"id": account.id, "ok": False, "error": str(e)})
    return {"results": results}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = _get_account(db, account_id)
    db.delete(account)
    db.commit()
    return {"deleted": account_id}
