from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    open_id = Column(String, unique=True, nullable=False)  # TikTok's stable user id
    union_id = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    # OAuth tokens, stored encrypted (see crypto.py)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    access_expires_at = Column(DateTime(timezone=True), nullable=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Latest profile stats (denormalized for quick dashboard reads)
    follower_count = Column(BigInteger, default=0)
    following_count = Column(BigInteger, default=0)
    likes_count = Column(BigInteger, default=0)
    video_count = Column(BigInteger, default=0)

    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    videos = relationship(
        "Video", back_populates="account", cascade="all, delete-orphan"
    )
    snapshots = relationship(
        "StatSnapshot", back_populates="account", cascade="all, delete-orphan"
    )


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("account_id", "video_id"),)

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    video_id = Column(String, nullable=False)

    title = Column(Text, nullable=True)
    cover_image_url = Column(String, nullable=True)
    share_url = Column(String, nullable=True)
    embed_link = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    create_time = Column(DateTime(timezone=True), nullable=True)

    view_count = Column(BigInteger, default=0)
    like_count = Column(BigInteger, default=0)
    comment_count = Column(BigInteger, default=0)
    share_count = Column(BigInteger, default=0)

    last_synced_at = Column(DateTime(timezone=True), default=_now)

    account = relationship("Account", back_populates="videos")


class StatSnapshot(Base):
    """One row per account per sync — powers the trend charts."""

    __tablename__ = "stat_snapshots"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    captured_at = Column(DateTime(timezone=True), default=_now)

    follower_count = Column(BigInteger, default=0)
    likes_count = Column(BigInteger, default=0)
    video_count = Column(BigInteger, default=0)

    account = relationship("Account", back_populates="snapshots")
