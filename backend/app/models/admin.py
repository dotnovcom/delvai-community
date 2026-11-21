import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentCategory(str, enum.Enum):
    LEGAL_NEWS = "legal_news"
    POLICY = "policy"
    ANNOUNCEMENT = "announcement"
    GUIDE = "guide"


class PushStatus(str, enum.Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class PushTargetType(str, enum.Enum):
    USER = "user"
    TAG = "tag"
    ALL = "all"


class ContentArticle(Base):
    __tablename__ = "content_articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default=ContentCategory.LEGAL_NEWS.value)
    cover_url: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default=ContentStatus.DRAFT.value)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PushTask(Base):
    __tablename__ = "push_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    target_type: Mapped[str] = mapped_column(String(16))
    target_value: Mapped[str | None] = mapped_column(String(256))
    push_type: Mapped[str] = mapped_column(String(32), default="legal_news")
    status: Mapped[str] = mapped_column(String(16), default=PushStatus.PENDING.value)
    sent_count: Mapped[int] = mapped_column(default=0)
    payload: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
