import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.admin_deps import require_admin_permission, require_super_admin
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import (
    ContentCreate,
    ContentResponse,
    ContentUpdate,
    DashboardStatsResponse,
    DashboardChartsResponse,
    PaginatedContent,
    PaginatedPush,
    PaginatedUsers,
    PushCreate,
    PushTaskResponse,
    AdminUserUpdate,
    AdminUserPasswordReset,
    AdminOrderItem,
    AdminOrderUpdate,
    PaginatedOrders,
    SettingResponse,
    SettingsUpdateRequest,
    LegalPagesSyncRequest,
    AiProviderResponse,
    AiProviderUpdate,
    AiTestResponse,
    PlanAdminCreate,
    PlanAdminUpdate,
    PlanAdminResponse,
    RolePermissionsResponse,
    UserDetailResponse,
    AdminWalletAdjust,
    AdminMembershipSet,
    WalletSummary,
    PaginatedAuditLogs,
    AuditLogBatchDelete,
    PaginatedConversations,
    AdminConversationDetail,
    AdminConversationUpdate,
    PaginatedEnterprises,
    AdminEnterpriseDetail,
    AdminEnterpriseUpdate,
    AdminEnterpriseCreate,
    AdminEnterpriseOverview,
    AdminEnterpriseModuleStats,
    AdminEnterpriseConfig,
    AdminEnterpriseConfigUpdate,
    AdminEnterpriseMemberCreate,
    AdminEnterpriseMemberUpdate,
    AdminEnterpriseMemberItem,
    PaginatedEnterpriseMembers,
    PaginatedEnterpriseRecords,
    PaginatedLaunchSplashes,
    LaunchSplashCreate,
    LaunchSplashUpdate,
    LaunchSplashResponse,
    PaginatedFeedbacks,
    FeedbackReply,
    FeedbackStatusUpdate,
    PaginatedDocumentTemplates,
    DocumentTemplateCreate,
    DocumentTemplateUpdate,
    DocumentTemplateResponse,
    RolePermissionsUpdate,
    PaginatedSearchLogs,
    AdminSearchLogDetail,
    SearchLogAdminCreate,
    SearchLogAdminUpdate,
    PaginatedContractReviews,
    AdminContractReviewDetail,
    ContractReviewAdminUpdate,
    PaginatedGeneratedDocs,
    AdminGeneratedDocDetail,
    GeneratedDocAdminCreate,
    GeneratedDocAdminUpdate,
    PaginatedLawyers,
    AdminLawyerItem,
    LawyerAdminCreate,
    LawyerAdminUpdate,
    PaginatedLawyerConsultations,
    LawyerConsultationAdminUpdate,
    LawyerConsultationAdminCreate,
    PaginatedAiUsage,
    PaginatedAiUsageByUser,
    AiUsageServiceOption,
)
from app.schemas.platform import AdminPasswordChange, AdminProfileUpdate, OpenApiKeyCreate, OpenApiKeyUpdate
from app.services import admin_service, cms_service
from app.services import config_service
from app.services import ai_usage_service

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("stats", "read")),
):
    return admin_service.get_dashboard_stats(db)


@router.get("/stats/charts", response_model=DashboardChartsResponse)
def dashboard_charts(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("stats", "read")),
):
    return admin_service.get_dashboard_charts(db)


@router.get("/ai-usage", response_model=PaginatedAiUsage)
def list_ai_usage(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    service_key: str | None = None,
    ai_engine: str | None = None,
    keyword: str | None = None,
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("stats", "read")),
):
    return ai_usage_service.list_admin_ai_usage(
        db,
        page=page,
        size=size,
        user_id=user_id,
        service_key=service_key,
        ai_engine=ai_engine,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/ai-usage/by-user", response_model=PaginatedAiUsageByUser)
def list_ai_usage_by_user(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    service_key: str | None = None,
    ai_engine: str | None = None,
    keyword: str | None = None,
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("stats", "read")),
):
    return ai_usage_service.list_admin_ai_usage_by_user(
        db,
        page=page,
        size=size,
        user_id=user_id,
        service_key=service_key,
        ai_engine=ai_engine,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/ai-usage/service-options", response_model=list[AiUsageServiceOption])
def list_ai_usage_service_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("stats", "read")),
):
    return ai_usage_service.list_service_options(db)


