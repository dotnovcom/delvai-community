"""账号绑定策略：后台开关 + 未完成绑定时的 API 白名单"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.config_service import get_bool_setting

AUTH_REQUIRE_PHONE_BIND = "auth_require_phone_bind"
AUTH_REQUIRE_EMAIL_BIND = "auth_require_email_bind"

_BIND_WECHAT_STATUS_RE = re.compile(
    r"^/api/v1/users/me/bind-wechat/status/[^/]+$"
)


def require_phone_bind_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_REQUIRE_PHONE_BIND, False)


def require_email_bind_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_REQUIRE_EMAIL_BIND, False)


def _skip_binding_check(user: User) -> bool:
    return bool(getattr(user, "is_admin", False))


def get_binding_requirements(db: Session, user: User) -> dict[str, bool]:
    if _skip_binding_check(user):
        return {"binding_required_phone": False, "binding_required_email": False}
    phone = (user.phone or "").strip()
    email = (user.email or "").strip()
    return {
        "binding_required_phone": require_phone_bind_enabled(db) and not phone,
        "binding_required_email": require_email_bind_enabled(db) and not email,
    }


def is_binding_complete(db: Session, user: User) -> bool:
    req = get_binding_requirements(db, user)
    return not req["binding_required_phone"] and not req["binding_required_email"]


def get_missing_bindings(db: Session, user: User) -> list[str]:
    req = get_binding_requirements(db, user)
    missing: list[str] = []
    if req["binding_required_phone"]:
        missing.append("phone")
    if req["binding_required_email"]:
        missing.append("email")
    return missing


_BINDING_ALLOWED_EXACT: dict[str, frozenset[str]] = {
    "/api/v1/users/me": frozenset({"GET", "PUT"}),
    "/api/v1/users/me/bind-phone": frozenset({"POST"}),
    "/api/v1/users/me/bind-email": frozenset({"POST"}),
    "/api/v1/users/me/bind-wechat/ticket": frozenset({"POST"}),
}

_BINDING_EXEMPT_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/config/",
    "/api/v1/cms/",
    "/api/v1/admin/",
    "/api/v1/open/",
    "/uploads/",
    "/ws/",
)


def is_path_allowed_for_incomplete_binding(path: str, method: str) -> bool:
    if method.upper() == "OPTIONS":
        return True
    normalized = (path or "/").rstrip("/") or "/"
    for prefix in _BINDING_EXEMPT_PREFIXES:
        if normalized.startswith(prefix):
            return True
    allowed_methods = _BINDING_ALLOWED_EXACT.get(normalized)
    if allowed_methods and method.upper() in allowed_methods:
        return True
    if method.upper() == "GET" and _BIND_WECHAT_STATUS_RE.match(normalized):
        return True
    return False
