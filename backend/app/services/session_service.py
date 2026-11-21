"""单设备登录：access token 绑定 user_sessions.id，新登录踢掉旧会话。"""



from datetime import datetime, timedelta, timezone



from sqlalchemy.orm import Session



from app.models.user import User

from app.models.user_session import UserSession



SESSION_REPLACED_CODE = "SESSION_REPLACED"

SESSION_REPLACED_MESSAGE = (

    "您已经在其它设备登录，如不是您本人登录，请至用户中心及时更改密码。"

)



SESSION_IDLE_EXPIRED_CODE = "SESSION_IDLE_EXPIRED"

SESSION_IDLE_EXPIRED_MESSAGE = "登录已过期，请重新登录"





class SessionReplacedError(Exception):

    code = SESSION_REPLACED_CODE

    message = SESSION_REPLACED_MESSAGE





class SessionIdleExpiredError(Exception):

    code = SESSION_IDLE_EXPIRED_CODE

    message = SESSION_IDLE_EXPIRED_MESSAGE





def revoke_user_sessions(db: Session, user_id: int) -> None:

    db.query(UserSession).filter(UserSession.user_id == user_id).delete()

    db.flush()





def validate_user_session(db: Session, user_id: int, session_id: int | None) -> UserSession:

    if session_id is None:

        raise SessionReplacedError()

    session = (

        db.query(UserSession)

        .filter(UserSession.id == session_id, UserSession.user_id == user_id)

        .first()

    )

    if not session:

        raise SessionReplacedError()

    if session.expires_at and session.expires_at < datetime.now(timezone.utc):

        db.delete(session)

        db.commit()

        raise SessionReplacedError()

    return session





def enforce_admin_session_idle(db: Session, user: User, session: UserSession) -> None:

    """管理员会话：无操作超过配置时长则删除会话并拒绝（不刷新活跃时间）。"""

    if not user.is_admin:

        return

    from app.services.runtime_config import resolve_admin_idle_minutes



    idle_minutes = resolve_admin_idle_minutes(db)

    if idle_minutes <= 0:

        return



    now = datetime.now(timezone.utc)

    last = session.last_active_at or session.created_at

    if last.tzinfo is None:

        last = last.replace(tzinfo=timezone.utc)

    if now - last > timedelta(minutes=idle_minutes):

        db.delete(session)

        db.commit()

        raise SessionIdleExpiredError()





def touch_admin_session(db: Session, user: User, session: UserSession) -> None:

    """管理员会话：校验空闲超时后刷新最后活跃时间。"""

    enforce_admin_session_idle(db, user, session)

    if not user.is_admin:

        return

    session.last_active_at = datetime.now(timezone.utc)





def purge_stale_sessions(db: Session) -> int:

    """清理已过 refresh 有效期或管理员空闲超时的会话。"""

    from app.models.user import User

    from app.services.runtime_config import resolve_admin_idle_minutes



    now = datetime.now(timezone.utc)

    removed = 0



    for row in db.query(UserSession).filter(UserSession.expires_at < now).all():

        db.delete(row)

        removed += 1



    idle_minutes = resolve_admin_idle_minutes(db)

    if idle_minutes > 0:

        cutoff = now - timedelta(minutes=idle_minutes)

        admin_idle = (

            db.query(UserSession)

            .join(User, User.id == UserSession.user_id)

            .filter(User.is_admin.is_(True))

            .all()

        )

        for row in admin_idle:

            last = row.last_active_at or row.created_at

            if last.tzinfo is None:

                last = last.replace(tzinfo=timezone.utc)

            if last < cutoff:

                db.delete(row)

                removed += 1



    if removed:

        db.commit()

    return removed

