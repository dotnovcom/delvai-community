from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AiEngineUsageItem(BaseModel):
    engine: str
    label: str
    messages: int
    tokens: int


class DashboardStatsResponse(BaseModel):
    user_total: int
    user_active: int
    user_new_week: int
    conversation_total: int
    enterprise_total: int
    order_total: int
    order_paid: int
    revenue_total: float
    membership_active: int
    search_total_7d: int = 0
    search_es_hits_7d: int = 0
    search_farui_calls_7d: int = 0
    search_indexed_7d: int = 0
    search_es_hit_rate_7d: float = 0.0
    ai_usage_7d: list[AiEngineUsageItem] = []


class TrendPoint(BaseModel):
    date: str
    users: int
    conversations: int
    orders: int


class MembershipSlice(BaseModel):
    name: str
    value: int


class RecentOrderItem(BaseModel):
    order_no: str
    plan_name: str
    amount: float
    status: str
    user_phone: str | None = None
    created_at: datetime

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v):
        return float(v) if v is not None else 0.0


class DashboardChartsResponse(BaseModel):
    trend: list[TrendPoint]
    membership_distribution: list[MembershipSlice]
    recent_orders: list[RecentOrderItem]


class AdminUserUpdate(BaseModel):
    status: Optional[Literal["active", "disabled"]] = None
    nickname: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    is_verified: Optional[bool] = None
    is_admin: Optional[bool] = None
    admin_role: Optional[Literal["super_admin", "operator", "content_editor", "viewer"]] = None


class AdminUserPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=64)


class AdminUserItem(BaseModel):
    id: int
    phone: Optional[str] = None
    email: Optional[str] = None
    nickname: Optional[str] = None
    platform: str
    status: str
    is_admin: bool
    is_verified: bool = False
    admin_role: Optional[str] = None
    created_at: datetime
    vip_label: Optional[str] = None
    vip_expire_at: Optional[datetime] = None
    balance: float = 0
    points: int = 0
    points_display_name: str = "法理豆"


class AdminWalletAdjust(BaseModel):
    balance_delta: Optional[float] = None
    points_delta: Optional[int] = None
    validity_days: Optional[int] = Field(None, ge=0, le=3650)
    remark: str = Field(..., min_length=1, max_length=500)

    @field_validator("balance_delta", "points_delta", mode="before")
    @classmethod
    def _empty_str_none(cls, v):
        if v == "":
            return None
        return v

    @model_validator(mode="after")
    def _require_delta(self):
        if self.balance_delta is None and self.points_delta is None:
            raise ValueError("请填写余额或积分调整量")
        return self


class AdminMembershipSet(BaseModel):
    plan_id: Optional[int] = None
    extend_days: Optional[int] = Field(None, ge=1, le=3650)
    cancel: bool = False


class WalletSummary(BaseModel):
    balance: float
    points: int
    points_display_name: str
    points_expiring_soon: int = 0


class WalletTransactionItem(BaseModel):
    id: int
    type: str
    amount: float
    balance_after: float
    remark: Optional[str] = None
    created_at: datetime


class PointsLedgerItem(BaseModel):
    id: int
    type: str
    delta: int
    balance_after: int
    remark: Optional[str] = None
    created_at: datetime


class PaginatedUsers(BaseModel):
    total: int
    items: list[AdminUserItem]


class ContentCreate(BaseModel):
    title: str = Field(..., min_length=2)
    summary: Optional[str] = None
    content: str
    category: str = "announcement"
    cover_url: Optional[str] = None
    status: str = "draft"


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None
    status: Optional[str] = None


class ContentResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    content: str
    category: str
    cover_url: Optional[str] = None
    status: str
    author_id: Optional[int] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedContent(BaseModel):
    total: int
    items: list[ContentResponse]


class PushCreate(BaseModel):
    title: str
    content: str
    target_type: Literal["user", "tag", "all", "email_bound"] = "all"
    target_value: Optional[str] = None
    push_type: str = "system"
    user_ids: Optional[list[int]] = None
    channels: Optional[list[str]] = None


class PushTaskResponse(BaseModel):
    id: int
    title: str
    content: str
    target_type: str
    target_value: Optional[str] = None
    push_type: str
    status: str
    sent_count: int
    payload: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPush(BaseModel):
    total: int
    items: list[PushTaskResponse]


