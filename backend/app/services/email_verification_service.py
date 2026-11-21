import random
import string

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.services.email_service import EmailDeliveryError, send_email
from app.services.runtime_config import get_bool, get_int
from app.services import config_service

EMAIL_CODE_PREFIX = "email:code:"
EMAIL_RATE_PREFIX = "email:rate:"
EMAIL_FAIL_PREFIX = "email:fail:"

PURPOSE_LABEL = {
    "login": "登录验证码",
    "register": "注册验证码",
    "reset_password": "找回密码验证码",
    "bind_email": "绑定邮箱验证码",
}


def _email_subject(db: Session, purpose: str) -> str:
    brand = config_service.get_platform_name(db)
    label = PURPOSE_LABEL.get(purpose, "验证码")
    return f"{brand}{label}" if brand else label


def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _code_key(email: str, purpose: str) -> str:
    return f"{EMAIL_CODE_PREFIX}{purpose}:{email.lower()}"


def _fail_key(email: str, purpose: str) -> str:
    return f"{EMAIL_FAIL_PREFIX}{purpose}:{email.lower()}"


def _fail_limits(db: Session) -> tuple[int, int]:
    return (
        get_int(db, "email_code_max_failures", 5),
        get_int(db, "email_code_fail_window_seconds", 900),
    )


def send_verification_code(email: str, purpose: str = "login", db: Session | None = None) -> dict:
    if db is None:
        session = SessionLocal()
        try:
            return send_verification_code(email, purpose, session)
        finally:
            session.close()

    if not get_bool(db, "email_enabled", False):
        raise ValueError("邮件服务未启用，无法发送邮箱验证码")

    expire = get_int(db, "email_code_expire_seconds", 600)
    rate = get_int(db, "email_code_rate_limit_seconds", 60)

    redis_client = get_redis()
    rate_key = f"{EMAIL_RATE_PREFIX}{purpose}:{email.lower()}"
    if redis_client.exists(rate_key):
        ttl = redis_client.ttl(rate_key)
        raise ValueError(f"发送过于频繁，请 {ttl} 秒后重试")

    code = _generate_code()
    code_key = _code_key(email, purpose)
    redis_client.setex(code_key, expire, code)

    subject = _email_subject(db, purpose)
    body = f"您的验证码为 {code}，{expire // 60} 分钟内有效。如非本人操作请忽略。"
    try:
        send_email(db, email, subject, body)
    except EmailDeliveryError as exc:
        redis_client.delete(code_key)
        raise ValueError(str(exc)) from exc

    redis_client.setex(rate_key, rate, "1")
    return {"message": "验证码已发送", "expire_seconds": expire}


def verify_code(email: str, code: str, purpose: str = "login", db: Session | None = None) -> bool:
    if db is None:
        session = SessionLocal()
        try:
            return verify_code(email, code, purpose, session)
        finally:
            session.close()

    redis_client = get_redis()
    max_fail, fail_window = _fail_limits(db)
    normalized = email.lower()
    fail_key = _fail_key(normalized, purpose)
    fails = int(redis_client.get(fail_key) or 0)
    if fails >= max_fail:
        raise ValueError("验证失败次数过多，请稍后再试")

    code_key = _code_key(normalized, purpose)
    stored = redis_client.get(code_key)
    if not stored or stored != code:
        new_fails = redis_client.incr(fail_key)
        if new_fails == 1:
            redis_client.expire(fail_key, fail_window)
        if new_fails >= max_fail:
            raise ValueError("验证失败次数过多，请稍后再试")
        return False

    redis_client.delete(code_key)
    redis_client.delete(fail_key)
    return True
