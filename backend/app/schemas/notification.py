from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    id: int
    title: str
    content: str
    category: str
    metadata: Optional[dict] = None
    read_at: Optional[datetime] = None
    created_at: datetime


class PaginatedNotificationsResponse(BaseModel):
    total: int
    items: list[NotificationItem]


class UnreadCountResponse(BaseModel):
    count: int
