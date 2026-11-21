from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import assign_admin_password, assign_user_password
from app.models.admin import ContentArticle, ContentStatus, PushStatus, PushTask
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.audit_log import AuditLog
try:
    from commercial.models.enterprise import ContractLedger, ContractStatus, Enterprise
    from commercial.models.membership import MembershipStatus, Order, OrderStatus, UserMembership
except ImportError:
    ContractLedger = ContractStatus = Enterprise = None
    MembershipStatus = Order = OrderStatus = UserMembership = None
from app.models.admin_account import AdminAccount
from app.models.user import User, UserStatus
from app.services.audit_service import log_action


def _front_users_query(db: Session):
    """前台用户：排除 is_admin 以及 admin_accounts 挂载行。"""
    admin_ids = db.query(AdminAccount.user_id)
    return db.query(User).filter(User.is_admin.is_(False), ~User.id.in_(admin_ids))


def get_dashboard_stats(db: Session) -> dict:
    today = date.today()
    week_ago = today - timedelta(days=7)
    stats = {
        "user_total": _front_users_query(db).count(),
        "user_active": _front_users_query(db).filter(User.status == UserStatus.ACTIVE).count(),
        "user_new_week": _front_users_query(db).filter(func.date(User.created_at) >= week_ago).count(),
        "conversation_total": db.query(Conversation).count(),
        "enterprise_total": db.query(Enterprise).count() if Enterprise is not None else 0,
        "order_total": db.query(Order).count() if Order is not None else 0,
        "order_paid": db.query(Order).filter(Order.status == OrderStatus.PAID).count() if Order is not None else 0,
        "revenue_total": float(
            db.query(func.coalesce(func.sum(Order.amount), 0))
            .filter(Order.status == OrderStatus.PAID)
            .scalar() or 0
        ) if Order is not None else 0,
        "membership_active": db.query(UserMembership).filter(UserMembership.status == MembershipStatus.ACTIVE).count() if UserMembership is not None else 0,
    }
    if Enterprise is not None:
        from commercial.services.legal_cache import get_search_cache_stats

        stats.update(get_search_cache_stats(db))
    else:
        stats.update({
            "search_total_7d": 0,
            "search_es_hits_7d": 0,
            "search_farui_calls_7d": 0,
            "search_indexed_7d": 0,
            "search_es_hit_rate_7d": 0.0,
        })
    stats["ai_usage_7d"] = _ai_engine_usage_7d(db)
    return stats


def _ai_engine_usage_7d(db: Session) -> list[dict]:
    """近 7 日 AI 助手消息按引擎聚合（供管理端监控）。"""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        db.query(
            Message.ai_engine,
            func.count(Message.id),
            func.coalesce(func.sum(Message.tokens_used), 0),
        )
        .filter(
            Message.role == MessageRole.ASSISTANT,
            Message.created_at >= since,
            Message.ai_engine.isnot(None),
            Message.ai_engine != "",
        )
        .group_by(Message.ai_engine)
        .order_by(func.count(Message.id).desc())
        .all()
    )
    labels = {"farui": "通义法睿", "deepseek": "DeepSeek", "qwen_vl": "Qwen-VL"}
    return [
        {
            "engine": engine,
            "label": labels.get(engine, engine),
            "messages": int(count),
            "tokens": int(tokens or 0),
        }
        for engine, count, tokens in rows
    ]


def get_dashboard_charts(db: Session) -> dict:
    from app.core.member_levels import MemberLevel

    today = date.today()
    trend = []
    for offset in range(29, -1, -1):
        d = today - timedelta(days=offset)
        trend.append({
            "date": d.isoformat(),
            "users": _front_users_query(db).filter(func.date(User.created_at) == d).count(),
            "conversations": db.query(Conversation).filter(func.date(Conversation.created_at) == d).count(),
            "orders": db.query(Order).filter(func.date(Order.created_at) == d).count() if Order is not None else 0,
        })

    if UserMembership is None:
        vip = svip = 0
    else:
        vip = db.query(UserMembership).filter(
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.level == int(MemberLevel.VIP),
        ).count()
        svip = db.query(UserMembership).filter(
            UserMembership.status == MembershipStatus.ACTIVE,
            UserMembership.level == int(MemberLevel.SVIP),
        ).count()
    active_members = vip + svip
    user_total = _front_users_query(db).count()
    free = max(0, user_total - active_members)

    recent_orders = list_orders(db, page=1, size=5)["items"] if Order is not None else []
    return {
        "trend": trend,
        "membership_distribution": [
            {"name": "免费用户", "value": free},
            {"name": "VIP", "value": vip},
            {"name": "SVIP", "value": svip},
        ],
        "recent_orders": [
            {
                "order_no": o["order_no"],
                "plan_name": o["plan_name"],
                "amount": o["amount"],
                "status": o["status"],
                "user_phone": o.get("user_phone"),
                "created_at": o["created_at"],
            }
            for o in recent_orders
        ],
    }


