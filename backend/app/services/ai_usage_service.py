"""AI Token 用量记录与成本估算。"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.quota import QUOTA_LABELS
from app.models.ai_usage_log import AiUsageLog
from app.models.conversation import InteractionType
from app.models.user import User
from app.services.runtime_config import get_float

logger = logging.getLogger(__name__)

ENGINE_LABELS: dict[str, str] = {
    "deepseek": "DeepSeek",
    "farui": "通义法睿",
    "qwen_vl": "Qwen-VL",
    "mimo_asr": "MiMo ASR",
    "mimo_tts": "MiMo TTS",
    "unknown": "未知",
}

EXTRA_SERVICE_LABELS: dict[str, str] = {
    "enterprise_compliance": "企业合规检查",
    "open_api_chat": "开放 API 对话",
}

DEFAULT_COST_PER_1K: dict[str, float] = {
    "deepseek": 0.002,
    "farui": 0.008,
    "qwen_vl": 0.01,
    "mimo_asr": 0.001,
}


def service_label_for(service_key: str, db: Session | None = None) -> str:
    if service_key in EXTRA_SERVICE_LABELS:
        return EXTRA_SERVICE_LABELS[service_key]
    if service_key in QUOTA_LABELS:
        return QUOTA_LABELS[service_key]
    if db is not None:
        from commercial.models.billing import BillingPrice

        row = db.query(BillingPrice).filter(BillingPrice.service_key == service_key).first()
        if row and row.label:
            return row.label
    return service_key


def chat_service_key(interaction_type: InteractionType | str) -> str:
    val = interaction_type.value if isinstance(interaction_type, InteractionType) else str(interaction_type)
    if val == InteractionType.VOICE.value:
        return "daily_voice"
    if val == InteractionType.VIDEO.value:
        return "monthly_video"
    return "daily_chat"


def get_cost_per_1k(db: Session, engine: str) -> Decimal:
    key = f"ai_cost_per_1k_tokens_{engine}"
    default = DEFAULT_COST_PER_1K.get(engine, DEFAULT_COST_PER_1K["deepseek"])
    rate = get_float(db, key, default)
    return Decimal(str(rate))


def estimate_cost(db: Session, engine: str, total_tokens: int) -> Decimal:
    if total_tokens <= 0:
        return Decimal("0")
    rate = get_cost_per_1k(db, engine or "deepseek")
    cost = (Decimal(total_tokens) / Decimal("1000")) * rate
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def log_ai_usage(
    db: Session,
    *,
    user_id: int,
    service_key: str,
    ai_engine: str,
    total_tokens: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    ref_type: str | None = None,
    ref_id: str | int | None = None,
    service_label: str | None = None,
) -> AiUsageLog | None:
    if total_tokens <= 0:
        return None
    try:
        row = AiUsageLog(
            user_id=user_id,
            service_key=service_key,
            service_label=service_label or service_label_for(service_key, db),
            ai_engine=ai_engine or "unknown",
            prompt_tokens=max(prompt_tokens, 0),
            completion_tokens=max(completion_tokens, 0),
            total_tokens=total_tokens,
            estimated_cost=estimate_cost(db, ai_engine or "deepseek", total_tokens),
            ref_type=ref_type,
            ref_id=str(ref_id) if ref_id is not None else None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        db.rollback()
        logger.warning("log_ai_usage failed: %s", exc)
        return None


def _parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        d = date.fromisoformat(value[:10])
    except ValueError:
        return None
    if end_of_day:
        return datetime.combine(d, time.max, tzinfo=timezone.utc)
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _apply_filters(
    q,
    *,
    user_id: int | None,
    service_key: str | None,
    ai_engine: str | None,
    keyword: str | None,
    date_from: str | None,
    date_to: str | None,
):
    if user_id:
        q = q.filter(AiUsageLog.user_id == user_id)
    if service_key:
        q = q.filter(AiUsageLog.service_key == service_key)
    if ai_engine:
        q = q.filter(AiUsageLog.ai_engine == ai_engine)
    start = _parse_date(date_from)
    end = _parse_date(date_to, end_of_day=True)
    if start:
        q = q.filter(AiUsageLog.created_at >= start)
    if end:
        q = q.filter(AiUsageLog.created_at <= end)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.join(User, User.id == AiUsageLog.user_id).filter(
            or_(User.phone.ilike(like), User.nickname.ilike(like))
        )
    return q


def _summary_for_query(db: Session, q) -> dict:
    total_tokens, total_cost, record_count = q.with_entities(
        func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
        func.coalesce(func.sum(AiUsageLog.estimated_cost), 0),
        func.count(AiUsageLog.id),
    ).one()
    user_count = q.with_entities(func.count(func.distinct(AiUsageLog.user_id))).scalar() or 0
    return {
        "total_tokens": int(total_tokens or 0),
        "total_cost": float(total_cost or 0),
        "record_count": int(record_count or 0),
        "user_count": int(user_count),
    }


def list_admin_ai_usage(
    db: Session,
    *,
    page: int = 1,
    size: int = 20,
    user_id: int | None = None,
    service_key: str | None = None,
    ai_engine: str | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    base = db.query(AiUsageLog)
    filtered = _apply_filters(
        base,
        user_id=user_id,
        service_key=service_key,
        ai_engine=ai_engine,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )
    summary = _summary_for_query(db, filtered)
    total = filtered.count()
    rows = (
        filtered.order_by(AiUsageLog.created_at.desc(), AiUsageLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    user_ids = {r.user_id for r in rows}
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            users[u.id] = u

    items = []
    for row in rows:
        u = users.get(row.user_id)
        items.append(
            {
                "id": row.id,
                "user_id": row.user_id,
                "user_phone": u.phone if u else None,
                "user_nickname": u.nickname if u else None,
                "service_key": row.service_key,
                "service_label": row.service_label or service_label_for(row.service_key, db),
                "ai_engine": row.ai_engine,
                "ai_engine_label": ENGINE_LABELS.get(row.ai_engine, row.ai_engine),
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens": row.total_tokens,
                "estimated_cost": float(row.estimated_cost or 0),
                "ref_type": row.ref_type,
                "ref_id": row.ref_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return {"total": total, "items": items, "summary": summary}


def list_admin_ai_usage_by_user(
    db: Session,
    *,
    page: int = 1,
    size: int = 20,
    user_id: int | None = None,
    service_key: str | None = None,
    ai_engine: str | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    base = db.query(AiUsageLog)
    filtered = _apply_filters(
        base,
        user_id=user_id,
        service_key=service_key,
        ai_engine=ai_engine,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )
    summary = _summary_for_query(db, filtered)

    grouped = filtered.with_entities(
        AiUsageLog.user_id,
        func.coalesce(func.sum(AiUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(AiUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(AiUsageLog.id).label("call_count"),
    ).group_by(AiUsageLog.user_id)

    total = grouped.count()
    rows = (
        grouped.order_by(func.sum(AiUsageLog.estimated_cost).desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    user_ids = [r.user_id for r in rows]
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            users[u.id] = u

    items = []
    for row in rows:
        u = users.get(row.user_id)
        items.append(
            {
                "user_id": row.user_id,
                "user_phone": u.phone if u else None,
                "user_nickname": u.nickname if u else None,
                "total_tokens": int(row.total_tokens or 0),
                "total_cost": float(row.total_cost or 0),
                "call_count": int(row.call_count or 0),
            }
        )
    return {"total": total, "items": items, "summary": summary}


def list_service_options(db: Session) -> list[dict]:
    keys = db.query(AiUsageLog.service_key, AiUsageLog.service_label).distinct().all()
    seen: set[str] = set()
    options: list[dict] = []
    for key, label in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        options.append({"service_key": key, "label": label or service_label_for(key, db)})
    options.sort(key=lambda x: x["label"])
    return options
