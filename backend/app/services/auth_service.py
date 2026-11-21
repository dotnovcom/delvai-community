import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import (
    assign_user_password,
    check_user_password,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User, UserPlatform, UserStatus
from app.models.user_session import UserSession
from app.schemas.auth import TokenResponse
from app.schemas.user import UserResponse
from app.services.email_verification_service import verify_code as verify_email_code
from app.services.sms_service import verify_code
try:
    from commercial.services.wechat_service import (
        build_wechat_oauth_authorize_url,
        code2session,
        oauth2_access_token,
    )
    from commercial.services.douyin_service import code2session as douyin_code2session
except ImportError:
    build_wechat_oauth_authorize_url = None
    code2session = None
    oauth2_access_token = None
    douyin_code2session = None
from app.services.integration_config import ai_mock_enabled, get_wechat_official_config

from app.services.session_service import revoke_user_sessions

logger = logging.getLogger(__name__)

QR_TICKET_PREFIX = "qrcode:ticket:"
QR_TICKET_EXPIRE = 300
WS_TICKET_PREFIX = "ws:ticket:"
WS_TICKET_EXPIRE = 60


def _build_token_response(user: User, db: Session, device_info: str | None = None) -> TokenResponse:
    from app.services.runtime_config import access_token_expire_minutes, refresh_token_expire_days

    revoke_user_sessions(db, user.id)

    refresh_token = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_token_expire_days(db))
    now = datetime.now(timezone.utc)

    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        device_info=device_info,
        expires_at=expires_at,
        last_active_at=now,
    )
    db.add(session)
    db.flush()

    access_token = create_access_token(
        user.id,
        expire_minutes=access_token_expire_minutes(db),
        session_id=session.id,
    )
    db.commit()
    db.refresh(user)

    from app.services.storage_service import present_file_url

    profile = UserResponse.model_validate(user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=profile.model_copy(update={"avatar": present_file_url(db, user.avatar)}),
    )


def _get_active_user(user: User | None) -> User:
    if not user:
        raise ValueError("用户不存在")
    if user.status == UserStatus.DISABLED:
        raise ValueError("账号已被禁用")
    return user


def _find_user_by_unionid(db: Session, unionid: str | None) -> User | None:
    if not unionid:
        return None
    return db.query(User).filter(User.unionid == unionid).first()


