"""TikTok OAuth: /login sends the user to TikTok, /callback stores the account."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import tiktok
from ..config import settings
from ..crypto import encrypt
from ..database import get_db
from ..models import Account

router = APIRouter(prefix="/api/auth/tiktok", tags=["auth"])

# In-memory store mapping OAuth `state` -> PKCE verifier.
# Fine for a local single-user app; use Redis/DB if you deploy multi-user.
_pending: dict[str, str] = {}


@router.get("/login")
def login():
    verifier, challenge = tiktok.make_pkce_pair()
    state = secrets.token_urlsafe(24)
    _pending[state] = verifier
    url = tiktok.build_authorize_url(state, challenge)
    return {"authorize_url": url}


@router.get("/callback")
async def callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{settings.frontend_url}/?error={error}")
    verifier = _pending.pop(state, None)
    if not code or verifier is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    bundle = await tiktok.exchange_code(code, verifier)
    user = await tiktok.get_user_info(bundle.access_token)
    open_id = user.get("open_id") or bundle.open_id
    now = datetime.now(timezone.utc)

    account = db.query(Account).filter(Account.open_id == open_id).first()
    if account is None:
        account = Account(open_id=open_id)
        db.add(account)

    account.union_id = user.get("union_id")
    account.display_name = user.get("display_name")
    account.avatar_url = user.get("avatar_url")
    account.access_token = encrypt(bundle.access_token)
    account.refresh_token = encrypt(bundle.refresh_token)
    account.access_expires_at = now + timedelta(seconds=bundle.expires_in)
    account.refresh_expires_at = now + timedelta(seconds=bundle.refresh_expires_in)
    account.follower_count = user.get("follower_count", 0)
    account.following_count = user.get("following_count", 0)
    account.likes_count = user.get("likes_count", 0)
    account.video_count = user.get("video_count", 0)
    db.commit()

    return RedirectResponse(f"{settings.frontend_url}/?connected=1")
