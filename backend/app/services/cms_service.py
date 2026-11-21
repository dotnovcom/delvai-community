from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.admin import ContentArticle, ContentStatus
from app.models.cms import LAUNCH_SPLASH_PLATFORMS, LaunchSplash, UserFeedback
from app.services.audit_service import log_action


def _refresh_splash_assets(db: Session, row: LaunchSplash) -> LaunchSplash:
    from app.services.storage_service import refresh_asset_url
    from app.utils.public_url import ensure_https_asset_url

    if row.media_url:
        row.media_url = ensure_https_asset_url(refresh_asset_url(db, row.media_url))
    return row


def list_launch_splash_admin(
    db: Session,
    page: int = 1,
    size: int = 20,
    platform: str | None = None,
    status: str | None = None,
) -> dict:
    q = db.query(LaunchSplash)
    if platform:
        q = q.filter(LaunchSplash.platform == platform)
    if status:
        q = q.filter(LaunchSplash.status == status)
    total = q.count()
    items = q.order_by(LaunchSplash.platform, LaunchSplash.sort_order, LaunchSplash.id.desc()).offset((page - 1) * size).limit(size).all()
    for row in items:
        _refresh_splash_assets(db, row)
    return {"total": total, "items": items}


def create_launch_splash(db: Session, data: dict, operator_id: int) -> LaunchSplash:
    row = LaunchSplash(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    log_action(db, user_id=operator_id, action="create_launch_splash", resource="launch_splash", resource_id=str(row.id))
    return _refresh_splash_assets(db, row)


def update_launch_splash(db: Session, splash_id: int, data: dict, operator_id: int) -> LaunchSplash:
    row = db.query(LaunchSplash).filter(LaunchSplash.id == splash_id).first()
    if not row:
        raise ValueError("启动引导不存在")
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    log_action(db, user_id=operator_id, action="update_launch_splash", resource="launch_splash", resource_id=str(splash_id))
    return _refresh_splash_assets(db, row)


def delete_launch_splash(db: Session, splash_id: int, operator_id: int) -> None:
    row = db.query(LaunchSplash).filter(LaunchSplash.id == splash_id).first()
    if row:
        db.delete(row)
        db.commit()
        log_action(db, user_id=operator_id, action="delete_launch_splash", resource="launch_splash", resource_id=str(splash_id))


def get_active_launch_splash(db: Session, platform: str) -> dict:
    from app.models.cms import LAUNCH_SPLASH_PLATFORMS

    if platform not in LAUNCH_SPLASH_PLATFORMS:
        return {"platform": platform, "version": "", "items": []}

    now = datetime.now(timezone.utc)
    rows = (
        db.query(LaunchSplash)
        .filter(
            LaunchSplash.platform == platform,
            LaunchSplash.enabled.is_(True),
            LaunchSplash.status == "active",
        )
        .order_by(LaunchSplash.sort_order, LaunchSplash.id)
        .all()
    )
    items = []
    version_ts = 0
    for row in rows:
        if row.start_at and row.start_at > now:
            continue
        if row.end_at and row.end_at < now:
            continue
        _refresh_splash_assets(db, row)
        if row.content_type in ("image", "video") and not row.media_url:
            continue
        if row.content_type == "html" and not (row.html_content or "").strip():
            continue
        items.append(row)
        if row.updated_at:
            version_ts = max(version_ts, int(row.updated_at.timestamp()))

    return {
        "platform": platform,
        "version": str(version_ts or 0),
        "items": items,
    }


def list_feedbacks_admin(
    db: Session,
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    keyword: str | None = None,
) -> dict:
    from app.models.user import User

    q = db.query(UserFeedback, User).outerjoin(User, UserFeedback.user_id == User.id)
    if status:
        q = q.filter(UserFeedback.status == status)
    if keyword:
        q = q.filter(
            (UserFeedback.content.ilike(f"%{keyword}%"))
            | (UserFeedback.contact.ilike(f"%{keyword}%"))
            | (User.phone.ilike(f"%{keyword}%"))
        )
    total = q.count()
    rows = q.order_by(UserFeedback.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "items": [
            {
                "id": fb.id,
                "user_id": fb.user_id,
                "user_phone": user.phone if user else None,
                "user_nickname": user.nickname if user else None,
                "category": fb.category,
                "content": fb.content,
                "contact": fb.contact,
                "status": fb.status,
                "admin_reply": fb.admin_reply,
                "replied_at": fb.replied_at,
                "created_at": fb.created_at,
            }
            for fb, user in rows
        ],
    }


_DEFAULT_SPLASH_HTML = """
<div style="min-height:100vh;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:72px 28px 120px;background:linear-gradient(180deg,#c4b5fd 0%,#2f78ff 36%,#4338ca 100%);color:#ffffff;">
  <div style="font-size:32px;font-weight:800;letter-spacing:0.04em;">得律AI</div>
  <div style="margin-top:14px;font-size:16px;opacity:0.92;">多模态法律智能服务平台</div>
  <div style="margin-top:12px;font-size:14px;letter-spacing:0.2em;opacity:0.8;">专业 · 智能 · 高效</div>
</div>
""".strip()


def seed_default_launch_splashes(db: Session) -> None:
    """把移动端现有品牌启动页写入各端引导配置，已有记录的平台不覆盖。"""
    existing = {
        row[0]
        for row in db.query(LaunchSplash.platform).distinct().all()
    }
    for platform in LAUNCH_SPLASH_PLATFORMS:
        if platform in existing:
            continue
        db.add(
            LaunchSplash(
                title="默认启动引导",
                platform=platform,
                enabled=True,
                content_type="html",
                html_content=_DEFAULT_SPLASH_HTML,
                duration_sec=0,
                allow_skip=False,
                sort_order=0,
                status="active",
            )
        )


def seed_cms_defaults(db: Session) -> None:
    """平台公告种子。已下线的法律资讯、指南、政策只在仍有数据时清一次。"""
    retired = ("legal_news", "guide", "policy")
    pending = (
        db.query(ContentArticle.id)
        .filter(ContentArticle.category.in_(retired))
        .limit(1)
        .first()
    )
    if pending:
        db.query(ContentArticle).filter(ContentArticle.category.in_(retired)).delete(synchronize_session=False)

    if db.query(ContentArticle).filter(ContentArticle.category == "announcement").count() == 0:
        announcements = [
            ContentArticle(
                title="得律AI平台正式上线",
                summary="多模态法律 AI 智能服务平台现已开放注册，欢迎体验。",
                content="<p>得律AI平台正式上线，提供 AI 法律咨询、法规检索、合同审查与文书生成等服务。</p>",
                category="announcement",
                status=ContentStatus.PUBLISHED.value,
                published_at=datetime.now(timezone.utc),
            ),
            ContentArticle(
                title="VIP 会员限时优惠活动",
                summary="升级 VIP 可解锁无限 AI 对话与高级法务工具。",
                content="<p>活动期间升级 VIP 会员享专属折扣，详情请查看会员中心。</p>",
                category="announcement",
                status=ContentStatus.PUBLISHED.value,
                published_at=datetime.now(timezone.utc),
            ),
        ]
        db.add_all(announcements)

    seed_default_launch_splashes(db)
    db.commit()


def list_published_articles(db: Session, page: int = 1, size: int = 10, category: str | None = None) -> dict:
    if category and category != "announcement":
        return {"total": 0, "items": []}
    q = db.query(ContentArticle).filter(
        ContentArticle.status == ContentStatus.PUBLISHED.value,
        ContentArticle.category == "announcement",
    )
    total = q.count()
    items = q.order_by(ContentArticle.published_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


def get_published_article(db: Session, article_id: int) -> ContentArticle | None:
    return (
        db.query(ContentArticle)
        .filter(
            ContentArticle.id == article_id,
            ContentArticle.status == ContentStatus.PUBLISHED.value,
            ContentArticle.category == "announcement",
        )
        .first()
    )


def create_feedback(db: Session, user_id: int | None, data: dict) -> UserFeedback:
    row = UserFeedback(user_id=user_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def reply_feedback(db: Session, feedback_id: int, reply: str, operator_id: int) -> UserFeedback:
    row = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if not row:
        raise ValueError("反馈不存在")
    row.admin_reply = reply
    row.replied_by = operator_id
    row.replied_at = datetime.now(timezone.utc)
    row.status = "replied"
    db.commit()
    db.refresh(row)
    log_action(
        db,
        user_id=operator_id,
        action="reply_feedback",
        resource="feedback",
        resource_id=str(feedback_id),
    )
    return row


def update_feedback_status(db: Session, feedback_id: int, status: str, operator_id: int) -> UserFeedback:
    row = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if not row:
        raise ValueError("反馈不存在")
    row.status = status
    db.commit()
    db.refresh(row)
    log_action(
        db,
        user_id=operator_id,
        action="update_feedback_status",
        resource="feedback",
        resource_id=str(feedback_id),
        detail={"status": status},
    )
    return row