@router.get("/users", response_model=PaginatedUsers)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("users", "read")),
):
    return admin_service.list_users(db, page, size, keyword)


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("users", "write")),
):
    try:
        user = admin_service.update_user(
            db,
            user_id,
            body.model_dump(exclude_unset=True),
            operator_id=admin.id,
            operator=admin,
        )
        return {"id": user.id, "status": user.status.value, "is_admin": user.is_admin, "admin_role": user.admin_role}
    except ValueError as e:
        msg = str(e)
        if "超级管理员" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=404, detail=msg)


@router.post("/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    body: AdminUserPasswordReset,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("users", "write")),
):
    try:
        admin_service.reset_user_password(db, user_id, body.new_password, operator_id=admin.id)
        return {"message": "密码已重置"}
    except ValueError as e:
        msg = str(e)
        if msg == "用户不存在":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("users", "read")),
):
    try:
        return admin_service.get_user_detail(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/content", response_model=PaginatedContent)
def list_content(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    category: str | None = None,
    exclude_category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("content", "read")),
):
    return admin_service.list_articles(db, page, size, status, category, exclude_category)


@router.post("/content", response_model=ContentResponse)
def create_content(
    body: ContentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("content", "write")),
):
    return admin_service.create_article(db, admin.id, body.model_dump())


@router.patch("/content/{article_id}", response_model=ContentResponse)
def update_content(
    article_id: int,
    body: ContentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("content", "write")),
):
    try:
        return admin_service.update_article(
            db, article_id, body.model_dump(exclude_unset=True), operator_id=admin.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/content/{article_id}")
def delete_content(
    article_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("content", "write")),
):
    admin_service.delete_article(db, article_id, operator_id=admin.id)
    return {"message": "已删除"}


@router.get("/settings")
def admin_list_settings(
    category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("settings", "read")),
):
    return config_service.list_settings_for_admin(db, category)


@router.put("/settings", response_model=list[SettingResponse])
def admin_update_settings(
    body: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("settings", "write")),
):
    items = [i.model_dump() for i in body.items]
    return config_service.upsert_settings(db, items, operator_id=admin.id)


@router.post("/settings/legal-pages/sync-defaults")
def admin_sync_legal_pages_defaults(
    body: LegalPagesSyncRequest | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("settings", "write")),
):
    req = body or LegalPagesSyncRequest()
    updated = config_service.sync_legal_pages_from_defaults(
        db,
        req.keys,
        force=req.force,
        operator_id=admin.id,
    )
    return {"updated_keys": updated, "count": len(updated)}


# ── AI 接口配置 ──

@router.get("/ai-providers", response_model=list[AiProviderResponse])
def admin_list_ai_providers(
    category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("ai", "read")),
):
    return config_service.list_ai_providers(db, category=category)


@router.patch("/ai-providers/{provider_id}", response_model=AiProviderResponse)
def admin_update_ai_provider(
    provider_id: int,
    body: AiProviderUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("ai", "write")),
):
    try:
        config_service.update_ai_provider(db, provider_id, body.model_dump(exclude_unset=True), operator_id=admin.id)
        for item in config_service.list_ai_providers(db):
            if item["id"] == provider_id:
                return item
        raise HTTPException(status_code=404, detail="未找到")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ai-providers/{provider_id}/test", response_model=AiTestResponse)
async def admin_test_ai_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("ai", "write")),
):
    try:
        return await config_service.test_ai_provider(db, provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/integrations/health")
async def admin_integrations_health(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("ai", "read")),
):
    from app.services import integration_health
    return await integration_health.run_all_checks(db)


# ── 角色权限 ──

@router.get("/roles", response_model=RolePermissionsResponse)
def admin_roles(
    _: User = Depends(require_admin_permission("settings", "read")),
):
    return config_service.get_role_permissions()


@router.put("/roles", response_model=RolePermissionsResponse)
def admin_update_roles(
    body: RolePermissionsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("settings", "write")),
):
    return config_service.update_role_permissions(body.matrix, admin.id, db)


# ── 订单管理 ──

@router.get("/audit-logs", response_model=PaginatedAuditLogs)
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("audit_logs", "read")),
):
    return admin_service.list_audit_logs(db, page, size, keyword, action, resource)


@router.delete("/audit-logs/{log_id}")
def delete_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    deleted = admin_service.delete_audit_logs(db, [log_id], admin.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="日志不存在")
    return {"message": "已删除", "deleted": deleted}


@router.post("/audit-logs/batch-delete")
def delete_audit_logs(
    body: AuditLogBatchDelete,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    deleted = admin_service.delete_audit_logs(db, body.ids, admin.id)
    return {"message": "已删除", "deleted": deleted}


@router.get("/conversations", response_model=PaginatedConversations)
def list_conversations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    user_id: int | None = None,
    interaction_type: str | None = None,
    interaction_types: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("conversations", "read")),
):
    return admin_service.list_conversations(
        db, page, size, keyword, user_id, interaction_type, interaction_types
    )


