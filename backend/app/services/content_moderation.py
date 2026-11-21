"""内容安全审核（阿里云 Green；未配置 AK 时使用关键词拦截）。"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.services.runtime_config import get_bool, get_secret, get_str

logger = logging.getLogger(__name__)

_BLOCKED_WORDS = ("违禁测试词",)


def _keyword_block(text: str) -> tuple[bool, str]:
    if any(w in text for w in _BLOCKED_WORDS):
        return False, "内容包含违规信息"
    return True, ""


def _green_check_sync(db: Session, text: str) -> tuple[bool, str]:
    access_key = get_secret(db, "aliyun_green_access_key_id")
    access_secret = get_secret(db, "aliyun_green_access_key_secret")
    if not access_key or not access_secret:
        return _keyword_block(text)
    endpoint = get_str(db, "aliyun_green_endpoint") or "green-cip.cn-shanghai.aliyuncs.com"
    url = f"https://{endpoint}/text/scan"
    payload = {"scenes": ["antispam"], "tasks": [{"content": text[:6000]}]}
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)
        if resp.status_code >= 500:
            return _keyword_block(text)
        data = resp.json()
        for task in data.get("data", []):
            for result in task.get("results", []):
                if result.get("suggestion") == "block":
                    return False, result.get("label", "内容违规")
        return True, ""
    except Exception as exc:
        logger.warning("Green check failed: %s", exc)
        return _keyword_block(text)


def moderate_text(db: Session, text: str) -> tuple[bool, str]:
    """返回 (passed, reason)。未启用时默认通过。"""
    if not get_bool(db, "content_moderation_enabled", False):
        return True, ""
    if not text.strip():
        return True, ""
    return _green_check_sync(db, text)