def list_users(db: Session, page: int = 1, size: int = 20, keyword: str | None = None) -> dict:
    try:
        from commercial.services.membership_service import batch_user_membership_labels
        from commercial.services.wallet_service import batch_wallet_balances, points_display_name
    except ImportError:
        batch_user_membership_labels = None
        batch_wallet_balances = None
        points_display_name = None

    q = _front_users_query(db)
    if keyword:
        q = q.filter(
            (User.phone.ilike(f"%{keyword}%"))
            | (User.email.ilike(f"%{keyword}%"))
            | (User.nickname.ilike(f"%{keyword}%"))
        )
    total = q.count()
    items = q.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size).all()
    display = points_display_name(db) if points_display_name else "积分"
    user_ids = [u.id for u in items]
    vip_map = batch_user_membership_labels(db, user_ids) if batch_user_membership_labels else {}
    wallet_map = batch_wallet_balances(db, user_ids) if batch_wallet_balances else {}
    result_items = []
    for u in items:
        vip = vip_map.get(u.id, {})
        balance, points = wallet_map.get(u.id, (0.0, 0))
        result_items.append(
            {
                "id": u.id,
                "phone": u.phone,
                "email": u.email,
                "nickname": u.nickname,
                "platform": u.platform.value,
                "status": u.status.value,
                "is_admin": u.is_admin,
                "is_verified": bool(u.is_verified),
                "admin_role": u.admin_role,
                "created_at": u.created_at,
                "vip_label": vip.get("level_label") or vip.get("plan_name") or "免费版",
                "vip_expire_at": vip.get("expire_at"),
                "balance": balance,
                "points": points,
                "points_display_name": display,
            }
        )
    return {"total": total, "items": result_items}


def _enterprise_subscription_snapshot(db: Session, ent: Enterprise) -> dict:
    from commercial.models.enterprise import EnterpriseMember
    from commercial.models.membership import MembershipPlan
    from commercial.services.enterprise_subscription_service import enterprise_subscription_active, resolve_seat_limit

    plan_name = None
    if ent.plan_id:
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == ent.plan_id).first()
        plan_name = plan.name if plan else None
    member_count = db.query(EnterpriseMember).filter(EnterpriseMember.enterprise_id == ent.id).count()
    return {
        "plan_id": ent.plan_id,
        "plan_name": plan_name,
        "seat_limit": resolve_seat_limit(ent),
        "seats_used": member_count,
        "subscription_expires_at": ent.subscription_expires_at,
        "subscription_active": enterprise_subscription_active(ent),
        "is_trial": bool(getattr(ent, "is_trial", False)),
    }


def _order_meta_fields(order: Order) -> dict:
    meta = order.pay_meta or {}
    return {
        "payment_mode": meta.get("payment_mode"),
        "invoice_title": meta.get("invoice_title"),
        "tax_id": meta.get("tax_id"),
        "invoice_email": meta.get("invoice_email"),
        "invoice_status": meta.get("invoice_status"),
        "bank_reference": meta.get("bank_reference"),
    }


def list_orders(
    db: Session,
    page: int = 1,
    size: int = 20,
    status: str | None = None,
    keyword: str | None = None,
) -> dict:
    from commercial.models.membership import MembershipPlan
    from commercial.services.membership_service import order_payment_accounting

    q = (
        db.query(Order, User, MembershipPlan)
        .join(User, Order.user_id == User.id)
        .outerjoin(MembershipPlan, Order.plan_id == MembershipPlan.id)
    )
    if status:
        try:
            q = q.filter(Order.status == OrderStatus(status))
        except ValueError:
            pass
    if keyword:
        q = q.filter(
            (Order.order_no.ilike(f"%{keyword}%"))
            | (User.phone.ilike(f"%{keyword}%"))
            | (User.nickname.ilike(f"%{keyword}%"))
        )
    total = q.count()
    rows = q.order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "items": [
            {
                "order_no": order.order_no,
                "status": order.status.value,
                "amount": order.amount,
                "platform": order.platform.value,
                **order_payment_accounting(db, order),
                "plan_name": plan.name if plan else ((order.pay_meta or {}).get("package_name") or "余额充值"),
                "order_type": getattr(order, "order_type", None) or "membership",
                "user_id": user.id,
                "user_phone": user.phone,
                "user_nickname": user.nickname,
                "paid_at": order.paid_at,
                "created_at": order.created_at,
                **_order_meta_fields(order),
            }
            for order, user, plan in rows
        ],
    }


def update_order_status(
    db: Session,
    order_no: str,
    status: str | None,
    operator_id: int,
    *,
    invoice_status: str | None = None,
    bank_reference: str | None = None,
) -> dict:
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise ValueError("订单不存在")

    meta_changed = False
    if invoice_status or bank_reference is not None:
        meta = dict(order.pay_meta or {})
        if invoice_status:
            meta["invoice_status"] = invoice_status
            meta_changed = True
        if bank_reference is not None:
            meta["bank_reference"] = bank_reference.strip() if bank_reference else None
            meta_changed = True
        if meta_changed:
            order.pay_meta = meta
            db.commit()
            log_action(
                db,
                user_id=operator_id,
                action="admin_update_order_meta",
                resource="order",
                resource_id=order_no,
                detail={"invoice_status": invoice_status, "bank_reference": bank_reference},
            )

    if not status:
        return {"order_no": order_no, "status": order.status.value, **_order_meta_fields(order)}

    if order.status not in (OrderStatus.PAID, OrderStatus.PENDING):
        raise ValueError("当前状态不可变更")
    try:
        new_status = OrderStatus(status)
    except ValueError:
        raise ValueError("无效状态")
    if new_status not in (OrderStatus.CANCELLED, OrderStatus.REFUNDED, OrderStatus.PAID):
        raise ValueError("无效的目标状态")
    if order.status == OrderStatus.PENDING and new_status == OrderStatus.REFUNDED:
        raise ValueError("待支付订单不可退款，请先取消")
    if new_status == OrderStatus.PAID:
        if order.status != OrderStatus.PENDING:
            raise ValueError("仅待支付订单可标记为已支付")
        from commercial.services.membership_service import admin_confirm_order_paid

        if not admin_confirm_order_paid(db, order, operator_id):
            raise ValueError("标记支付失败")
        log_action(
            db,
            user_id=operator_id,
            action="admin_update_order",
            resource="order",
            resource_id=order_no,
            detail={"status": status, "manual_paid": True},
        )
        return {"order_no": order_no, "status": OrderStatus.PAID.value}
    if new_status == OrderStatus.REFUNDED:
        if order.status != OrderStatus.PAID:
            raise ValueError("仅已支付订单可退款")
        from commercial.services.membership_service import process_order_refund

        process_order_refund(db, order)
    elif new_status == OrderStatus.CANCELLED and order.status == OrderStatus.PENDING:
        from commercial.services.membership_service import _release_order_wallet_holds

        _release_order_wallet_holds(db, order)
    order.status = new_status
    db.commit()
    log_action(
        db,
        user_id=operator_id,
        action="admin_update_order",
        resource="order",
        resource_id=order_no,
        detail={"status": status},
    )
    return {"order_no": order_no, "status": order.status.value}