@router.get("/conversations/{conversation_id}", response_model=AdminConversationDetail)
def get_conversation_detail(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("conversations", "read")),
):
    try:
        return admin_service.get_conversation_detail(db, conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/conversations/{conversation_id}")
def admin_update_conversation(
    conversation_id: int,
    body: AdminConversationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("conversations", "write")),
):
    try:
        return admin_service.update_conversation_admin(
            db, conversation_id, body.model_dump(exclude_unset=True), admin.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/conversations/{conversation_id}")
def admin_delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("conversations", "write")),
):
    try:
        admin_service.delete_conversation_admin(db, conversation_id, admin.id)
        return {"message": "已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── 企业管理 ──

@router.get("/feedbacks", response_model=PaginatedFeedbacks)
def admin_list_feedbacks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_permission("feedbacks", "read")),
):
    return cms_service.list_feedbacks_admin(db, page, size, status, keyword)


@router.patch("/feedbacks/{feedback_id}/reply")
def admin_reply_feedback(
    feedback_id: int,
    body: FeedbackReply,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("feedbacks", "write")),
):
    try:
        fb = cms_service.reply_feedback(db, feedback_id, body.admin_reply, admin.id)
        return {"id": fb.id, "status": fb.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/feedbacks/{feedback_id}/status")
def admin_update_feedback_status(
    feedback_id: int,
    body: FeedbackStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("feedbacks", "write")),
):
    try:
        fb = cms_service.update_feedback_status(db, feedback_id, body.status, admin.id)
        return {"id": fb.id, "status": fb.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── 文书模板 ──

def _admin_account_for(db: Session, admin: User):
    from app.models.admin_account import AdminAccount

    account = db.query(AdminAccount).filter(AdminAccount.user_id == admin.id).first()
    if account:
        return account
    phone = (admin.phone or "").strip()
    if phone:
        return (
            db.query(AdminAccount)
            .filter((AdminAccount.phone == phone) | (AdminAccount.nickname == phone))
            .first()
        )
    return None


@router.get("/me")
def admin_get_profile(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    account = _admin_account_for(db, admin)
    return {
        "id": admin.id,
        "phone": (account.phone if account else None) or admin.phone or "",
        "nickname": admin.nickname or (account.nickname if account else "") or "",
        "admin_role": admin.admin_role or (account.role if account else "") or "",
        "created_at": admin.created_at,
    }


@router.patch("/me")
def admin_update_profile(
    body: AdminProfileUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("settings", "write")),
):
    if body.nickname:
        admin.nickname = body.nickname
    db.commit()
    db.refresh(admin)
    return {"id": admin.id, "nickname": admin.nickname}


@router.post("/me/password")
def admin_change_password(
    body: AdminPasswordChange,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    from app.core.security import assign_admin_password, check_admin_password
    from app.models.user_session import UserSession
    from app.services.session_service import revoke_user_sessions

    if not admin.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    account = _admin_account_for(db, admin)
    if not account:
        raise HTTPException(status_code=400, detail="未找到管理员账号，无法修改密码")
    if account.user_id != admin.id:
        account.user_id = admin.id
    if not check_admin_password(account, body.old_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    assign_admin_password(account, body.new_password)
    try:
        db.flush()
    except Exception:
        logger.exception("admin password save failed user_id=%s", admin.id)
        db.rollback()
        raise HTTPException(status_code=500, detail="新密码未能保存，请重试")
    db.refresh(account)
    if not check_admin_password(account, body.new_password):
        db.rollback()
        raise HTTPException(status_code=500, detail="新密码未能保存，请重试")
    for obj in list(db.identity_map.values()):
        if isinstance(obj, UserSession):
            db.expunge(obj)
    revoke_user_sessions(db, admin.id)
    db.commit()
    return {"message": "密码已修改，请重新登录"}


@router.post("/upload")
async def admin_upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_permission("settings", "write")),
):
    from app.services import upload_service

    try:
        url = await upload_service.save_upload(db, file, subdir="admin")
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionError as e:
        logger.exception("admin upload permission denied")
        raise HTTPException(
            status_code=500,
            detail="文件保存失败：uploads 目录无写权限，请重建 backend 容器后重试",
        ) from e
    except OSError as e:
        logger.exception("admin upload failed")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}") from e


# ── 前台法律服务 ──