class SettingItem(BaseModel):
    key: str
    value: str | None = None
    category: str = "basic"
    label: str | None = None
    value_type: str = "string"


class SettingsUpdateRequest(BaseModel):
    items: list[SettingItem]


class LegalPagesSyncRequest(BaseModel):
    keys: list[str] | None = None
    force: bool = True


class SettingResponse(BaseModel):
    key: str
    value: str | None = None
    category: str
    label: str | None = None
    value_type: str
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AiProviderResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str = "ai"
    description: str | None = None
    api_key_masked: str = ""
    api_secret_masked: str = ""
    has_api_key: bool = False
    has_api_secret: bool = False
    base_url: str | None = None
    extra_json: str = "{}"
    enabled: bool
    daily_limit: int
    call_count_today: int
    updated_at: datetime | None = None


class AiProviderUpdate(BaseModel):
    name: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    base_url: str | None = None
    description: str | None = None
    extra_json: str | None = None
    enabled: bool | None = None
    daily_limit: int | None = None


class AiTestResponse(BaseModel):
    success: bool
    latency_ms: int
    message: str


class PlanAdminCreate(BaseModel):
    name: str
    code: str
    level: int = 0
    plan_type: str = "subscription"
    audience: str = "personal"
    billing_cycle: str = "monthly"
    price: float
    original_price: float | None = None
    duration_days: int | None = None
    description: str | None = None
    features: list | None = None
    quota: dict | None = None
    status: str = "active"
    sort_order: int = 0


class PlanAdminUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    level: int | None = None
    plan_type: str | None = None
    audience: str | None = None
    billing_cycle: str | None = None
    price: float | None = None
    original_price: float | None = None
    duration_days: int | None = None
    description: str | None = None
    features: list | None = None
    quota: dict | None = None
    status: str | None = None
    sort_order: int | None = None


class PlanAdminResponse(BaseModel):
    id: int
    name: str
    code: str
    level: int
    plan_type: str
    audience: str = "personal"
    billing_cycle: str = "monthly"
    price: float
    original_price: float | None = None
    duration_days: int
    description: str | None = None
    features: list | None = None
    quota: dict | None = None
    status: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("price", "original_price", mode="before")
    @classmethod
    def _coerce_decimal(cls, v):
        if v is None:
            return None
        return float(v)


class RolePermissionsResponse(BaseModel):
    roles: list[str]
    modules: list[str]
    actions: list[str]
    matrix: dict[str, dict[str, list[str]]]


class AdminOrderItem(BaseModel):
    order_no: str
    status: str
    amount: float
    platform: str
    original_amount: float = 0
    cash_amount: float = 0
    balance_used: float = 0
    points_used: int = 0
    points_yuan: float = 0
    pay_channel: str = ""
    payment_method: str = ""
    plan_name: str
    order_type: str = "membership"
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    paid_at: datetime | None = None
    created_at: datetime
    payment_mode: str | None = None
    invoice_title: str | None = None
    tax_id: str | None = None
    invoice_email: str | None = None
    invoice_status: str | None = None
    bank_reference: str | None = None

    @field_validator("amount", "original_amount", "cash_amount", "balance_used", "points_yuan", mode="before")
    @classmethod
    def _coerce_amount(cls, v):
        return float(v) if v is not None else 0.0


class PaginatedOrders(BaseModel):
    total: int
    items: list[AdminOrderItem]


class AdminOrderUpdate(BaseModel):
    status: Optional[Literal["cancelled", "refunded", "paid"]] = None
    invoice_status: Optional[Literal["none", "requested", "issued"]] = None
    bank_reference: Optional[str] = None


class UserMembershipRecord(BaseModel):
    plan_name: str
    level: int
    status: str
    start_at: datetime
    expire_at: datetime | None = None


class UserOrderBrief(BaseModel):
    order_no: str
    plan_name: str
    amount: float
    status: str
    created_at: datetime

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v):
        return float(v) if v is not None else 0.0


class UserDetailResponse(BaseModel):
    id: int
    phone: str | None = None
    nickname: str | None = None
    platform: str
    status: str
    is_admin: bool
    admin_role: str | None = None
    created_at: datetime
    conversation_count: int
    message_count: int
    memberships: list[UserMembershipRecord]
    orders: list[UserOrderBrief]
    wallet: WalletSummary
    vip_label: Optional[str] = None
    vip_expire_at: Optional[datetime] = None
    wallet_transactions: list[WalletTransactionItem] = []
    points_ledger: list[PointsLedgerItem] = []


