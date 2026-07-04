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


class PostingAccount(Base):
    """One of the TikTok accounts we schedule posts to.

    Maps a friendly name to the upload-post.com profile ("user") that is
    connected to that TikTok account, so the worker knows where to post.
    """

    __tablename__ = "posting_accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g. "HSK Fish Main"
    upload_post_user = Column(String, nullable=False)  # upload-post.com profile
    color = Column(String, nullable=True)  # calendar dot color
    created_at = Column(DateTime(timezone=True), default=_now)

    posts = relationship(
        "ScheduledPost", back_populates="account", cascade="all, delete-orphan"
    )


class ScheduledPost(Base):
    """A song queued to be generated into a video and posted at a given time."""

    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True)
    posting_account_id = Column(
        Integer, ForeignKey("posting_accounts.id"), nullable=False
    )

    # What to make
    song_query = Column(Text, nullable=False)  # song name or YouTube URL
    title = Column(String, nullable=True)
    artist = Column(String, nullable=True)
    caption = Column(Text, nullable=True)  # optional override

    # When to post
    scheduled_at = Column(DateTime(timezone=True), nullable=False)

    # Lifecycle: pending -> generating -> ready -> posting -> posted / error
    status = Column(String, default="pending", nullable=False)
    video_path = Column(Text, nullable=True)  # set by the worker after render
    post_result = Column(Text, nullable=True)  # upload-post.com response / url
    error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    account = relationship("PostingAccount", back_populates="posts")