def delete_order_admin(db: Session, order_no: str, operator_id: int) -> None:
    from commercial.models.billing import ReferralPendingReward
    from commercial.models.membership import Payment, PaymentStatus

    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise ValueError("订单不存在")
    if order.status not in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        raise ValueError("仅已取消或已退款订单可删除")

    db.query(ReferralPendingReward).filter(ReferralPendingReward.order_id == order.id).delete(
        synchronize_session=False
    )
    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if payment:
        db.delete(payment)
    db.delete(order)
    db.commit()
    log_action(
        db,
        user_id=operator_id,
        action="admin_delete_order",
        resource="order",
        resource_id=order_no,
    )


def update_user(
    db: Session,
    user_id: int,
    data: dict,
    operator_id: int | None = None,
    *,
    operator: User | None = None,
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")

    operator_role = (operator.admin_role if operator else None) or "viewer"
    is_super = operator_role == "super_admin"
    if ("is_admin" in data or "admin_role" in data) and not is_super:
        raise ValueError("仅超级管理员可修改管理员权限")

    changes = {}
    if "status" in data and data["status"]:
        user.status = UserStatus(data["status"])
        changes["status"] = data["status"]
    if "nickname" in data:
        user.nickname = data["nickname"]
        changes["nickname"] = data["nickname"]
    if "phone" in data:
        phone = (data["phone"] or "").strip() or None
        if phone and not phone.isdigit():
            raise ValueError("手机号格式不正确")
        if phone and (len(phone) != 11 or not phone.startswith("1")):
            raise ValueError("请输入 11 位手机号")
        if phone:
            dup = db.query(User).filter(User.phone == phone, User.id != user_id).first()
            if dup:
                raise ValueError("手机号已被其他账号使用")
        user.phone = phone
        changes["phone"] = phone
    if "email" in data:
        email = (data["email"] or "").strip().lower() or None
        if email and "@" not in email:
            raise ValueError("邮箱格式不正确")
        if email:
            dup = db.query(User).filter(User.email == email, User.id != user_id).first()
            if dup:
                raise ValueError("邮箱已被其他账号使用")
        user.email = email
        changes["email"] = email
    if "is_verified" in data and data["is_verified"] is not None:
        user.is_verified = bool(data["is_verified"])
        changes["is_verified"] = user.is_verified
    if "is_admin" in data:
        user.is_admin = data["is_admin"]
        changes["is_admin"] = data["is_admin"]
    if "admin_role" in data:
        user.admin_role = data["admin_role"]
        changes["admin_role"] = data["admin_role"]
    _sync_admin_account(db, user)
    db.commit()
    db.refresh(user)
    if changes and operator_id:
        log_action(
            db,
            user_id=operator_id,
            action="update_user",
            resource="user",
            resource_id=str(user_id),
            detail=changes,
        )
    return user


def reset_user_password(
    db: Session,
    user_id: int,
    new_password: str,
    operator_id: int | None = None,
) -> User:
    """重置前台用户登录密码，并踢掉已有会话。不记录明文密码。"""
    from app.services.session_service import revoke_user_sessions

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if user.is_admin:
        raise ValueError("管理员请在个人设置中修改密码")
    assign_user_password(user, new_password)
    revoke_user_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    if operator_id:
        log_action(
            db,
            user_id=operator_id,
            action="reset_user_password",
            resource="user",
            resource_id=str(user_id),
            detail={"password_reset": True},
        )
    return user


def list_articles(db: Session, page: int = 1, size: int = 20, status: str | None = None, category: str | None = None, exclude_category: str | None = None) -> dict:
    q = db.query(ContentArticle)
    if status:
        q = q.filter(ContentArticle.status == status)
    if category:
        q = q.filter(ContentArticle.category == category)
    if exclude_category:
        q = q.filter(ContentArticle.category != exclude_category)
    total = q.count()
    items = q.order_by(ContentArticle.updated_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


def create_article(db: Session, author_id: int, data: dict) -> ContentArticle:
    from app.utils.sanitize_html import sanitize_html

    article = ContentArticle(
        title=data["title"],
        summary=data.get("summary"),
        content=sanitize_html(data["content"]),
        category="announcement",
        cover_url=data.get("cover_url"),
        status=data.get("status", ContentStatus.DRAFT.value),
        author_id=author_id,
    )
    if article.status == ContentStatus.PUBLISHED.value:
        article.published_at = datetime.now(timezone.utc)
    db.add(article)
    db.commit()
    db.refresh(article)
    log_action(
        db,
        user_id=author_id,
        action="create_content",
        resource="content",
        resource_id=str(article.id),
        detail={"title": article.title},
    )
    return article


def update_article(db: Session, article_id: int, data: dict, operator_id: int | None = None) -> ContentArticle:
    article = db.query(ContentArticle).filter(ContentArticle.id == article_id).first()
    if not article:
        raise ValueError("文章不存在")
    from app.utils.sanitize_html import sanitize_html

    if "category" in data:
        data["category"] = "announcement"
    for k in ("title", "summary", "content", "category", "cover_url", "status"):
        if k in data and data[k] is not None:
            value = sanitize_html(data[k]) if k == "content" else data[k]
            setattr(article, k, value)
    if data.get("status") == ContentStatus.PUBLISHED.value and not article.published_at:
        article.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    if operator_id:
        log_action(
            db,
            user_id=operator_id,
            action="update_content",
            resource="content",
            resource_id=str(article_id),
            detail={"title": article.title},
        )
    return article


def delete_article(db: Session, article_id: int, operator_id: int | None = None) -> None:
    article = db.query(ContentArticle).filter(ContentArticle.id == article_id).first()
    if article:
        title = article.title
        db.delete(article)
        db.commit()
        if operator_id:
            log_action(
                db,
                user_id=operator_id,
                action="delete_content",
                resource="content",
                resource_id=str(article_id),
                detail={"title": title},
            )


def get_user_detail(db: Session, user_id: int) -> dict:
    try:
        from commercial.models.membership import MembershipPlan
        from commercial.services.membership_service import get_user_membership_info
        from commercial.services.wallet_service import (
            get_wallet_summary,
            list_points_ledger,
            list_wallet_transactions,
        )
    except ImportError:
        MembershipPlan = None
        get_user_membership_info = None
        get_wallet_summary = None
        list_points_ledger = None
        list_wallet_transactions = None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")

    conv_count = db.query(Conversation).filter(Conversation.user_id == user_id).count()
    msg_count = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id)
        .count()
    )

    if MembershipPlan is None or UserMembership is None or Order is None:
        membership_rows = []
        order_rows = []
    else:
        membership_rows = (
            db.query(UserMembership, MembershipPlan)
            .join(MembershipPlan, UserMembership.plan_id == MembershipPlan.id)
            .filter(UserMembership.user_id == user_id)
            .order_by(UserMembership.created_at.desc())
            .limit(10)
            .all()
        )
        order_rows = (
            db.query(Order, MembershipPlan)
            .join(MembershipPlan, Order.plan_id == MembershipPlan.id)
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )

    if get_user_membership_info is None:
        vip = {}
        wallet = {}
        wallet_tx = {"items": []}
        points_tx = {"items": []}
    else:
        vip = get_user_membership_info(db, user_id)
        wallet = get_wallet_summary(db, user_id)
        wallet_tx = list_wallet_transactions(db, user_id, page=1, size=20)
        points_tx = list_points_ledger(db, user_id, page=1, size=20)

    return {
        "id": user.id,
        "phone": user.phone,
        "email": user.email,
        "is_verified": bool(user.is_verified),
        "nickname": user.nickname,
        "platform": user.platform.value,
        "status": user.status.value,
        "is_admin": user.is_admin,
        "admin_role": user.admin_role,
        "created_at": user.created_at,
        "conversation_count": conv_count,
        "message_count": msg_count,
        "vip_label": vip.get("level_label") or vip.get("plan_name"),
        "vip_expire_at": vip.get("expire_at"),
        "wallet": wallet,
        "memberships": [
            {
                "plan_name": plan.name,
                "level": m.level,
                "status": m.status.value,
                "start_at": m.start_at,
                "expire_at": m.expire_at,
            }
            for m, plan in membership_rows
        ],
        "orders": [
            {
                "order_no": order.order_no,
                "plan_name": plan.name,
                "amount": order.amount,
                "status": order.status.value,
                "created_at": order.created_at,
            }
            for order, plan in order_rows
        ],
        "wallet_transactions": wallet_tx["items"],
        "points_ledger": points_tx["items"],
    }