class AuditLogItem(BaseModel):
    id: int
    user_id: int | None = None
    operator_name: str = ""
    action: str
    action_label: str = ""
    resource: str
    resource_label: str = ""
    resource_id: str | None = None
    summary: str = ""
    detail: dict | None = None
    ip: str | None = None
    created_at: datetime


class PaginatedAuditLogs(BaseModel):
    total: int
    items: list[AuditLogItem]


class AuditLogBatchDelete(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=200)


class AdminConversationItem(BaseModel):
    id: int
    title: str
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    interaction_type: str
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class PaginatedConversations(BaseModel):
    total: int
    items: list[AdminConversationItem]


class AdminMessageItem(BaseModel):
    id: int
    role: str
    content_type: str
    content: str
    ai_engine: str | None = None
    created_at: datetime


class AdminConversationDetail(BaseModel):
    id: int
    title: str
    user_id: int
    user_phone: str | None = None
    interaction_type: str
    status: str
    created_at: datetime
    messages: list[AdminMessageItem]


class AdminConversationUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[Literal["active", "archived", "deleted"]] = None


class AdminEnterpriseItem(BaseModel):
    id: int
    name: str
    industry: str | None = None
    credit_code: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    owner_user_id: int
    owner_phone: str | None = None
    owner_nickname: str | None = None
    status: str
    member_count: int
    created_at: datetime
    plan_id: int | None = None
    plan_name: str | None = None
    seat_limit: int | None = None
    seats_used: int | None = None
    subscription_expires_at: datetime | None = None
    subscription_active: bool = False
    is_trial: bool = False


class PaginatedEnterprises(BaseModel):
    total: int
    items: list[AdminEnterpriseItem]


class AdminEnterpriseDetail(AdminEnterpriseItem):
    contract_count: int
    compliance_count: int


class AdminEnterpriseUpdate(BaseModel):
    status: Optional[Literal["active", "suspended"]] = None
    name: Optional[str] = None
    industry: Optional[str] = None
    credit_code: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    seat_limit: Optional[int] = Field(None, ge=1)
    subscription_expires_at: Optional[datetime] = None
    is_trial: Optional[bool] = None
    grant_trial_days: Optional[int] = Field(None, ge=1, le=90)


class AdminEnterpriseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    owner_phone: str = Field(..., min_length=11, max_length=20)
    industry: Optional[str] = None
    credit_code: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    seat_limit: Optional[int] = Field(None, ge=1)
    grant_trial_days: Optional[int] = Field(None, ge=1, le=90)


class AdminEnterpriseMemberCreate(BaseModel):
    phone: str = Field(..., min_length=11, max_length=20)
    role: Literal["admin", "member", "viewer"] = "member"
    department: Optional[str] = None


class AdminEnterpriseMemberUpdate(BaseModel):
    role: Optional[Literal["admin", "member", "viewer"]] = None
    department: Optional[str] = None
    status: Optional[Literal["active", "pending", "removed"]] = None


class AdminEnterpriseConfigUpdate(BaseModel):
    department_isolation: Optional[bool] = None
    sso_enabled: Optional[bool] = None
    sso_email_domain: Optional[str] = None
    brand_display_name: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_logo_url: Optional[str] = None
    workflow_steps: Optional[list[dict]] = None


class AdminEnterpriseRecordItem(BaseModel):
    id: int
    enterprise_id: int
    enterprise_name: str | None = None
    created_at: datetime | None = None


class PaginatedEnterpriseRecords(BaseModel):
    total: int
    module: str
    items: list[dict]


class AdminEnterpriseMemberItem(BaseModel):
    id: int
    user_id: int
    phone: str | None = None
    nickname: str | None = None
    role: str
    department: str | None = None
    status: str
    joined_at: datetime | None = None
    created_at: datetime


class PaginatedEnterpriseMembers(BaseModel):
    total: int
    items: list[AdminEnterpriseMemberItem]


class AdminEnterpriseUsageMetric(BaseModel):
    key: str
    label: str
    used: float
    total: float
    unit: str
    unlimited: bool = False


