"""社区版额度入口。装有商业包时使用完整扣费逻辑。"""

from __future__ import annotations

try:
    from commercial.quota_ext import (
        QUOTA_LABELS,
        UNLIMITED,
        QuotaCheckResult,
        _active_membership,
        _pack_contract_remaining,
        check_quota,
        consume_quota,
        get_usage_summary,
        period_key_for,
        preview_access,
        preview_feature_access,
        preview_quota_access,
        raise_quota_exceeded,
        rollback_quota,
    )
except ImportError:
    from dataclasses import dataclass
    from datetime import datetime, timezone

    from fastapi import HTTPException, status
    from sqlalchemy import func
    from sqlalchemy.orm import Session

    from app.models.usage_log import UsageLog
    from app.services.runtime_config import free_daily_chat_quota

    UNLIMITED = -1
    QUOTA_LABELS = {"daily_chat": "AI 文字咨询"}

    @dataclass
    class QuotaCheckResult:
        allowed: bool
        quota_key: str
        used: int
        limit: int
        remaining: int
        unlimited: bool
        period: str
        period_key: str
        message: str = ""
        suggest_level: str = ""
        consume_source: str = ""

    def period_key_for(quota_key: str, now: datetime | None = None) -> tuple[str, str]:
        now = now or datetime.now(timezone.utc)
        return "daily", now.strftime("%Y-%m-%d")

    def _active_membership(db: Session, user_id: int):
        return None, None

    def _pack_contract_remaining(membership) -> int:
        return 0

    def check_quota(db: Session, user_id: int, quota_key: str, amount: int = 1) -> QuotaCheckResult:
        if quota_key != "daily_chat":
            return QuotaCheckResult(
                False, quota_key, 0, 0, 0, False, "daily", "", message="社区版未提供该额度",
            )
        _, pkey = period_key_for(quota_key)
        limit = free_daily_chat_quota(db)
        used = (
            db.query(func.coalesce(func.sum(UsageLog.amount), 0))
            .filter(UsageLog.user_id == user_id, UsageLog.quota_key == quota_key, UsageLog.period_key == pkey)
            .scalar()
            or 0
        )
        used = int(used)
        remaining = max(limit - used, 0)
        return QuotaCheckResult(
            remaining >= amount, quota_key, used, limit, remaining, False, "daily", pkey,
        )

    def raise_quota_exceeded(check: QuotaCheckResult) -> None:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=check.message or "今日咨询次数已用完")

    def consume_quota(db: Session, user_id: int, quota_key: str, amount: int = 1) -> QuotaCheckResult:
        check = check_quota(db, user_id, quota_key, amount)
        if not check.allowed:
            raise_quota_exceeded(check)
        _, pkey = period_key_for(quota_key)
        db.add(UsageLog(user_id=user_id, quota_key=quota_key, amount=amount, period_key=pkey, source="community"))
        db.commit()
        check.used += amount
        check.remaining = max(check.limit - check.used, 0)
        check.consume_source = "community"
        return check

    def rollback_quota(db: Session, user_id: int, quota_key: str, amount: int = 1, *, consume_source: str = "") -> None:
        _, pkey = period_key_for(quota_key)
        db.add(UsageLog(user_id=user_id, quota_key=quota_key, amount=-amount, period_key=pkey, source="rollback"))
        db.commit()

    def preview_feature_access(db: Session, user_id: int, feature: str | None) -> tuple[bool, str]:
        if feature and feature != "chat":
            return False, "社区版未提供该功能"
        return True, ""

    def preview_quota_access(db: Session, user_id: int, quota_key: str, amount: int = 1) -> tuple[bool, str]:
        check = check_quota(db, user_id, quota_key, amount)
        return check.allowed, check.message

    def preview_access(db: Session, user_id: int, feature: str | None = None, quotas: list[str] | None = None) -> tuple[bool, str]:
        ok, message = preview_feature_access(db, user_id, feature)
        if not ok:
            return ok, message
        for key in quotas or []:
            ok, message = preview_quota_access(db, user_id, key)
            if not ok:
                return ok, message
        return True, ""

    def get_usage_summary(db: Session, user_id: int) -> dict:
        check = check_quota(db, user_id, "daily_chat")
        return {"daily_chat": {"used": check.used, "limit": check.limit, "remaining": check.remaining}}
