import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BannerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"
    REPLIED = "replied"
    CLOSED = "closed"


class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128))
    image_url: Mapped[str] = mapped_column(String(1024))
    link_url: Mapped[str | None] = mapped_column(String(1024))
    position: Mapped[str] = mapped_column(String(32), default="home")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default=BannerStatus.ACTIVE.value)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LaunchSplashContentType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    HTML = "html"


# 平台：mp-weixin / mp-toutiao / h5 / wechat_h5 / app-android / app-ios / app-harmony
LAUNCH_SPLASH_PLATFORMS = (
    "mp-weixin",
    "mp-toutiao",
    "h5",
    "wechat_h5",
    "app-android",
    "app-ios",
    "app-harmony",
)


class LaunchSplash(Base):
    __tablename__ = "launch_splashes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    platform: Mapped[str] = mapped_column(String(32), index=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    content_type: Mapped[str] = mapped_column(String(16), default=LaunchSplashContentType.IMAGE.value)
    media_url: Mapped[str | None] = mapped_column(String(1024))
    html_content: Mapped[str | None] = mapped_column(Text)
    link_url: Mapped[str | None] = mapped_column(String(1024))
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    allow_skip: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default=BannerStatus.ACTIVE.value)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    category: Mapped[str] = mapped_column(String(32), default="general")
    content: Mapped[str] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default=FeedbackStatus.PENDING.value)
    admin_reply: Mapped[str | None] = mapped_column(Text)
    replied_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