def _audit_labels() -> tuple[dict[str, str], dict[str, str]]:
    actions = {
        "update_user": "修改了用户资料",
        "reset_user_password": "重置了用户密码",
        "admin_update_order": "更新了订单",
        "admin_update_order_meta": "修改了订单备注",
        "admin_delete_order": "删除了订单",
        "admin_set_membership": "调整了用户会员",
        "admin_extend_membership": "延长了会员期限",
        "admin_cancel_membership": "取消了用户会员",
        "create_content": "发布了内容",
        "update_content": "更新了内容",
        "delete_content": "删除了内容",
        "update_settings": "保存了系统配置",
        "update_role_permissions": "更新了角色权限",
        "sync_legal_pages_defaults": "同步了协议默认正文",
        "create_plan": "新建了会员套餐",
        "update_plan": "修改了会员套餐",
        "delete_plan": "删除了会员套餐",
        "delete_audit_log": "删除了操作日志",
        "create_launch_splash": "新建了启动闪屏",
        "update_launch_splash": "修改了启动闪屏",
        "delete_launch_splash": "删除了启动闪屏",
        "reply_feedback": "回复了用户反馈",
        "update_feedback_status": "更新了反馈状态",
        "create_open_api_key": "创建了开放 API 密钥",
        "update_open_api_key": "修改了开放 API 密钥",
        "delete_open_api_key": "删除了开放 API 密钥",
        "create_enterprise": "创建了企业",
        "update_enterprise": "修改了企业",
        "delete_enterprise": "删除了企业",
        "add_enterprise_member": "添加了企业成员",
        "update_enterprise_member": "修改了企业成员",
        "remove_enterprise_member": "移除了企业成员",
        "update_enterprise_config": "修改了企业配置",
        "delete_enterprise_record": "删除了企业记录",
        "create_lawyer": "新建了律师",
        "update_lawyer": "修改了律师",
        "deactivate_lawyer": "停用了律师",
        "create_document_template": "新建了文书模板",
        "update_document_template": "修改了文书模板",
        "delete_document_template": "删除了文书模板",
        "sync_document_template_catalog": "同步了文书模板目录",
        "admin_wallet_adjust": "调整了用户钱包",
        "update_conversation": "修改了咨询会话",
        "delete_conversation": "删除了咨询会话",
        "change_password": "修改了登录密码",
        "update_ai_provider": "修改了 AI 服务配置",
        "create_lawyer_consultation": "新建了律师咨询",
        "update_lawyer_consultation": "修改了律师咨询",
        "delete_lawyer_consultation": "删除了律师咨询",
        "dev_confirm_payment": "模拟确认了支付",
    }
    resources = {
        "user": "用户",
        "order": "订单",
        "content": "内容",
        "plan": "套餐",
        "membership_plan": "会员套餐",
        "settings": "系统配置",
        "system_settings": "系统配置",
        "ai": "AI 配置",
        "ai_provider": "AI 服务",
        "banner": "轮播",
        "launch_splash": "启动闪屏",
        "open_api_key": "开放 API 密钥",
        "enterprise": "企业",
        "lawyer": "律师",
        "document_template": "文书模板",
        "conversation": "咨询会话",
        "auth": "登录账号",
        "user_membership": "会员",
    }
    return actions, resources


