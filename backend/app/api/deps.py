from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token_payload
from app.models.user import User, UserStatus
from app.services.auth_service import get_user_by_id
from app.services.session_service import (
    SessionIdleExpiredError,
    SessionReplacedError,
    touch_admin_session,
    validate_user_session,
)

security_scheme = HTTPBearer(auto_error=False)

SESSION_REPLACED_DETAIL = {
    "code": SessionReplacedError.code,
    "message": SessionReplacedError.message,
}

SESSION_IDLE_EXPIRED_DETAIL = {
    "code": SessionIdleExpiredError.code,
    "message": SessionIdleExpiredError.message,
}


def _resolve_user_from_token(db: Session, token: str, *, strict_session: bool) -> User | None:
    payload = decode_access_token_payload(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None

    sid_raw = payload.get("sid")
    session_id = None
    if sid_raw is not None:
        try:
            session_id = int(sid_raw)
        except (TypeError, ValueError):
            session_id = None

    session = None
    if strict_session:
        try:
            session = validate_user_session(db, user_id, session_id)
        except SessionReplacedError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": exc.code, "message": exc.message},
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    elif session_id is not None:
        try:
            session = validate_user_session(db, user_id, session_id)
        except SessionReplacedError:
            return None

    user = get_user_by_id(db, user_id)
    if not user:
        if strict_session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
        return None
    if user.status == UserStatus.DISABLED:
        if strict_session:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
        return None

    if strict_session and session:
        try:
            touch_admin_session(db, user, session)
        except SessionIdleExpiredError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": exc.code, "message": exc.message},
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _resolve_user_from_token(db, credentials.credentials, strict_session=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials or not credentials.credentials:
        return None
    return _resolve_user_from_token(db, credentials.credentials, strict_session=False)
