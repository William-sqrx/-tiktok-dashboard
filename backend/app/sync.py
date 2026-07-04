"""Pull fresh data from TikTok into the local DB."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from . import tiktok
from .crypto import decrypt, encrypt
from .models import Account, StatSnapshot, Video


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_fresh_token(db: Session, account: Account) -> str:
    """Return a valid access token, refreshing it first if it's near expiry."""
    expires = account.access_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires is None or expires <= _now() + timedelta(minutes=5):
        bundle = await tiktok.refresh_access_token(decrypt(account.refresh_token))
        account.access_token = encrypt(bundle.access_token)
        account.refresh_token = encrypt(bundle.refresh_token)
        account.access_expires_at = _now() + timedelta(seconds=bundle.expires_in)
        account.refresh_expires_at = _now() + timedelta(
            seconds=bundle.refresh_expires_in
        )
        db.commit()

    return decrypt(account.access_token)


async def sync_account(db: Session, account: Account) -> None:
    access_token = await ensure_fresh_token(db, account)

    # 1. Profile stats
    user = await tiktok.get_user_info(access_token)
    account.display_name = user.get("display_name") or account.display_name
    account.avatar_url = user.get("avatar_url") or account.avatar_url
    account.follower_count = user.get("follower_count", account.follower_count)
    account.following_count = user.get("following_count", account.following_count)
    account.likes_count = user.get("likes_count", account.likes_count)
    account.video_count = user.get("video_count", account.video_count)

    # 2. Trend snapshot
    db.add(
        StatSnapshot(
            account_id=account.id,
            follower_count=account.follower_count,
            likes_count=account.likes_count,
            video_count=account.video_count,
        )
    )

    # 3. Videos — upsert each one
    videos = await tiktok.list_videos(access_token)
    existing = {v.video_id: v for v in account.videos}
    for item in videos:
        vid = str(item.get("id"))
        row = existing.get(vid) or Video(account_id=account.id, video_id=vid)
        row.title = item.get("title")
        row.cover_image_url = item.get("cover_image_url")
        row.share_url = item.get("share_url")
        row.embed_link = item.get("embed_link")
        row.duration = item.get("duration")
        ct = item.get("create_time")
        row.create_time = (
            datetime.fromtimestamp(ct, tz=timezone.utc) if ct else None
        )
        row.view_count = item.get("view_count", 0)
        row.like_count = item.get("like_count", 0)
        row.comment_count = item.get("comment_count", 0)
        row.share_count = item.get("share_count", 0)
        row.last_synced_at = _now()
        if row.id is None:
            db.add(row)

    account.last_synced_at = _now()
    db.commit()
