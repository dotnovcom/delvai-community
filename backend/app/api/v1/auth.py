import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AdminLoginRequest,
    EmailLoginRequest,
    EmailRegisterRequest,
    PhoneLoginRequest,
    QrcodeCreateResponse,
    QrcodeStatusResponse,
    RefreshTokenRequest,
    LogoutRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordEmailRequest,
    SendEmailRequest,
    SendSmsRequest,
    ChangePasswordRequest,
    TokenResponse,
    WechatLoginRequest,
    WechatBindRequest,
    DouyinLoginRequest,
    WechatOauthLoginRequest,
    WechatOauthAuthorizeResponse,
)
from app.schemas.user import UserResponse
from app.services import auth_service
from app.services import auth_policy
from app.services.session_service import SessionIdleExpiredError
from app.services.audit_service import log_action
from app.services.email_verification_service import send_verification_code as send_email_verification
from app.services.sms_service import SmsRateLimitError, send_verification_code

logger = logging.getLogger(__name__)

router = APIRouter()


def _request_public_base(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        return f"{proto}://{host}".rstrip("/")
    return ""


@router.post("/wechat-login", response_model=TokenResponse)
async def wechat_login(body: WechatLoginRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_wechat(db)
        return await auth_service.wechat_login(db, body.code, body.ticket)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/douyin-login", response_model=TokenResponse)
async def douyin_login(body: DouyinLoginRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_douyin(db)
        return await auth_service.douyin_login(db, body.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/wechat-oauth/authorize-url", response_model=WechatOauthAuthorizeResponse)
def wechat_oauth_authorize_url(
    redirect: str = Query("/pages/index/index", max_length=512),
    db: Session = Depends(get_db),
):
    try:
        auth_policy.require_login_wechat(db)
        return auth_service.get_wechat_oauth_authorize_url(db, redirect)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/wechat-oauth/login", response_model=TokenResponse)
async def wechat_oauth_login(body: WechatOauthLoginRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_wechat(db)
        return await auth_service.wechat_oauth_login(db, body.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/wechat-oauth/qr-callback", response_class=HTMLResponse)
async def wechat_qr_callback(
    db: Session = Depends(get_db),
    code: str = Query("", max_length=256),
    state: str = Query("", max_length=256),
):
    """微信扫码后的网页授权回调（公众号 OAuth），确认 PC 登录/绑定 ticket。"""
    try:
        auth_policy.require_login_wechat(db)
    except ValueError as e:
        return HTMLResponse(auth_service.qr_result_html(ok=False, title="未开放", message=str(e)))
    html = await auth_service.complete_wechat_qr_callback(db, code, state)
    return HTMLResponse(html)


@router.get("/wechat-oauth/h5-callback")
def wechat_h5_oauth_callback(
    db: Session = Depends(get_db),
    code: str = Query("", max_length=256),
    state: str = Query("", max_length=512),
):
    """公众号网页授权落在授权域名后，再跳回 H5 登录页完成登录。"""
    from app.services.runtime_config import get_str

    target = auth_service.h5_login_redirect_target(get_str(db, "h5_site_url"), code, state)
    return RedirectResponse(url=target, status_code=302)


@router.post("/phone-login", response_model=TokenResponse)
def phone_login(body: PhoneLoginRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_phone(db)
        if body.login_type == "sms":
            auth_policy.require_login_phone_sms(db)
        return auth_service.phone_login(
            db,
            phone=body.phone,
            login_type=body.login_type,
            code=body.code,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/admin-login", response_model=TokenResponse)
def admin_login(body: AdminLoginRequest, db: Session = Depends(get_db)):
    """平台管理员登录（独立帐密表，与前台用户分离）。"""
    if body.login_type != "password" or not body.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请使用密码登录")
    try:
        return auth_service.admin_login(db, phone=body.phone, password=body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/email-login", response_model=TokenResponse)
def email_login(body: EmailLoginRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_email(db)
        if body.login_type == "sms":
            auth_policy.require_login_email_sms(db)
        return auth_service.email_login(
            db,
            email=body.email,
            login_type=body.login_type,
            code=body.code,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/email-register", response_model=TokenResponse)
def email_register(body: EmailRegisterRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_register_email(db)
        return auth_service.email_register(db, body.email, body.password, body.code, body.invite_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_register_phone(db)
        return auth_service.register(db, body.phone, body.password, body.code, body.invite_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_phone(db)
        return auth_service.reset_password(db, body.phone, body.code, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reset-password-email")
def reset_password_email(body: ResetPasswordEmailRequest, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_email(db)
        return auth_service.reset_password_by_email(db, body.email, body.code, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wechat-bind")
async def wechat_bind(body: WechatBindRequest, db: Session = Depends(get_db)):
    try:
        return await auth_service.confirm_wechat_bind(db, body.code, body.ticket)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = auth_service.change_password(db, current_user, body.old_password, body.new_password)
        log_action(db, user_id=current_user.id, action="change_password", resource="auth")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/check-phone")
def check_phone(phone: str, db: Session = Depends(get_db)):
    try:
        auth_policy.require_register_phone(db)
        normalized = phone.strip()
        if not normalized or len(normalized) != 11 or not normalized.isdigit():
            raise ValueError("手机号格式不正确")
        return {"registered": auth_service.is_phone_registered(db, normalized)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    try:
        auth_policy.require_register_email(db)
        normalized = email.strip()
        if not normalized or "@" not in normalized:
            raise ValueError("邮箱格式不正确")
        return {"registered": auth_service.is_email_registered(db, normalized)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/send-sms")
def send_sms(
    body: SendSmsRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    try:
        if body.purpose == "register":
            auth_policy.require_register_phone(db)
            if auth_service.is_phone_registered(db, body.phone.strip()):
                raise ValueError("该手机号已注册")
        elif body.purpose == "bind_phone":
            if not current_user:
                raise HTTPException(status_code=401, detail="请先登录")
            phone = body.phone.strip()
            if current_user.phone and current_user.phone == phone:
                raise ValueError("新手机号与当前手机号相同")
            if auth_service.is_phone_registered(db, phone):
                raise ValueError("该手机号已被其他账号绑定")
        else:
            auth_policy.require_login_phone(db)
            if body.purpose == "login":
                auth_policy.require_login_phone_sms(db)
        return send_verification_code(body.phone, body.purpose, db=db)
    except SmsRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("send-sms failed phone=%s purpose=%s", body.phone, body.purpose)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"短信服务异常: {type(e).__name__}",
        ) from e


@router.post("/send-email")
def send_email(
    body: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    try:
        if body.purpose == "register":
            auth_policy.require_register_email(db)
            if auth_service.is_email_registered(db, body.email.strip()):
                raise ValueError("该邮箱已注册")
        elif body.purpose == "bind_email":
            if not current_user:
                raise HTTPException(status_code=401, detail="请先登录")
            email = body.email.strip().lower()
            if current_user.email and current_user.email.strip().lower() == email:
                raise ValueError("新邮箱与当前邮箱相同")
            if auth_service.is_email_registered(db, email):
                raise ValueError("该邮箱已被其他账号绑定")
        else:
            auth_policy.require_login_email(db)
            if body.purpose == "login":
                auth_policy.require_login_email_sms(db)
        return send_email_verification(body.email, body.purpose, db=db)
    except ValueError as e:
        message = str(e)
        code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "发送过于频繁" in message
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=message)


@router.post("/qrcode/create", response_model=QrcodeCreateResponse)
def create_qrcode(request: Request, db: Session = Depends(get_db)):
    try:
        auth_policy.require_login_wechat(db)
        return auth_service.create_qrcode_ticket(db, _request_public_base(request))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/qrcode/status/{ticket}", response_model=QrcodeStatusResponse)
def qrcode_status(ticket: str):
    data = auth_service.get_qrcode_status(ticket)
    user = None
    if data.get("user"):
        user = UserResponse(**data["user"])
    return QrcodeStatusResponse(
        status=data.get("status", "expired"),
        access_token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        user=user,
    )


@router.post("/ws-ticket")
def create_ws_ticket(current_user: User = Depends(get_current_user)):
    return auth_service.create_ws_ticket(current_user.id)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.refresh_access_token(db, body.refresh_token)
    except SessionIdleExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
def logout(
    body: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth_service.logout(db, body.refresh_token, current_user.id)
    log_action(db, user_id=current_user.id, action="logout", resource="auth")
    return {"message": "已退出登录"}
