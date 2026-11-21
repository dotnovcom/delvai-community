"""生产环境启动前安全校验。"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "changeme",
        "secret",
        "dev-secret-key-change-in-production",
    }
)


def validate_settings() -> None:
    """非 production 仅告警；production 配置不合规则拒绝启动。"""
    if settings.APP_ENV != "production":
        if settings.DEBUG and settings.APP_ENV == "staging":
            logger.warning("staging 环境 DEBUG=true，请确认是否为预期")
        return

    errors: list[str] = []

    if settings.DEBUG:
        errors.append("生产环境禁止 DEBUG=true")

    key = (settings.SECRET_KEY or "").strip()
    if key in WEAK_SECRET_KEYS or len(key) < 32:
        errors.append("生产环境 SECRET_KEY 须为至少 32 位的强随机字符串")

    if settings.ALLOW_PAYMENT_MOCK:
        errors.append("生产环境禁止 ALLOW_PAYMENT_MOCK=true")

    if settings.ALLOW_DEV_PAYMENT_CONFIRM:
        errors.append("生产环境禁止 ALLOW_DEV_PAYMENT_CONFIRM=true")

    if settings.ALLOW_PUBLIC_UPLOADS:
        errors.append("生产环境禁止 ALLOW_PUBLIC_UPLOADS=true")

    if settings.AI_MOCK_MODE:
        errors.append("生产环境禁止 AI_MOCK_MODE=true（请使用后台 ai_mock_enabled 或保持 false）")

    origins = settings.CORS_ORIGINS or []
    if not origins:
        errors.append("生产环境须配置 CORS_ORIGINS")
    elif any(o.strip() == "*" for o in origins):
        errors.append("生产环境 CORS_ORIGINS 禁止包含 *")

    if settings.ALLOW_ESIGN_CALLBACK_WITHOUT_SECRET and not settings.ESIGN_CALLBACK_SECRET:
        enc = (settings.ENCRYPTION_KEY or "").strip()
        if not enc or enc in WEAK_SECRET_KEYS:
            logger.warning("生产未配置 ENCRYPTION_KEY，敏感配置仍使用 SECRET_KEY 派生密钥")

    if errors:
        raise RuntimeError("生产环境配置校验失败: " + "; ".join(errors))

    logger.info("生产环境配置校验通过")