def list_audit_logs(
    db: Session,
    page: int = 1,
    size: int = 20,
    keyword: str | None = None,
    action: str | None = None,
    resource: str | None = None,
) -> dict:
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource:
        q = q.filter(AuditLog.resource == resource)
    if keyword:
        q = q.filter(
            (AuditLog.action.ilike(f"%{keyword}%"))
            | (AuditLog.resource.ilike(f"%{keyword}%"))
            | (AuditLog.resource_id.ilike(f"%{keyword}%"))
        )
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size).all()
    actions, resources = _audit_labels()
    user_ids = {log.user_id for log in items if log.user_id}
    names: dict[int, str] = {}
    if user_ids:
        for user in db.query(User).filter(User.id.in_(user_ids)).all():
            names[user.id] = (user.nickname or user.phone or f"用户{user.id}").strip()
    rows = []
    for log in items:
        operator = names.get(log.user_id or 0) or "系统"
        action_label = actions.get(log.action, log.action.replace("_", " "))
        resource_label = resources.get(log.resource, log.resource)
        target = f"（编号 {log.resource_id}）" if log.resource_id else ""
        summary = f"{operator}{action_label}{resource_label}{target}"
        rows.append(
            {
                "id": log.id,
                "user_id": log.user_id,
                "operator_name": operator,
                "action": log.action,
                "action_label": action_label,
                "resource": log.resource,
                "resource_label": resource_label,
                "resource_id": log.resource_id,
                "summary": summary,
                "detail": log.detail,
                "ip": log.ip,
                "created_at": log.created_at,
            }
        )
    return {"total": total, "items": rows}