class AdminEnterpriseOverview(BaseModel):
    contract_total: int
    contract_pending: int
    contract_expiring: int
    receivable_total: float
    receivable_overdue: int
    compliance_count: int
    compliance_pending_items: int
    ip_total: int
    ip_alerts: int
    knowledge_docs: int
    case_analyses: int
    todo_count: int
    sla_score: int
    sla_summary: str
    subscription_active: bool
    usage_metrics: list[AdminEnterpriseUsageMetric] = []


class AdminEnterpriseModuleStat(BaseModel):
    key: str
    label: str
    count: int
    detail: str | None = None
    status: str = "ok"


class AdminEnterpriseModuleStats(BaseModel):
    items: list[AdminEnterpriseModuleStat]


class AdminEnterpriseConfig(BaseModel):
    sso_enabled: bool
    sso_email_domain: str | None = None
    sso_provider: str | None = None
    department_isolation: bool
    brand_display_name: str | None = None
    brand_primary_color: str | None = None
    brand_logo_url: str | None = None
    workflow_step_count: int
    workflow_roles: list[str] = []


class LaunchSplashCreate(BaseModel):
    title: str = ""
    platform: str
    enabled: bool = True
    content_type: str = "image"
    media_url: Optional[str] = None
    html_content: Optional[str] = None
    link_url: Optional[str] = None
    duration_sec: int = 0
    allow_skip: bool = True
    sort_order: int = 0
    status: str = "active"
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class LaunchSplashUpdate(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    enabled: Optional[bool] = None
    content_type: Optional[str] = None
    media_url: Optional[str] = None
    html_content: Optional[str] = None
    link_url: Optional[str] = None
    duration_sec: Optional[int] = None
    allow_skip: Optional[bool] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class LaunchSplashResponse(BaseModel):
    id: int
    title: str
    platform: str
    enabled: bool
    content_type: str
    media_url: str | None = None
    html_content: str | None = None
    link_url: str | None = None
    duration_sec: int
    allow_skip: bool
    sort_order: int
    status: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedLaunchSplashes(BaseModel):
    total: int
    items: list[LaunchSplashResponse]


class LaunchSplashItemPublic(BaseModel):
    id: int
    title: str
    content_type: str
    media_url: str | None = None
    html_content: str | None = None
    link_url: str | None = None
    duration_sec: int
    allow_skip: bool
    sort_order: int

    model_config = {"from_attributes": True}


class LaunchSplashPublicResponse(BaseModel):
    platform: str
    version: str
    items: list[LaunchSplashItemPublic]


class FeedbackItem(BaseModel):
    id: int
    user_id: int | None = None
    user_phone: str | None = None
    user_nickname: str | None = None
    category: str
    content: str
    contact: str | None = None
    status: str
    admin_reply: str | None = None
    replied_at: datetime | None = None
    created_at: datetime


class PaginatedFeedbacks(BaseModel):
    total: int
    items: list[FeedbackItem]


class FeedbackReply(BaseModel):
    admin_reply: str


class FeedbackStatusUpdate(BaseModel):
    status: Literal["pending", "replied", "closed"]


class FeedbackCreate(BaseModel):
    category: str = "general"
    content: str = Field(..., min_length=5)
    contact: Optional[str] = None


class DocumentTemplateCreate(BaseModel):
    name: str
    category: str
    template_body: str
    field_schema: Optional[list[str]] = None
    sort_order: int = 0
    status: str = "active"


class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    template_body: Optional[str] = None
    field_schema: Optional[list[str]] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None


class DocumentTemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    template_body: str
    field_schema: list | None = None
    sort_order: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedDocumentTemplates(BaseModel):
    total: int
    items: list[DocumentTemplateResponse]


class AdminSearchLogItem(BaseModel):
    id: int
    kind: str
    query: str
    source: str
    es_hit_count: int
    farui_hit_count: int
    indexed_count: int
    latency_ms: int
    created_at: datetime


class PaginatedSearchLogs(BaseModel):
    total: int
    items: list[AdminSearchLogItem]


class AdminSearchLogHitSample(BaseModel):
    title: str
    snippet: str
    source: str


class AdminSearchLogDetail(AdminSearchLogItem):
    kind_label: str
    source_label: str
    sample_hits: list[AdminSearchLogHitSample] = []


class SearchLogAdminCreate(BaseModel):
    kind: str
    query: str
    source: str = "es"
    es_hit_count: int = 0
    farui_hit_count: int = 0
    indexed_count: int = 0
    latency_ms: int = 0


class SearchLogAdminUpdate(BaseModel):
    kind: Optional[str] = None
    query: Optional[str] = None
    source: Optional[str] = None
    es_hit_count: Optional[int] = None
    farui_hit_count: Optional[int] = None
    indexed_count: Optional[int] = None
    latency_ms: Optional[int] = None


class AdminContractReviewItem(BaseModel):
    id: int
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    file_name: str
    file_type: str
    status: str
    risk_high: int | None = None
    risk_medium: int | None = None
    risk_low: int | None = None
    created_at: datetime


class PaginatedContractReviews(BaseModel):
    total: int
    items: list[AdminContractReviewItem]


class AdminContractReviewDetail(AdminContractReviewItem):
    file_url: str
    result: dict | None = None


class ContractReviewAdminUpdate(BaseModel):
    status: Optional[str] = None
    file_name: Optional[str] = None


class AdminGeneratedDocItem(BaseModel):
    id: int
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    doc_type: str
    title: str
    content_preview: str
    file_url: str | None = None
    created_at: datetime


class PaginatedGeneratedDocs(BaseModel):
    total: int
    items: list[AdminGeneratedDocItem]


class AdminGeneratedDocDetail(AdminGeneratedDocItem):
    params: dict | None = None
    content: str


class GeneratedDocAdminCreate(BaseModel):
    user_id: int
    doc_type: str
    title: str
    content: str = ""


class GeneratedDocAdminUpdate(BaseModel):
    doc_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


class AdminLawyerItem(BaseModel):
    id: int
    name: str
    title: str | None = None
    firm: str | None = None
    specialties: list = []
    rating: float = 5.0
    case_count: int = 0
    avatar: str | None = None
    intro: str | None = None
    status: str
    created_at: datetime

    @field_validator("rating", mode="before")
    @classmethod
    def _coerce_rating(cls, v):
        return float(v) if v is not None else 0.0


class PaginatedLawyers(BaseModel):
    total: int
    items: list[AdminLawyerItem]


class LawyerAdminCreate(BaseModel):
    name: str
    title: str | None = None
    firm: str | None = None
    specialties: list | None = None
    rating: float = 5.0
    case_count: int = 0
    avatar: str | None = None
    intro: str | None = None
    status: str = "active"


class LawyerAdminUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    firm: str | None = None
    specialties: list | None = None
    rating: float | None = None
    case_count: int | None = None
    avatar: str | None = None
    intro: str | None = None
    status: str | None = None


class AdminLawyerConsultationItem(BaseModel):
    id: int
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    lawyer_id: int
    lawyer_name: str
    topic: str
    description: str | None = None
    status: str
    scheduled_at: datetime | None = None
    reply: str | None = None
    created_at: datetime


class PaginatedLawyerConsultations(BaseModel):
    total: int
    items: list[AdminLawyerConsultationItem]


class LawyerConsultationAdminUpdate(BaseModel):
    status: str | None = None
    reply: str | None = None


class LawyerConsultationAdminCreate(BaseModel):
    user_id: int
    lawyer_id: int
    topic: str
    description: Optional[str] = None
    status: str = "pending"


class AiUsageSummary(BaseModel):
    total_tokens: int = 0
    total_cost: float = 0
    record_count: int = 0
    user_count: int = 0


class AdminAiUsageItem(BaseModel):
    id: int
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    service_key: str
    service_label: str
    ai_engine: str
    ai_engine_label: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0
    ref_type: str | None = None
    ref_id: str | None = None
    created_at: str | None = None


class AdminAiUsageByUserItem(BaseModel):
    user_id: int
    user_phone: str | None = None
    user_nickname: str | None = None
    total_tokens: int = 0
    total_cost: float = 0
    call_count: int = 0


class PaginatedAiUsage(BaseModel):
    total: int
    items: list[AdminAiUsageItem]
    summary: AiUsageSummary


class PaginatedAiUsageByUser(BaseModel):
    total: int
    items: list[AdminAiUsageByUserItem]
    summary: AiUsageSummary


class AiUsageServiceOption(BaseModel):
    service_key: str
    label: str


class RolePermissionsUpdate(BaseModel):
    matrix: dict[str, dict[str, list[str]]]
