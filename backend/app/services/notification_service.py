"""用户站内信。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.user_notification import UserNotification


def create_user_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    *,
    category: str = "system",
    metadata: dict | None = None,
    commit: bool = True,
) -> UserNotification:
    row = UserNotification(
        user_id=user_id,
        title=title,
        content=content,
        category=category,
        metadata_json=metadata,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def list_user_notifications(
    db: Session,
    user_id: int,
    *,
    page: int = 1,
    size: int = 20,
    unread_only: bool = False,
    category: str | None = None,
    category_prefix: str | None = None,
) -> dict[str, Any]:
    q = db.query(UserNotification).filter(UserNotification.user_id == user_id)
    if unread_only:
        q = q.filter(UserNotification.read_at.is_(None))
    if category:
        q = q.filter(UserNotification.category == category)
    elif category_prefix:
        q = q.filter(UserNotification.category.like(f"{category_prefix}%"))
    total = q.count()
    rows = (
        q.order_by(UserNotification.created_at.desc())
        .offset((page - 1) * size)
        .limit(min(size, 100))
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "category": n.category,
                "metadata": n.metadata_json,
                "read_at": n.read_at,
                "created_at": n.created_at,
            }
            for n in rows
        ],
    }


def count_unread_notifications(
    db: Session,
    user_id: int,
    *,
    category_prefix: str | None = None,
) -> int:
    q = db.query(UserNotification).filter(UserNotification.user_id == user_id, UserNotification.read_at.is_(None))
    if category_prefix:
        q = q.filter(UserNotification.category.like(f"{category_prefix}%"))
    return q.count()


def mark_notification_read(db: Session, user_id: int, notification_id: int) -> None:
    row = (
        db.query(UserNotification)
        .filter(UserNotification.id == notification_id, UserNotification.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("消息不存在")
    if not row.read_at:
        row.read_at = datetime.now(timezone.utc)
        db.commit()


def mark_all_notifications_read(
    db: Session,
    user_id: int,
    *,
    category_prefix: str | None = None,
) -> int:
    now = datetime.now(timezone.utc)
    q = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.read_at.is_(None),
    )
    if category_prefix:
        q = q.filter(UserNotification.category.like(f"{category_prefix}%"))
    rows = q.all()
    for row in rows:
        row.read_at = now
    db.commit()
    return len(rows)
