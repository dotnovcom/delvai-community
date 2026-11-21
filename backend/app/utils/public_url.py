"""公网 URL 规范化（生产环境统一 HTTPS，避免 Mixed Content）。"""

from __future__ import annotations


def _is_local_host(url: str) -> bool:
    lower = url.lower()
    return "localhost" in lower or "127.0.0.1" in lower


def normalize_public_base(url: str) -> str:
    """站点根地址：非本地 http 升级为 https。"""
    base = (url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.startswith("http://") and not _is_local_host(base):
        return "https://" + base[7:]
    return base


def ensure_https_asset_url(url: str) -> str:
    """图片/文件等绝对 URL。"""
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("http://") and not _is_local_host(u):
        return "https://" + u[7:]
    return u
