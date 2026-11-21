import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.conversation_tasks.cleanup_expired_conversations")
def cleanup_expired_conversations() -> dict:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func

    from app.models.conversation import Conversation, ConversationStatus
    from commercial.models.membership import MembershipStatus, UserMembership
    from app.models.message import Message
    from app.services.runtime_config import get_int

    session = SessionLocal()
    deleted_msgs = 0
    archived = 0
    try:
        free_days = get_int(session, "history_retention_days_free", 7)
        cutoff = datetime.now(timezone.utc) - timedelta(days=free_days)
        active_paid = (
            session.query(UserMembership.user_id)
            .filter(
                UserMembership.status == MembershipStatus.ACTIVE,
                UserMembership.level > 0,
            )
            .all()
        )
        paid_ids = {r[0] for r in active_paid}
        old_convs = (
            session.query(Conversation)
            .filter(
                Conversation.updated_at < cutoff,
                Conversation.status == ConversationStatus.ACTIVE,
            )
            .limit(500)
            .all()
        )
        for conv in old_convs:
            if conv.user_id in paid_ids:
                continue
            cnt = session.query(func.count(Message.id)).filter(Message.conversation_id == conv.id).scalar() or 0
            session.query(Message).filter(Message.conversation_id == conv.id).delete()
            conv.status = ConversationStatus.DELETED
            deleted_msgs += int(cnt)
            archived += 1
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("cleanup conversations failed: %s", exc)
        return {"error": str(exc)}
    finally:
        session.close()
    return {"archived_conversations": archived, "deleted_messages": deleted_msgs}
