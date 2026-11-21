"""从 system_settings 读取运行时配置，后台修改为唯一标准。"""

from sqlalchemy.orm import Session

from app.services import config_service

SECRET_CATEGORIES = {"sms", "email", "payment", "upload", "cache"}


def get_str(db: Session, key: str, default: str = "") -> str:
    return config_service.get_setting(db, key, default) or default


def get_int(db: Session, key: str, default: int = 0) -> int:
    val = config_service.get_setting(db, key)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def get_float(db: Session, key: str, default: float = 0.0) -> float:
    val = config_service.get_setting(db, key)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def get_bool(db: Session, key: str, default: bool = False) -> bool:
    return config_service.get_bool_setting(db, key, default)


def get_secret(db: Session, key: str, env_fallback: str | None = None) -> str | None:
    val = config_service.get_setting(db, key)
    if val:
        return config_service.decrypt_setting_value(val)
    return env_fallback


def access_token_expire_minutes(db: Session) -> int:
    return get_int(db, "access_token_expire_minutes", 60 * 24 * 7)


def refresh_token_expire_days(db: Session) -> int:
    return get_int(db, "refresh_token_expire_days", 30)


def admin_session_idle_minutes(db: Session) -> int:
    return get_int(db, "admin_session_idle_minutes", 30)


def resolve_admin_idle_minutes(db: Session) -> int:
    """管理员无操作登出分钟数。未配置或 0 时按 30 分钟。"""
    dedicated = admin_session_idle_minutes(db)
    return dedicated if dedicated > 0 else 30


def sms_code_expire_seconds(db: Session) -> int:
    return get_int(db, "sms_code_expire_seconds", 300)


def sms_rate_limit_seconds(db: Session) -> int:
    return get_int(db, "sms_rate_limit_seconds", 60)


def free_daily_chat_quota(db: Session) -> int:
    return get_int(db, "free_daily_chat_quota", 5)


def upload_max_size_bytes(db: Session) -> int:
    return get_int(db, "upload_max_size_mb", 10) * 1024 * 1024


def cache_default_ttl(db: Session) -> int:
    return get_int(db, "cache_default_ttl_seconds", 3600)
