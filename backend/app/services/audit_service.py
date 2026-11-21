import logging

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=detail,
        ip=ip,
    )
    db.add(entry)
    db.commit()
    logger.info(
        "AUDIT user=%s action=%s resource=%s/%s detail=%s ip=%s",
        user_id, action, resource, resource_id, detail, ip,
    )