def _login_or_register_wechat_user(
    db: Session,
    openid: str,
    unionid: str | None,
    device_info: str,
) -> TokenResponse:
    user = _find_user_by_unionid(db, unionid)
    if not user:
        user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(
            openid=openid,
            unionid=unionid,
            nickname=f"微信用户{openid[-4:]}",
            platform=UserPlatform.WECHAT,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
    elif unionid and not user.unionid:
        user.unionid = unionid
    user = _get_active_user(user)
    return _build_token_response(user, db, device_info=device_info)


def _public_pc_base(db: Session) -> str:
    from app.services.runtime_config import get_str

    return get_str(db, "pc_site_url", "http://localhost:18080").rstrip("/")


def _wechat_qr_callback_uri(db: Session, public_base: str | None = None) -> str:
    base = (public_base or "").rstrip("/") or _public_pc_base(db)
    return f"{base}/api/v1/auth/wechat-oauth/qr-callback"


def _build_wechat_scan_url(db: Session, ticket: str, mode: str, public_base: str | None = None) -> str:
    """生成微信可识别的公众号网页授权地址（用微信扫码，而不是小程序协议）。"""
    state = f"{mode}:{ticket}"
    cfg = get_wechat_official_config(db)
    if cfg.get("app_id"):
        redirect_uri = _wechat_qr_callback_uri(db)
        return build_wechat_oauth_authorize_url(db, redirect_uri, state, scope="snsapi_userinfo")
    from app.core.config import settings

    if ai_mock_enabled(db) or settings.AI_MOCK_MODE:
        from urllib.parse import quote

        redirect_uri = _wechat_qr_callback_uri(db, public_base)
        return f"{redirect_uri}?code=mock_{ticket[:8]}&state={quote(state, safe='')}"
    raise ValueError("请在系统配置中填写公众号 AppID/AppSecret，PC 微信扫码登录使用公众号网页授权")


def _parse_qr_state(state: str) -> tuple[str, str]:
    raw = (state or "").strip()
    if ":" not in raw:
        raise ValueError("无效的扫码状态")
    mode, ticket = raw.split(":", 1)
    if mode not in {"login", "bind"} or not ticket:
        raise ValueError("无效的扫码状态")
    return mode, ticket


def qr_result_html(*, ok: bool, title: str, message: str) -> str:
    return _qr_result_html(ok=ok, title=title, message=message)


def _qr_result_html(*, ok: bool, title: str, message: str) -> str:
    from html import escape

    accent = "#10b981" if ok else "#ef4444"
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{escape(title)}</title>
<style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;background:#f3f4f6;color:#1f2937}}
.card{{width:min(420px,90vw);background:#fff;border-radius:24px;padding:40px 28px;text-align:center;
box-shadow:0 24px 64px rgba(15,23,42,.12)}}
h1{{margin:0 0 12px;font-size:22px;font-weight:500;color:{accent}}}
p{{margin:0;color:#6b7280;line-height:1.6}}
</style></head>
<body><div class="card"><h1>{escape(title)}</h1><p>{escape(message)}</p></div></body></html>"""


async def wechat_login(db: Session, code: str, ticket: str | None = None) -> TokenResponse:
    wx_data = await code2session(code, db)
    token_resp = _login_or_register_wechat_user(
        db, wx_data["openid"], wx_data.get("unionid"), "wechat",
    )
    if ticket:
        _confirm_qrcode_ticket(ticket, token_resp)
    return token_resp


async def wechat_oauth_login(db: Session, code: str) -> TokenResponse:
    wx_data = await oauth2_access_token(code, db)
    return _login_or_register_wechat_user(
        db, wx_data["openid"], wx_data.get("unionid"), "wechat_h5",
    )


async def douyin_login(db: Session, code: str) -> TokenResponse:
    dy_data = await douyin_code2session(code, db)
    openid = dy_data["openid"]
    storage_key = f"douyin:{openid}"

    user = db.query(User).filter(User.openid == storage_key).first()
    if not user:
        user = User(
            openid=storage_key,
            unionid=dy_data.get("unionid"),
            nickname=f"抖音用户{openid[-4:]}",
            platform=UserPlatform.DOUYIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()

    user = _get_active_user(user)
    return _build_token_response(user, db, device_info="douyin")


def _oauth_domain_host(raw: str) -> str:
    host = (raw or "").strip().lower()
    host = host.removeprefix("https://").removeprefix("http://")
    return host.split("/")[0].strip()


def wechat_h5_oauth_redirect_uri(oauth_domain: str, h5_site_url: str) -> str:
    """网页授权回调必须落在公众号后台配置的授权域名上。"""
    host = _oauth_domain_host(oauth_domain)
    if host:
        return f"https://{host}/api/v1/auth/wechat-oauth/h5-callback"
    base = (h5_site_url or "http://localhost:8081").strip().rstrip("/")
    return f"{base}/api/v1/auth/wechat-oauth/h5-callback"


def h5_login_redirect_target(h5_site_url: str, code: str, state: str) -> str:
    from urllib.parse import quote

    base = (h5_site_url or "http://localhost:8081").strip().rstrip("/")
    redirect = "/pages/chat/chat"
    try:
        payload = json.loads(state or "")
        raw = str(payload.get("redirect") or "") if isinstance(payload, dict) else ""
        if raw.startswith("/pages/") and "://" not in raw:
            redirect = raw
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return (
        f"{base}/#/pages/login/login"
        f"?code={quote(code or '', safe='')}"
        f"&redirect={quote(redirect, safe='')}"
    )


def get_wechat_oauth_authorize_url(db: Session, redirect_path: str) -> dict:
    from app.services.integration_config import get_wechat_official_config
    from app.services.runtime_config import get_str

    h5_base = get_str(db, "h5_site_url", "http://localhost:8081")
    oauth_domain = get_wechat_official_config(db).get("oauth_domain") or ""
    safe_path = redirect_path if redirect_path.startswith("/pages/") else "/pages/index/index"
    redirect_uri = wechat_h5_oauth_redirect_uri(oauth_domain, h5_base)
    state = json.dumps({"redirect": safe_path}, ensure_ascii=False)
    url = build_wechat_oauth_authorize_url(db, redirect_uri, state)
    return {"authorize_url": url, "state": state, "redirect_uri": redirect_uri}


def phone_login(
    db: Session,
    phone: str,
    login_type: str,
    code: str | None = None,
    password: str | None = None,
) -> TokenResponse:
    user = db.query(User).filter(User.phone == phone).first()
    if user and user.is_admin:
        raise ValueError("管理员请从管理后台登录")

    if login_type == "sms":
        if not verify_code(phone, code, "login", db):
            raise ValueError("验证码错误或已过期")
        if not user:
            user = User(
                phone=phone,
                nickname=f"用户{phone[-4:]}",
                platform=UserPlatform.PHONE,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
    else:
        if not user or not user.password_hash:
            raise ValueError("手机号或密码错误")
        if not check_user_password(user, password or ""):
            raise ValueError("手机号或密码错误")

    user = _get_active_user(user)
    return _build_token_response(user, db, device_info="phone")


def admin_login(db: Session, phone: str, password: str) -> TokenResponse:
    from datetime import datetime, timezone

    from sqlalchemy.exc import ProgrammingError, OperationalError

    from app.core.security import check_admin_password
    from app.models.admin_account import AdminAccount

    ident = (phone or "").strip()
    try:
        account = (
            db.query(AdminAccount)
            .filter((AdminAccount.phone == ident) | (AdminAccount.nickname == ident))
            .first()
        )
    except (ProgrammingError, OperationalError):
        logger.exception("admin_login query failed")
        db.rollback()
        raise ValueError("管理员数据表未就绪，请在服务器执行 alembic upgrade head")
    if not account or not check_admin_password(account, password):
        raise ValueError("账号或密码错误")
    if account.status != "active":
        raise ValueError("管理员账号已被禁用")
    user = db.query(User).filter(User.id == account.user_id).first()
    if not user:
        raise ValueError("管理员账号未关联用户")
    user = _get_active_user(user)
    user.is_admin = True
    user.admin_role = account.role or "viewer"
    account.last_login_at = datetime.now(timezone.utc)
    return _build_token_response(user, db, device_info="admin")


def email_login(
    db: Session,
    email: str,
    login_type: str,
    code: str | None = None,
    password: str | None = None,
) -> TokenResponse:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user and user.is_admin:
        raise ValueError("管理员请从管理后台登录")

    if login_type == "sms":
        if not verify_email_code(email, code, "login", db):
            raise ValueError("验证码错误或已过期")
        if not user:
            user = User(
                email=email,
                nickname=email.split("@")[0][:32] or "邮箱用户",
                platform=UserPlatform.WEB,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
    else:
        if not user or not user.password_hash:
            raise ValueError("邮箱或密码错误")
        if not check_user_password(user, password or ""):
            raise ValueError("邮箱或密码错误")

    user = _get_active_user(user)
    return _build_token_response(user, db, device_info="email")


def email_register(
    db: Session, email: str, password: str, code: str, invite_code: str | None = None
) -> TokenResponse:
    email = email.strip().lower()
    if not verify_email_code(email, code, "register", db):
        raise ValueError("验证码错误或已过期")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("该邮箱已注册")

    user = User(
        email=email,
        nickname=email.split("@")[0][:32] or "邮箱用户",
        platform=UserPlatform.WEB,
        status=UserStatus.ACTIVE,
    )
    assign_user_password(user, password)
    db.add(user)
    db.flush()
    _after_user_registered(db, user.id, invite_code)

    return _build_token_response(user, db, device_info="web")


def is_phone_registered(db: Session, phone: str) -> bool:
    return db.query(User).filter(User.phone == phone).first() is not None


def is_email_registered(db: Session, email: str) -> bool:
    normalized = (email or "").strip().lower()
    if not normalized:
        return False
    return db.query(User).filter(User.email == normalized).first() is not None


def register(
    db: Session, phone: str, password: str, code: str, invite_code: str | None = None
) -> TokenResponse:
    if not verify_code(phone, code, "register", db):
        raise ValueError("验证码错误或已过期")

    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        raise ValueError("该手机号已注册")

    user = User(
        phone=phone,
        nickname=f"用户{phone[-4:]}",
        platform=UserPlatform.WEB,
        status=UserStatus.ACTIVE,
    )
    assign_user_password(user, password)
    db.add(user)
    db.flush()
    _after_user_registered(db, user.id, invite_code)

    return _build_token_response(user, db, device_info="web")


def _after_user_registered(db: Session, user_id: int, invite_code: str | None) -> None:
    from commercial.services.checkin_service import grant_register_gift
    from commercial.services.referral_service import bind_referrer

    grant_register_gift(db, user_id)
    bind_referrer(db, user_id, invite_code)


def reset_password(db: Session, phone: str, code: str, new_password: str) -> dict:
    if not verify_code(phone, code, "reset_password", db):
        raise ValueError("验证码错误或已过期")
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise ValueError("该手机号未注册")
    if user.is_admin:
        raise ValueError("管理员请从管理后台修改密码")
    assign_user_password(user, new_password)
    revoke_user_sessions(db, user.id)
    db.commit()
    return {"message": "密码已重置"}


def change_password(db: Session, user: User, old_password: str, new_password: str) -> dict:
    if user.is_admin:
        raise ValueError("管理员请从管理后台修改密码")
    if not user.password_hash:
        raise ValueError("当前账号未设置密码，请使用找回密码功能")
    if not check_user_password(user, old_password):
        raise ValueError("原密码不正确")
    assign_user_password(user, new_password)
    revoke_user_sessions(db, user.id)
    db.commit()
    return {"message": "密码已修改"}


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def update_user_profile(db: Session, user: User, nickname: str | None, avatar: str | None) -> User:
    if nickname is not None:
        user.nickname = nickname
    if avatar is not None:
        user.avatar = avatar
    db.commit()
    db.refresh(user)
    return user


def create_qrcode_ticket(db: Session, public_base: str | None = None) -> dict:
    redis_client = get_redis()
    ticket = create_refresh_token()[:32]
    key = f"{QR_TICKET_PREFIX}{ticket}"
    redis_client.setex(
        key,
        QR_TICKET_EXPIRE,
        json.dumps({"status": "pending", "mode": "login"}),
    )
    return {
        "ticket": ticket,
        "expire_seconds": QR_TICKET_EXPIRE,
        "qrcode_url": _build_wechat_scan_url(db, ticket, "login", public_base),
    }


def get_qrcode_status(ticket: str) -> dict:
    redis_client = get_redis()
    key = f"{QR_TICKET_PREFIX}{ticket}"
    data = redis_client.get(key)

    if not data:
        return {"status": "expired"}

    return json.loads(data)


def create_ws_ticket(user_id: int) -> dict:
    """签发一次性 WebSocket 连接票据，避免在 URL 中传递 access_token。"""
    redis_client = get_redis()
    ticket = create_refresh_token()[:32]
    key = f"{WS_TICKET_PREFIX}{ticket}"
    redis_client.setex(key, WS_TICKET_EXPIRE, str(user_id))
    return {"ticket": ticket, "expire_seconds": WS_TICKET_EXPIRE}


def consume_ws_ticket(ticket: str) -> int | None:
    if not ticket or not str(ticket).strip():
        return None
    redis_client = get_redis()
    key = f"{WS_TICKET_PREFIX}{ticket.strip()}"
    raw = redis_client.get(key)
    if not raw:
        return None
    redis_client.delete(key)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _confirm_qrcode_ticket(ticket: str, token_resp: TokenResponse) -> None:
    redis_client = get_redis()
    key = f"{QR_TICKET_PREFIX}{ticket}"
    if not redis_client.exists(key):
        return

    redis_client.setex(
        key,
        60,
        json.dumps({
            "status": "confirmed",
            "access_token": token_resp.access_token,
            "refresh_token": token_resp.refresh_token,
            "user": token_resp.user.model_dump(mode="json"),
        }),
    )


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    session = (
        db.query(UserSession)
        .filter(UserSession.refresh_token == refresh_token)
        .first()
    )
    if not session:
        raise ValueError("无效的刷新令牌")
    if session.expires_at and session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise ValueError("刷新令牌已过期")

    user = get_user_by_id(db, session.user_id)
    if not user or user.status == UserStatus.DISABLED:
        raise ValueError("用户不可用")

    from app.services.session_service import SessionIdleExpiredError, enforce_admin_session_idle

    try:
        enforce_admin_session_idle(db, user, session)
    except SessionIdleExpiredError:
        raise

    db.delete(session)
    db.flush()
    return _build_token_response(user, db, device_info=session.device_info)


def logout(db: Session, refresh_token: str, user_id: int | None = None) -> None:
    q = db.query(UserSession).filter(UserSession.refresh_token == refresh_token)
    if user_id:
        q = q.filter(UserSession.user_id == user_id)
    session = q.first()
    if session:
        db.delete(session)
        db.commit()


def bind_phone(db: Session, user: User, phone: str, code: str) -> User:
    if user.phone == phone:
        raise ValueError("新手机号与当前手机号相同")
    if not verify_code(phone, code, "bind_phone", db):
        raise ValueError("验证码错误或已过期")
    existing = db.query(User).filter(User.phone == phone, User.id != user.id).first()
    if existing:
        raise ValueError("该手机号已被其他账号绑定")
    user.phone = phone
    db.commit()
    db.refresh(user)
    return user


def bind_email(db: Session, user: User, email: str, code: str) -> User:
    email = email.strip().lower()
    if user.email == email:
        raise ValueError("新邮箱与当前邮箱相同")
    if not verify_email_code(email, code, "bind_email", db):
        raise ValueError("验证码错误或已过期")
    existing = db.query(User).filter(User.email == email, User.id != user.id).first()
    if existing:
        raise ValueError("该邮箱已被其他账号绑定")
    user.email = email
    db.commit()
    db.refresh(user)
    return user


def reset_password_by_email(db: Session, email: str, code: str, new_password: str) -> dict:
    email = email.strip().lower()
    if not verify_email_code(email, code, "reset_password", db):
        raise ValueError("验证码错误或已过期")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("该邮箱未注册")
    if user.is_admin:
        raise ValueError("管理员请从管理后台修改密码")
    assign_user_password(user, new_password)
    revoke_user_sessions(db, user.id)
    db.commit()
    return {"message": "密码已重置"}


def create_bind_wechat_ticket(user_id: int, db: Session, public_base: str | None = None) -> dict:
    cfg = get_wechat_official_config(db)
    if not cfg.get("enabled", True) or not cfg.get("app_id") or not cfg.get("app_secret"):
        if not (ai_mock_enabled(db) or settings.AI_MOCK_MODE):
            raise ValueError("微信登录暂未配置完成，暂时无法绑定")
    redis_client = get_redis()
    ticket = create_refresh_token()[:32]
    key = f"{QR_TICKET_PREFIX}{ticket}"
    redis_client.setex(
        key,
        QR_TICKET_EXPIRE,
        json.dumps({"status": "pending", "mode": "bind", "user_id": user_id}),
    )
    return {
        "ticket": ticket,
        "expire_seconds": QR_TICKET_EXPIRE,
        "qrcode_url": _build_wechat_scan_url(db, ticket, "bind", public_base),
    }


def get_bind_wechat_status(ticket: str) -> dict:
    data = get_qrcode_status(ticket)
    if data.get("status") == "expired":
        return {"status": "expired"}
    if data.get("mode") != "bind":
        return {"status": "expired"}
    return {"status": data.get("status", "pending")}


def _confirm_wechat_bind_identity(db: Session, ticket: str, openid: str, unionid: str | None) -> dict:
    redis_client = get_redis()
    key = f"{QR_TICKET_PREFIX}{ticket}"
    raw = redis_client.get(key)
    if not raw:
        raise ValueError("绑定二维码已过期，请刷新后重试")
    data = json.loads(raw)
    if data.get("mode") != "bind":
        raise ValueError("无效的绑定请求")
    if data.get("status") == "confirmed":
        return {"message": "微信已绑定"}

    user_id = data.get("user_id")
    if not user_id:
        raise ValueError("绑定会话无效")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if user.openid:
        raise ValueError("当前账号已绑定微信")

    existing = db.query(User).filter(User.openid == openid, User.id != user.id).first()
    if existing:
        raise ValueError("该微信已被其他账号绑定")
    if unionid:
        existing_union = _find_user_by_unionid(db, unionid)
        if existing_union and existing_union.id != user.id:
            raise ValueError("该微信已被其他账号绑定")

    user.openid = openid
    if unionid:
        user.unionid = unionid
    db.commit()
    db.refresh(user)

    redis_client.setex(key, 60, json.dumps({"status": "confirmed", "mode": "bind", "user_id": user_id}))
    return {"message": "微信绑定成功"}


async def confirm_wechat_bind(db: Session, code: str, ticket: str) -> dict:
    wx_data = await oauth2_access_token(code, db)
    return _confirm_wechat_bind_identity(db, ticket, wx_data["openid"], wx_data.get("unionid"))


async def complete_wechat_qr_callback(db: Session, code: str, state: str) -> str:
    """微信扫码授权回调：登录或绑定 PC 端 ticket。"""
    if not code:
        return _qr_result_html(ok=False, title="授权失败", message="未获取到微信授权码，请返回电脑刷新二维码后重试")
    try:
        mode, ticket = _parse_qr_state(state)
    except ValueError:
        return _qr_result_html(ok=False, title="授权失败", message="扫码状态无效，请返回电脑刷新二维码")

    pending = get_qrcode_status(ticket)
    if pending.get("status") == "expired":
        return _qr_result_html(ok=False, title="二维码已过期", message="请返回电脑刷新二维码后重新扫码")

    try:
        wx_data = await oauth2_access_token(code, db)
        openid = wx_data["openid"]
        unionid = wx_data.get("unionid")
        if mode == "bind":
            _confirm_wechat_bind_identity(db, ticket, openid, unionid)
            return _qr_result_html(ok=True, title="绑定成功", message="微信已绑定，请返回电脑继续操作")
        token_resp = _login_or_register_wechat_user(db, openid, unionid, "wechat_scan")
        _confirm_qrcode_ticket(ticket, token_resp)
        return _qr_result_html(ok=True, title="登录成功", message="请返回电脑，页面将自动完成登录")
    except ValueError as exc:
        return _qr_result_html(ok=False, title="操作失败", message=str(exc))


