from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import BindEmailRequest, BindPhoneRequest
from app.schemas.notification import PaginatedNotificationsResponse, UnreadCountResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services import auth_service
from app.services import notification_service
from app.services import auth_binding
from app.services.audit_service import log_action

router = APIRouter()


def _user_response(db: Session, user: User) -> UserResponse:
    from app.services.storage_service import present_file_url

    base = UserResponse.model_validate(user)
    req = auth_binding.get_binding_requirements(db, user)
    return base.model_copy(update={**req, "avatar": present_file_url(db, user.avatar)})


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _user_response(db, current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = auth_service.update_user_profile(
        db, current_user, body.nickname, body.avatar
    )
    return _user_response(db, user)


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services import upload_service

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")
    from app.services.storage_service import present_file_url

    url = present_file_url(db, await upload_service.save_upload(db, file, subdir="avatars"))
    user = auth_service.update_user_profile(db, current_user, None, url)
    return {"url": url, "avatar": present_file_url(db, user.avatar)}


@router.post("/me/bind-phone", response_model=UserResponse)
def bind_phone(
    body: BindPhoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user = auth_service.bind_phone(db, current_user, body.phone, body.code)
        log_action(db, user_id=current_user.id, action="bind_phone", resource="user")
        return _user_response(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/me/bind-email", response_model=UserResponse)
def bind_email(
    body: BindEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user = auth_service.bind_email(db, current_user, body.email, body.code)
        log_action(db, user_id=current_user.id, action="bind_email", resource="user")
        return _user_response(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/me/bind-wechat/ticket")
def create_bind_wechat_ticket(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.openid:
        raise HTTPException(status_code=400, detail="已绑定微信")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    public_base = f"{proto}://{host}".rstrip("/") if host else None
    try:
        from app.services import auth_policy

        auth_policy.require_login_wechat(db)
        return auth_service.create_bind_wechat_ticket(current_user.id, db, public_base)
    except ValueError as exc:
        message = str(exc)
        if any(word in message for word in ("AppID", "AppSecret", "公众号", "未启用", "未开放", "配置")):
            message = "微信登录暂未配置完成，暂时无法绑定"
        raise HTTPException(status_code=400, detail=message) from exc
    except Exception as exc:
        from redis.exceptions import RedisError

        if isinstance(exc, RedisError):
            raise HTTPException(status_code=400, detail="绑定服务暂时不可用，请稍后重试") from exc
        raise


@router.get("/me/bind-wechat/status/{ticket}")
def bind_wechat_status(ticket: str, current_user: User = Depends(get_current_user)):
    return auth_service.get_bind_wechat_status(ticket)


@router.get("/me/notifications", response_model=PaginatedNotificationsResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    category: str | None = None,
    category_prefix: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.list_user_notifications(
        db,
        current_user.id,
        page=page,
        size=size,
        unread_only=unread_only,
        category=category,
        category_prefix=category_prefix,
    )


@router.get("/me/notifications/unread-count", response_model=UnreadCountResponse)
def unread_notification_count(
    category_prefix: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "count": notification_service.count_unread_notifications(
            db, current_user.id, category_prefix=category_prefix
        )
    }


@router.post("/me/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        notification_service.mark_notification_read(db, current_user.id, notification_id)
        return {"message": "已标记为已读"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/me/notifications/read-all")
def mark_all_notifications_read(
    category_prefix: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = notification_service.mark_all_notifications_read(
        db, current_user.id, category_prefix=category_prefix
    )
    return {"message": "已全部标记为已读", "count": count}