def delete_audit_logs(db: Session, ids: list[int], operator_id: int) -> int:
    unique_ids = sorted({int(i) for i in ids if i})
    if not unique_ids:
        return 0
    deleted = (
        db.query(AuditLog)
        .filter(AuditLog.id.in_(unique_ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted:
        log_action(
            db,
            user_id=operator_id,
            action="delete_audit_log",
            resource="audit_log",
            detail={"ids": unique_ids, "deleted": deleted},
        )
    return int(deleted or 0)


def list_conversations(
    db: Session,
    page: int = 1,
    size: int = 20,
    keyword: str | None = None,
    user_id: int | None = None,
    interaction_type: str | None = None,
    interaction_types: str | None = None,
) -> dict:
    from app.models.conversation import ConversationStatus

    q = db.query(Conversation, User).join(User, Conversation.user_id == User.id)
    q = q.filter(Conversation.status != ConversationStatus.DELETED)
    if user_id:
        q = q.filter(Conversation.user_id == user_id)
    if interaction_type:
        from app.models.conversation import InteractionType

        q = q.filter(Conversation.interaction_type == InteractionType(interaction_type))
    elif interaction_types:
        from app.models.conversation import InteractionType

        types = [InteractionType(t.strip()) for t in interaction_types.split(",") if t.strip()]
        if types:
            q = q.filter(Conversation.interaction_type.in_(types))
    if keyword:
        q = q.filter(
            (Conversation.title.ilike(f"%{keyword}%"))
            | (User.phone.ilike(f"%{keyword}%"))
            | (User.nickname.ilike(f"%{keyword}%"))
        )
    total = q.count()
    rows = (
        q.order_by(Conversation.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    items = []
    for conv, user in rows:
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        items.append({
            "id": conv.id,
            "title": conv.title,
            "user_id": user.id,
            "user_phone": user.phone,
            "user_nickname": user.nickname,
            "interaction_type": conv.interaction_type.value,
            "status": conv.status.value,
            "message_count": msg_count,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
        })
    return {"total": total, "items": items}


def get_conversation_detail(db: Session, conversation_id: int) -> dict:
    row = (
        db.query(Conversation, User)
        .join(User, Conversation.user_id == User.id)
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not row:
        raise ValueError("对话不存在")
    conv, user = row
    from app.models.message import MessageRole
    from app.utils.legal_content import polish_legal_assistant_content

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    msg_items = []
    for m in messages:
        content = m.content or ""
        if m.role == MessageRole.ASSISTANT and content:
            content = polish_legal_assistant_content(content)
        msg_items.append({
            "id": m.id,
            "role": m.role.value,
            "content_type": m.content_type.value,
            "content": content,
            "ai_engine": m.ai_engine,
            "tokens_used": m.tokens_used or 0,
            "created_at": m.created_at,
        })
    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": user.id,
        "user_phone": user.phone,
        "interaction_type": conv.interaction_type.value,
        "status": conv.status.value,
        "created_at": conv.created_at,
        "messages": msg_items,
    }


def update_conversation_admin(
    db: Session,
    conversation_id: int,
    data: dict,
    operator_id: int,
) -> dict:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise ValueError("对话不存在")
    if "title" in data and data["title"] is not None:
        conv.title = data["title"].strip() or conv.title
    if "status" in data and data["status"] is not None:
        conv.status = ConversationStatus(data["status"])
    db.commit()
    db.refresh(conv)
    log_action(
        db,
        user_id=operator_id,
        action="update_conversation",
        resource="conversation",
        resource_id=str(conv.id),
    )
    return {"id": conv.id, "title": conv.title, "status": conv.status.value}


def delete_conversation_admin(db: Session, conversation_id: int, operator_id: int) -> None:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise ValueError("对话不存在")
    db.delete(conv)
    db.commit()
    log_action(
        db,
        user_id=operator_id,
        action="delete_conversation",
        resource="conversation",
        resource_id=str(conversation_id),
    )


def list_enterprises_admin(
    db: Session,
    page: int = 1,
    size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
) -> dict:
    from commercial.models.enterprise import Enterprise, EnterpriseMember, EnterpriseStatus

    q = db.query(Enterprise, User).join(User, Enterprise.owner_user_id == User.id)
    if status:
        try:
            q = q.filter(Enterprise.status == EnterpriseStatus(status))
        except ValueError:
            pass
    if keyword:
        q = q.filter(
            (Enterprise.name.ilike(f"%{keyword}%"))
            | (Enterprise.contact_phone.ilike(f"%{keyword}%"))
            | (User.phone.ilike(f"%{keyword}%"))
            | (User.nickname.ilike(f"%{keyword}%"))
        )
    total = q.count()
    rows = q.order_by(Enterprise.created_at.desc()).offset((page - 1) * size).limit(size).all()
    items = []
    for ent, owner in rows:
        member_count = db.query(EnterpriseMember).filter(EnterpriseMember.enterprise_id == ent.id).count()
        items.append({
            "id": ent.id,
            "name": ent.name,
            "industry": ent.industry,
            "credit_code": ent.credit_code,
            "contact_name": ent.contact_name,
            "contact_phone": ent.contact_phone,
            "owner_user_id": owner.id,
            "owner_phone": owner.phone,
            "owner_nickname": owner.nickname,
            "status": ent.status.value,
            "member_count": member_count,
            "created_at": ent.created_at,
            **_enterprise_subscription_snapshot(db, ent),
        })
    return {"total": total, "items": items}


def get_enterprise_admin(db: Session, enterprise_id: int) -> dict:
    from commercial.models.enterprise import Enterprise, EnterpriseMember, ContractLedger, ComplianceCheck

    row = (
        db.query(Enterprise, User)
        .join(User, Enterprise.owner_user_id == User.id)
        .filter(Enterprise.id == enterprise_id)
        .first()
    )
    if not row:
        raise ValueError("企业不存在")
    ent, owner = row
    member_count = db.query(EnterpriseMember).filter(EnterpriseMember.enterprise_id == ent.id).count()
    contract_count = db.query(ContractLedger).filter(ContractLedger.enterprise_id == ent.id).count()
    compliance_count = db.query(ComplianceCheck).filter(ComplianceCheck.enterprise_id == ent.id).count()
    return {
        "id": ent.id,
        "name": ent.name,
        "industry": ent.industry,
        "credit_code": ent.credit_code,
        "contact_name": ent.contact_name,
        "contact_phone": ent.contact_phone,
        "owner_user_id": owner.id,
        "owner_phone": owner.phone,
        "owner_nickname": owner.nickname,
        "status": ent.status.value,
        "member_count": member_count,
        "contract_count": contract_count,
        "compliance_count": compliance_count,
        "created_at": ent.created_at,
        **_enterprise_subscription_snapshot(db, ent),
    }


def update_enterprise_admin(db: Session, enterprise_id: int, data: dict, operator_id: int) -> dict:
    from commercial.models.enterprise import Enterprise, EnterpriseStatus
    from commercial.services.enterprise_subscription_service import admin_apply_enterprise_subscription

    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise ValueError("企业不存在")
    changes = {}
    if "status" in data and data["status"]:
        ent.status = EnterpriseStatus(data["status"])
        changes["status"] = data["status"]
    if "name" in data and data["name"]:
        ent.name = data["name"]
        changes["name"] = data["name"]

    sub_changes = {}
    if any(k in data for k in ("seat_limit", "subscription_expires_at", "is_trial", "grant_trial_days")):
        expires = data.get("subscription_expires_at")
        admin_apply_enterprise_subscription(
            db,
            ent,
            seat_limit=data.get("seat_limit"),
            subscription_expires_at=expires,
            is_trial=data.get("is_trial"),
            grant_trial_days=data.get("grant_trial_days"),
        )
        sub_changes = {
            "seat_limit": ent.seat_limit,
            "subscription_expires_at": ent.subscription_expires_at.isoformat() if ent.subscription_expires_at else None,
            "is_trial": ent.is_trial,
        }
        changes.update(sub_changes)

    db.commit()
    if changes:
        log_action(
            db,
            user_id=operator_id,
            action="update_enterprise",
            resource="enterprise",
            resource_id=str(enterprise_id),
            detail=changes,
        )
    return get_enterprise_admin(db, enterprise_id)


def _admin_enterprise_kpi(db: Session, enterprise_id: int) -> dict:
    from decimal import Decimal

    from commercial.models.enterprise import (
        ComplianceCheck,
        ContractLedger,
        ContractStatus,
        EnterpriseCaseAnalysis,
        EnterpriseKnowledgeDoc,
        IPMonitor,
        Receivable,
        ReceivableStatus,
    )

    today = date.today()
    contract_total = db.query(ContractLedger).filter(ContractLedger.enterprise_id == enterprise_id).count()
    contract_pending = db.query(ContractLedger).filter(
        ContractLedger.enterprise_id == enterprise_id,
        ContractLedger.status == ContractStatus.PENDING_REVIEW,
    ).count()
    contract_expiring = db.query(ContractLedger).filter(
        ContractLedger.enterprise_id == enterprise_id,
        ContractLedger.status.in_([ContractStatus.APPROVED, ContractStatus.ACTIVE]),
        ContractLedger.expire_date.isnot(None),
        ContractLedger.expire_date <= today + timedelta(days=30),
        ContractLedger.expire_date >= today,
    ).count()
    receivables = db.query(Receivable).filter(Receivable.enterprise_id == enterprise_id).all()
    receivable_total = float(sum((r.amount for r in receivables), Decimal("0")))
    receivable_overdue = sum(1 for r in receivables if r.status == ReceivableStatus.OVERDUE)
    compliance_rows = db.query(ComplianceCheck).filter(ComplianceCheck.enterprise_id == enterprise_id).all()
    compliance_count = len(compliance_rows)
    compliance_pending_items = 0
    for check in compliance_rows:
        checklist = check.checklist or []
        compliance_pending_items += sum(1 for i in checklist if (i.get("status") or "pending") == "pending")
    ip_rows = db.query(IPMonitor).filter(IPMonitor.enterprise_id == enterprise_id).all()
    ip_alerts = sum(len(r.alerts or []) for r in ip_rows)
    knowledge_docs = (
        db.query(EnterpriseKnowledgeDoc).filter(EnterpriseKnowledgeDoc.enterprise_id == enterprise_id).count()
    )
    case_analyses = (
        db.query(EnterpriseCaseAnalysis).filter(EnterpriseCaseAnalysis.enterprise_id == enterprise_id).count()
    )
    todo_count = contract_pending + contract_expiring + (1 if compliance_pending_items else 0) + receivable_overdue
    return {
        "contract_total": contract_total,
        "contract_pending": contract_pending,
        "contract_expiring": contract_expiring,
        "receivable_total": receivable_total,
        "receivable_overdue": receivable_overdue,
        "compliance_count": compliance_count,
        "compliance_pending_items": compliance_pending_items,
        "ip_total": len(ip_rows),
        "ip_alerts": ip_alerts,
        "knowledge_docs": knowledge_docs,
        "case_analyses": case_analyses,
        "todo_count": todo_count,
    }


def get_enterprise_overview_admin(db: Session, enterprise_id: int) -> dict:
    from commercial.services.enterprise_quota_service import get_enterprise_usage_summary
    from commercial.services.enterprise_sla_service import get_sla_report_admin
    from commercial.services.enterprise_subscription_service import enterprise_subscription_active

    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise ValueError("企业不存在")
    kpi = _admin_enterprise_kpi(db, enterprise_id)
    sla = get_sla_report_admin(db, enterprise_id)
    usage = get_enterprise_usage_summary(db, enterprise_id)
    metrics = []
    for key in ("api_calls", "contract_reviews", "consult_hours"):
        item = usage.get(key) or {}
        total = item.get("total", 0)
        metrics.append(
            {
                "key": key,
                "label": item.get("label") or key,
                "used": float(item.get("used") or 0),
                "total": float(total) if total != -1 else float(item.get("used") or 0),
                "unit": item.get("unit") or "",
                "unlimited": total == -1,
            }
        )
    return {
        **kpi,
        "sla_score": sla.get("sla_score", 0),
        "sla_summary": sla.get("summary") or "",
        "subscription_active": enterprise_subscription_active(ent),
        "usage_metrics": metrics,
    }


def list_enterprise_members_admin(
    db: Session,
    enterprise_id: int,
    page: int = 1,
    size: int = 50,
) -> dict:
    from commercial.models.enterprise import EnterpriseMember

    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise ValueError("企业不存在")
    q = (
        db.query(EnterpriseMember, User)
        .join(User, EnterpriseMember.user_id == User.id)
        .filter(EnterpriseMember.enterprise_id == enterprise_id)
    )
    total = q.count()
    rows = q.order_by(EnterpriseMember.created_at.desc()).offset((page - 1) * size).limit(size).all()
    items = []
    for member, user in rows:
        items.append(
            {
                "id": member.id,
                "user_id": user.id,
                "phone": user.phone,
                "nickname": user.nickname,
                "role": member.role.value,
                "department": member.department,
                "status": member.status.value,
                "joined_at": member.joined_at,
                "created_at": member.created_at,
            }
        )
    return {"total": total, "items": items}


def get_enterprise_module_stats_admin(db: Session, enterprise_id: int) -> dict:
    from commercial.models.enterprise import EnterpriseMember, MemberStatus
    from commercial.services.enterprise_subscription_service import enterprise_subscription_active

    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise ValueError("企业不存在")
    kpi = _admin_enterprise_kpi(db, enterprise_id)
    active_members = (
        db.query(EnterpriseMember)
        .filter(
            EnterpriseMember.enterprise_id == enterprise_id,
            EnterpriseMember.status == MemberStatus.ACTIVE,
        )
        .count()
    )
    sub_active = enterprise_subscription_active(ent)
    workflow_steps = (ent.workflow_config or {}).get("steps") or []

    def stat(key: str, label: str, count: int, detail: str | None = None, status: str = "ok") -> dict:
        return {"key": key, "label": label, "count": count, "detail": detail, "status": status}

    items = [
        stat("contracts", "合同管理", kpi["contract_total"], f"待审批 {kpi['contract_pending']} · 30 天内到期 {kpi['contract_expiring']}", "warn" if kpi["contract_pending"] else "ok"),
        stat("compliance", "合规中心", kpi["compliance_count"], f"待办项 {kpi['compliance_pending_items']}", "warn" if kpi["compliance_pending_items"] else "ok"),
        stat("receivables", "账款管理", kpi["receivable_overdue"], f"逾期 {kpi['receivable_overdue']} 笔", "warn" if kpi["receivable_overdue"] else "ok"),
        stat("ip", "知识产权", kpi["ip_total"], f"预警 {kpi['ip_alerts']}", "warn" if kpi["ip_alerts"] else "ok"),
        stat("knowledge", "知识库", kpi["knowledge_docs"]),
        stat("case-analysis", "类案分析", kpi["case_analyses"]),
        stat("members", "团队成员", active_members, f"席位 {active_members}/{ent.seat_limit or '—'}"),
        stat("workflow", "审批配置", len(workflow_steps), "已配置步骤" if workflow_steps else "默认流程", "idle" if not workflow_steps else "ok"),
        stat("usage", "用量统计", 1 if sub_active else 0, "订阅有效" if sub_active else "未开通", "ok" if sub_active else "idle"),
        stat("sla", "SLA 报表", 1 if sub_active else 0, "可导出" if sub_active else "需订阅", "ok" if sub_active else "idle"),
        stat("brand", "白标设置", 1 if (ent.brand_config or {}) else 0, (ent.brand_config or {}).get("display_name") or "未配置", "ok" if ent.brand_config else "idle"),
        stat("sso", "单点登录", 1 if ent.sso_enabled else 0, (ent.sso_config or {}).get("provider") or "未启用", "ok" if ent.sso_enabled else "idle"),
        stat("notifications", "通知中心", 0, "按成员未读统计"),
    ]
    return {"items": items}


def get_enterprise_config_admin(db: Session, enterprise_id: int) -> dict:
    ent = db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    if not ent:
        raise ValueError("企业不存在")
    brand = ent.brand_config or {}
    steps = (ent.workflow_config or {}).get("steps") or []
    roles = []
    for step in steps:
        role = step.get("role")
        if role and role not in roles:
            roles.append(role)
    return {
        "sso_enabled": bool(ent.sso_enabled),
        "sso_email_domain": ent.sso_email_domain,
        "sso_provider": (ent.sso_config or {}).get("provider"),
        "department_isolation": bool(ent.department_isolation),
        "brand_display_name": brand.get("display_name"),
        "brand_primary_color": brand.get("primary_color"),
        "brand_logo_url": brand.get("logo_url"),
        "workflow_step_count": len(steps),
        "workflow_roles": roles,
    }


def list_push_tasks(db: Session, page: int = 1, size: int = 20) -> dict:
    q = db.query(PushTask)
    total = q.count()
    items = q.order_by(PushTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


def _sync_admin_account(db: Session, user: User) -> None:
    from app.models.admin_account import AdminAccount

    account = db.query(AdminAccount).filter(AdminAccount.user_id == user.id).first()
    if not user.is_admin:
        if account:
            account.status = "disabled"
        return
    phone = (user.phone or "").strip()
    if not phone:
        return
    if not account:
        account = AdminAccount(
            user_id=user.id,
            phone=phone,
            email=user.email or None,
            nickname=user.nickname,
            password_hash="",
            password_salt="",
            role=user.admin_role or "viewer",
            status="active" if user.status == UserStatus.ACTIVE else "disabled",
        )
        db.add(account)
        return
    account.phone = phone
    account.email = user.email or None
    account.nickname = user.nickname
    account.role = user.admin_role or account.role or "viewer"
    account.status = "active" if user.status == UserStatus.ACTIVE else "disabled"


def ensure_admin_user(db: Session, phone: str, password: str, nickname: str = "超级管理员") -> User:
    """只维护独立管理员行（users.phone 为空）。禁止把已有前台手机号提成管理员。"""
    from app.models.admin_account import AdminAccount

    ident = (phone or "").strip()
    if not ident:
        raise ValueError("管理员引导账号不能为空")

    front = (
        db.query(User)
        .filter(User.phone == ident, User.is_admin.is_(False))
        .first()
    )
    login_id = "manage" if front else ident

    account = (
        db.query(AdminAccount)
        .filter(
            (AdminAccount.phone == login_id)
            | (AdminAccount.phone == "manage")
            | (AdminAccount.nickname == "manage")
        )
        .first()
    )
    user = db.query(User).filter(User.id == account.user_id).first() if account else None
    if not user:
        user = db.query(User).filter(User.is_admin.is_(True), User.phone.is_(None)).first()
    if not user:
        user = User(
            phone=None,
            nickname=nickname,
            is_admin=True,
            admin_role="super_admin",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
    else:
        user.phone = None
        user.is_admin = True
        user.admin_role = "super_admin"
        user.password_hash = None
        user.password_salt = None

    if not account:
        account = AdminAccount(
            user_id=user.id,
            phone=login_id,
            email=None,
            nickname="manage",
            password_hash="",
            password_salt="",
            role="super_admin",
            status="active",
        )
        db.add(account)
    else:
        account.user_id = user.id
        account.phone = login_id
        account.nickname = "manage"
        account.role = "super_admin"
        account.status = "active"
    # 只在首次创建时写入引导密码。已有密码不能在每次进程启动时覆盖，否则改密后会回到初始密码。
    if password and not (account.password_hash and account.password_salt):
        assign_admin_password(account, password)
    db.commit()
    db.refresh(user)
    return user
