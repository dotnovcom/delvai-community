from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.admin_deps import require_admin_permission
from app.core.database import get_db
from app.models.user import User
from app.services import chat_action_service

router = APIRouter()


@router.get("/chat-actions/feedbacks")
def admin_list_message_feedbacks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    vote: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("conversations", "read")),
):
    return chat_action_service.list_feedbacks(db, page, size, vote)


@router.get("/chat-actions/shares")
def admin_list_message_shares(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("conversations", "read")),
):
    return chat_action_service.list_shares(db, page, size)


@router.delete("/chat-actions/shares/{share_id}")
def admin_delete_message_share(
    share_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("settings", "write")),
):
    if not chat_action_service.delete_share(db, share_id):
        raise HTTPException(status_code=404, detail="分享不存在")
    return {"message": "已删除"}
