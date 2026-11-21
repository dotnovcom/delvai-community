import secrets

from sqlalchemy.orm import Session

from app.models.message import Message, MessageRole
from app.models.message_action import MessageFeedback, MessageShare
from app.models.user import User
from app.services.config_service import get_bool_setting, get_setting


AI_ACTION_KEYS = (
    "ai_action_copy",
    "ai_action_regenerate",
    "ai_action_like",
    "ai_action_dislike",
    "ai_action_speak",
    "ai_action_share",
)


def ai_chat_ui(db: Session) -> dict:
    from app.services.storage_service import public_base_url
    from app.utils.file_tokens import refresh_signed_file_url
    from app.utils.public_url import ensure_https_asset_url

    avatar = (get_setting(db, "ai_reply_avatar", "") or "").strip()
    if avatar:
        avatar = ensure_https_asset_url(
            refresh_signed_file_url(avatar, public_base=public_base_url(db))
        )
    return {
        "avatar": avatar,
        "copy": get_bool_setting(db, "ai_action_copy", True),
        "regenerate": get_bool_setting(db, "ai_action_regenerate", True),
        "like": get_bool_setting(db, "ai_action_like", True),
        "dislike": get_bool_setting(db, "ai_action_dislike", True),
        "speak": get_bool_setting(db, "ai_action_speak", True),
        "share": get_bool_setting(db, "ai_action_share", True),
    }


def action_enabled(db: Session, key: str) -> bool:
    return get_bool_setting(db, key, True)


def feedback_map(db: Session, user_id: int, message_ids: list[int]) -> dict[int, str]:
    if not message_ids:
        return {}
    rows = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.user_id == user_id, MessageFeedback.message_id.in_(message_ids))
        .all()
    )
    return {row.message_id: row.vote for row in rows}


def set_feedback(db: Session, user: User, message: Message, vote: str | None) -> str | None:
    row = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == message.id, MessageFeedback.user_id == user.id)
        .first()
    )
    if not vote:
        if row:
            db.delete(row)
            db.commit()
        return None
    if row:
        row.vote = vote
    else:
        row = MessageFeedback(message_id=message.id, user_id=user.id, vote=vote)
        db.add(row)
    db.commit()
    return vote


def _question_before(db: Session, message: Message) -> str:
    prev = (
        db.query(Message)
        .filter(
            Message.conversation_id == message.conversation_id,
            Message.role == MessageRole.USER,
            Message.id < message.id,
        )
        .order_by(Message.id.desc())
        .first()
    )
    return prev.content if prev else ""


def create_share(db: Session, user: User, message: Message) -> MessageShare:
    share = MessageShare(
        token=secrets.token_urlsafe(18),
        message_id=message.id,
        user_id=user.id,
        question=_question_before(db, message),
        answer=message.content or "",
        view_count=0,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def get_share(db: Session, token: str) -> MessageShare | None:
    share = db.query(MessageShare).filter(MessageShare.token == token).first()
    if not share:
        return None
    share.view_count = (share.view_count or 0) + 1
    db.commit()
    db.refresh(share)
    return share


def _excerpt(text: str, limit: int = 80) -> str:
    raw = (text or "").replace("\n", " ").strip()
    return raw if len(raw) <= limit else raw[:limit] + "…"


def list_feedbacks(db: Session, page: int, size: int, vote: str | None = None) -> dict:
    q = db.query(MessageFeedback, User, Message).join(User, User.id == MessageFeedback.user_id).join(
        Message, Message.id == MessageFeedback.message_id
    )
    if vote in ("like", "dislike"):
        q = q.filter(MessageFeedback.vote == vote)
    total = q.count()
    rows = (
        q.order_by(MessageFeedback.updated_at.desc(), MessageFeedback.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    items = []
    for feedback, user, message in rows:
        items.append({
            "id": feedback.id,
            "message_id": feedback.message_id,
            "user_id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "vote": feedback.vote,
            "content": _excerpt(message.content, 120),
            "created_at": feedback.created_at,
            "updated_at": feedback.updated_at,
        })
    return {"items": items, "total": total, "page": page, "size": size}


def list_shares(db: Session, page: int, size: int) -> dict:
    q = db.query(MessageShare, User).join(User, User.id == MessageShare.user_id)
    total = q.count()
    rows = (
        q.order_by(MessageShare.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    items = []
    for share, user in rows:
        items.append({
            "id": share.id,
            "token": share.token,
            "path": f"/share/{share.token}",
            "message_id": share.message_id,
            "user_id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "question": _excerpt(share.question, 80),
            "answer": _excerpt(share.answer, 120),
            "view_count": share.view_count or 0,
            "created_at": share.created_at,
        })
    return {"items": items, "total": total, "page": page, "size": size}


def delete_share(db: Session, share_id: int) -> bool:
    row = db.query(MessageShare).filter(MessageShare.id == share_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
