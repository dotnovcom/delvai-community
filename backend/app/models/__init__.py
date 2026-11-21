from app.models.admin import ContentArticle, PushTask
from app.models.admin_account import AdminAccount
from app.models.ai_usage_log import AiUsageLog
from app.models.audit_log import AuditLog
from app.models.cms import Banner, LaunchSplash, UserFeedback
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.platform_config import AiProviderConfig, SystemSetting
from app.models.usage_log import UsageLog
from app.models.user import User
from app.models.user_session import UserSession

try:
    from commercial.models import (  # noqa: F401
        AnalysisReport,
        BillingPrice,
        ComplianceCheck,
        ContractExtract,
        ContractLedger,
        ContractReview,
        DocumentTemplate,
        ESignRecord,
        Enterprise,
        EnterpriseCaseAnalysis,
        EnterpriseKnowledgeDoc,
        EnterpriseMember,
        EnterpriseUsageLog,
        GeneratedDocument,
        IPMonitor,
        Lawyer,
        LawyerConsultation,
        LegalCacheLog,
        MembershipPlan,
        OpenApiKey,
        Order,
        Payment,
        PointsLedger,
        PointsLot,
        Receivable,
        RechargePackage,
        ReferralPendingReward,
        ReferralRecord,
        UserCheckin,
        UserMembership,
        UserSearchHistory,
        UserWallet,
        WalletTransaction,
    )
except ImportError:
    pass
