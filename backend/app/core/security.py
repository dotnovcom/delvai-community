from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
import hashlib
import hmac
import os

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"

USER_PWD_ALGO = "pbkdf2_sha256"
USER_PWD_ITERATIONS = 310_000
USER_SALT_BYTES = 16

ADMIN_PWD_ALGO = "pbkdf2_sha512"
ADMIN_PWD_ITERATIONS = 210_000
ADMIN_SALT_BYTES = 32


def _is_bcrypt(stored: str) -> bool:
    return stored.startswith("$2a$") or stored.startswith("$2b$") or stored.startswith("$2y$")


def _pbkdf2(password: bytes, salt: bytes, iterations: int, hash_name: str) -> str:
    return hashlib.pbkdf2_hmac(hash_name, password, salt, iterations).hex()


def hash_user_password(password: str) -> tuple[str, str]:
    """前台用户：PBKDF2-HMAC-SHA256 + 独立盐值。返回 (password_hash, password_salt)。"""
    salt = os.urandom(USER_SALT_BYTES)
    digest = _pbkdf2(password.encode("utf-8"), salt, USER_PWD_ITERATIONS, "sha256")
    return f"{USER_PWD_ALGO}${USER_PWD_ITERATIONS}${digest}", salt.hex()


def verify_user_password(plain_password: str, password_hash: str, password_salt: str | None = None) -> bool:
    if not plain_password or not password_hash:
        return False
    if _is_bcrypt(password_hash):
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    parts = password_hash.split("$")
    if len(parts) != 3 or parts[0] != USER_PWD_ALGO or not password_salt:
        return False
    try:
        iterations = int(parts[1])
        expected = parts[2]
        salt = bytes.fromhex(password_salt)
    except (ValueError, TypeError):
        return False
    actual = _pbkdf2(plain_password.encode("utf-8"), salt, iterations, "sha256")
    return hmac.compare_digest(actual, expected)


def _admin_pepper() -> bytes:
    return hashlib.sha256(f"admin-pw|{settings.SECRET_KEY}".encode("utf-8")).digest()


def hash_admin_password(password: str) -> tuple[str, str]:
    """管理员：HMAC-SHA512(pepper) 后再 PBKDF2-HMAC-SHA512 + 更长盐值。"""
    salt = os.urandom(ADMIN_SALT_BYTES)
    material = hmac.new(_admin_pepper(), password.encode("utf-8"), hashlib.sha512).digest()
    digest = _pbkdf2(material, salt, ADMIN_PWD_ITERATIONS, "sha512")
    return f"{ADMIN_PWD_ALGO}${ADMIN_PWD_ITERATIONS}${digest}", salt.hex()


def verify_admin_password(plain_password: str, password_hash: str, password_salt: str | None = None) -> bool:
    if not plain_password or not password_hash:
        return False
    if _is_bcrypt(password_hash):
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    parts = password_hash.split("$")
    if len(parts) != 3 or parts[0] != ADMIN_PWD_ALGO or not password_salt:
        return False
    try:
        iterations = int(parts[1])
        expected = parts[2]
        salt = bytes.fromhex(password_salt)
    except (ValueError, TypeError):
        return False
    material = hmac.new(_admin_pepper(), plain_password.encode("utf-8"), hashlib.sha512).digest()
    actual = _pbkdf2(material, salt, iterations, "sha512")
    return hmac.compare_digest(actual, expected)


def assign_user_password(user: Any, password: str) -> None:
    digest, salt = hash_user_password(password)
    user.password_hash = digest
    user.password_salt = salt


def check_user_password(user: Any, password: str) -> bool:
    ok = verify_user_password(password, getattr(user, "password_hash", None) or "", getattr(user, "password_salt", None))
    if ok and user.password_hash and _is_bcrypt(user.password_hash):
        assign_user_password(user, password)
    return ok


def assign_admin_password(account: Any, password: str) -> None:
    digest, salt = hash_admin_password(password)
    account.password_hash = digest
    account.password_salt = salt


def check_admin_password(account: Any, password: str) -> bool:
    ok = verify_admin_password(
        password,
        getattr(account, "password_hash", None) or "",
        getattr(account, "password_salt", None),
    )
    if ok and account.password_hash and _is_bcrypt(account.password_hash):
        assign_admin_password(account, password)
    return ok


# 兼容旧测试与调用：默认按前台用户算法，hash 内嵌盐值
def hash_password(password: str) -> str:
    digest, salt = hash_user_password(password)
    return f"{digest}|{salt}"


def verify_password(plain_password: str, hashed_password: str, password_salt: str | None = None) -> bool:
    if not hashed_password:
        return False
    if _is_bcrypt(hashed_password):
        return verify_user_password(plain_password, hashed_password, password_salt)
    if password_salt:
        return verify_user_password(plain_password, hashed_password, password_salt)
    if "|" in hashed_password:
        digest, salt = hashed_password.rsplit("|", 1)
        return verify_user_password(plain_password, digest, salt)
    return verify_user_password(plain_password, hashed_password, password_salt)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    expire_minutes: int | None = None,
    session_id: int | None = None,
) -> str:
    if expires_delta is None and expire_minutes is not None:
        expires_delta = timedelta(minutes=expire_minutes)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
    if session_id is not None:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    return uuid4().hex + uuid4().hex


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def verify_access_token(token: str) -> str | None:
    payload = decode_access_token_payload(token)
    if not payload:
        return None
    return payload.get("sub")


def decode_access_token_payload(token: str) -> dict[str, Any] | None:
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
