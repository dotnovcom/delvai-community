"""本地文件访问签名（用于替代公开 /uploads 静态目录）。"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from urllib.parse import urlparse

from app.core.config import settings

PUBLIC_FOLDERS = frozenset({"avatars"})
AUTH_FOLDERS = frozenset({
    "chat",
    "files",
    "admin",
    "signed",
    "contracts",
    "contract-extract",
    "documents",
    "reports",
})
_LOCAL_FILE_PATH_RE = re.compile(
    r"(?:/api/v1)?/files/(?P<folder>avatars|chat|files|admin|signed|contracts|contract-extract|documents|reports)/(?P<filename>[a-zA-Z0-9._-]+)"
)


def sign_file_access(folder: str, filename: str, exp: int) -> str:
    msg = f"{folder}/{filename}:{exp}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_file_access(folder: str, filename: str, exp: int, sig: str | None) -> bool:
    if not sig or exp < int(time.time()):
        return False
    expected = sign_file_access(folder, filename, exp)
    return hmac.compare_digest(expected, sig)


def parse_local_file_ref(url: str) -> tuple[str, str] | None:
    """从完整签名 URL 或 `admin/xxx.png` 相对路径解析本地文件引用。"""
    u = (url or "").strip()
    if not u:
        return None
    bare = u.split("?", 1)[0]
    if "://" not in bare and "/" in bare and not bare.startswith("/"):
        folder, name = bare.split("/", 1)
        if folder in AUTH_FOLDERS | PUBLIC_FOLDERS and name:
            return folder, name
    path = urlparse(bare).path if "://" in bare else bare
    m = _LOCAL_FILE_PATH_RE.search(path)
    if not m:
        return None
    return m.group("folder"), m.group("filename")


def build_signed_file_url(
    folder: str,
    filename: str,
    *,
    public_base: str = "",
    expires_in: int | None = None,
) -> str:
    ttl = expires_in if expires_in is not None else settings.FILE_URL_EXPIRE_SECONDS
    exp = int(time.time()) + ttl
    sig = sign_file_access(folder, filename, exp)
    path = f"{settings.API_V1_PREFIX}/files/{folder}/{filename}?exp={exp}&sig={sig}"
    base = (public_base or "").rstrip("/")
    if base:
        return f"{base}{path}"
    return path


def refresh_signed_file_url(
    url: str,
    *,
    public_base: str = "",
    expires_in: int | None = None,
) -> str:
    """本地签名链接过期后，按 folder/filename 重新签发（OSS 等外链原样返回）。"""
    ref = parse_local_file_ref(url)
    if not ref:
        return url
    folder, filename = ref
    return build_signed_file_url(folder, filename, public_base=public_base, expires_in=expires_in)


def normalize_stored_file_ref(url: str) -> str:
    """持久化仅存 folder/filename，避免 DB 中签名过期。"""
    ref = parse_local_file_ref(url)
    if not ref:
        return url
    folder, filename = ref
    return f"{folder}/{filename}"
