import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.platform_config import AiProviderConfig, SystemSetting
from app.utils.secret_box import decrypt_secret, encrypt_secret, mask_secret

logger = logging.getLogger(__name__)

_settings_cache: dict[str, str] = {}
_ai_cache: dict[str, dict] = {}

# (key, default, category, label, value_type)
CONFIG_DEFAULTS: list[tuple[str, str, str, str, str]] = [
    # general — 常规配置（含 SEO）
    ("platform_name", "得律AI", "general", "平台名称", "string"),
    ("ai_nav_label", "小理AI", "general", "AI 导航名称", "string"),
    ("logo_url", "", "general", "LOGO 图片", "image"),
    ("member_badge_vip_url", "", "general", "VIP 角标图", "image"),
    ("member_badge_svip_url", "", "general", "SVIP 角标图", "image"),
    ("member_badge_enterprise_url", "", "general", "企业版角标图", "image"),
    ("favicon_url", "", "general", "Favicon", "image"),
    ("support_qr_url", "", "general", "客服二维码", "image"),
    ("wechat_official_qr_url", "", "general", "公众号二维码", "image"),
    ("icp_number", "", "general", "ICP 备案号", "string"),
    ("police_icp_number", "", "general", "公安备案号", "string"),
    ("support_phone", "400-000-0000", "general", "客服电话", "string"),
    ("support_email", "support@falitong.com", "general", "客服邮箱", "string"),
    ("company_address", "", "general", "公司地址", "string"),
    ("site_title", "得律AI - 多模态法律 AI 智能服务平台", "general", "SEO 标题", "string"),
    ("site_keywords", "法律AI,法规检索,合同审查,文书生成", "general", "SEO 关键词", "string"),
    ("site_description", "得律AI提供 AI 法律咨询、法规案例检索、合同审查与文书生成服务", "general", "SEO 描述", "text"),
    ("og_image", "", "general", "分享预览图", "image"),
    # basic — 基础配置（运维/能力）
    ("email_enabled", "false", "email", "启用邮件", "boolean"),
    ("smtp_host", "", "email", "SMTP 主机", "string"),
    ("smtp_port", "465", "email", "SMTP 端口", "number"),
    ("smtp_user", "", "email", "SMTP 用户名", "string"),
    ("smtp_password", "", "email", "SMTP 密码", "secret"),
    ("smtp_from", "", "email", "发件人地址", "string"),
    ("smtp_use_tls", "true", "email", "启用 TLS", "boolean"),
    ("upload_active_provider", "local", "basic", "当前存储方式", "string"),
    ("upload_max_size_mb", "10", "basic", "单文件上限(MB)", "number"),
    ("upload_allowed_types", "jpg,jpeg,png,gif,webp,pdf,doc,docx,xls,xlsx,txt", "basic", "允许文件类型", "string"),
    # storage — 对象存储（在服务集成配置）
    ("aliyun_oss_access_key_id", "", "storage", "阿里云 AccessKey ID", "secret"),
    ("aliyun_oss_access_key_secret", "", "storage", "阿里云 AccessKey Secret", "secret"),
    ("aliyun_oss_region", "oss-cn-hangzhou", "storage", "阿里云 Region", "string"),
    ("aliyun_oss_endpoint", "", "storage", "阿里云 Endpoint", "string"),
    ("aliyun_oss_bucket", "", "storage", "阿里云 Bucket", "string"),
    ("aliyun_oss_base_url", "", "storage", "阿里云自定义域名", "string"),
    ("tencent_cos_secret_id", "", "storage", "腾讯云 SecretId", "secret"),
    ("tencent_cos_secret_key", "", "storage", "腾讯云 SecretKey", "secret"),
    ("tencent_cos_region", "ap-guangzhou", "storage", "腾讯云 Region", "string"),
    ("tencent_cos_bucket", "", "storage", "腾讯云 Bucket", "string"),
    ("tencent_cos_base_url", "", "storage", "腾讯云自定义域名", "string"),
    ("qiniu_access_key", "", "storage", "七牛云 AccessKey", "secret"),
    ("qiniu_secret_key", "", "storage", "七牛云 SecretKey", "secret"),
    ("qiniu_bucket", "", "storage", "七牛云空间名", "string"),
    ("qiniu_region", "z0", "storage", "七牛云存储区域", "string"),
    ("qiniu_domain", "", "storage", "七牛云访问域名", "string"),
    ("cache_provider", "redis", "basic", "缓存类型", "string"),
    ("redis_url", "", "basic", "Redis 连接 URL", "string"),
    ("cache_default_ttl_seconds", "3600", "basic", "默认缓存 TTL(秒)", "number"),
    ("access_token_expire_minutes", "10080", "basic", "Access Token 有效期(分钟，管理员无操作登出上限)", "number"),
    ("refresh_token_expire_days", "30", "basic", "Refresh Token 有效期(天)", "number"),
    ("login_fail_lock_count", "5", "basic", "登录失败锁定次数", "number"),
    ("admin_session_idle_minutes", "30", "basic", "管理员闲置退出(分钟)", "number"),
    # auth — 登录注册方式
    ("auth_login_phone_enabled", "true", "auth", "启用手机号登录", "boolean"),
    ("auth_login_phone_sms_enabled", "true", "auth", "启用手机号验证码登录", "boolean"),
    ("auth_login_email_enabled", "true", "auth", "启用邮箱登录", "boolean"),
    ("auth_login_email_sms_enabled", "true", "auth", "启用邮箱验证码登录", "boolean"),
    ("auth_login_wechat_enabled", "true", "auth", "启用微信登录", "boolean"),
    ("auth_login_douyin_enabled", "true", "auth", "启用抖音登录（tt.login + code2session）", "boolean"),
    ("auth_register_phone_enabled", "true", "auth", "启用手机号注册", "boolean"),
    ("auth_register_email_enabled", "true", "auth", "启用邮箱注册", "boolean"),
    ("auth_invite_code_enabled", "true", "auth", "启用邀请码", "boolean"),
    ("auth_require_phone_bind", "false", "auth", "强制绑定手机号（登录后未绑定则限制业务功能）", "boolean"),
    ("auth_require_email_bind", "false", "auth", "强制绑定邮箱（登录后未绑定则限制业务功能）", "boolean"),
    ("email_code_expire_seconds", "600", "auth", "邮箱验证码有效期(秒)", "number"),
    ("email_code_rate_limit_seconds", "60", "auth", "邮箱验证码发送间隔(秒)", "number"),
    ("email_code_max_failures", "5", "auth", "邮箱验证码最大失败次数", "number"),
    ("email_code_fail_window_seconds", "900", "auth", "邮箱验证码失败计数窗口(秒)", "number"),
    ("app_version", "1.0.0", "basic", "当前版本号", "string"),
    ("force_update", "false", "basic", "强制更新", "boolean"),
    ("update_message", "", "basic", "更新说明", "text"),
    ("download_url_android", "", "basic", "Android 下载地址", "string"),
    ("download_url_ios", "", "basic", "iOS 下载地址", "string"),
    ("feature_voice_enabled", "true", "basic", "语音对话", "boolean"),
    ("voice_asr_provider", "mimo_asr", "voice", "语音识别引擎(mimo_asr|paraformer)", "string"),
    ("voice_tts_provider", "cosyvoice", "voice", "语音合成引擎(mimo_tts|cosyvoice)", "string"),
    ("feature_video_enabled", "true", "basic", "视频对话", "boolean"),
    ("feature_esign_enabled", "true", "basic", "电子签章", "boolean"),
    ("ai_mock_enabled", "false", "basic", "开发模式", "boolean"),
    ("free_daily_chat_quota", "5", "basic", "免费用户每日咨询次数", "number"),
    ("search_es_min_hits", "3", "basic", "ES 命中条数阈值", "number"),
    ("search_es_min_score", "1.0", "basic", "ES 最低相关分", "number"),
    ("search_farui_enabled", "true", "basic", "法睿检索回填", "boolean"),
    ("semantic_cache_enabled", "true", "basic", "语义缓存", "boolean"),
    ("semantic_cache_ttl_seconds", "86400", "basic", "语义缓存 TTL(秒)", "number"),
    ("search_llm_summary_enabled", "true", "basic", "检索 LLM 摘要", "boolean"),
    ("content_moderation_enabled", "false", "basic", "内容安全审核", "boolean"),
    ("pii_mask_enabled", "true", "basic", "PII 脱敏", "boolean"),
    ("history_retention_days_free", "7", "basic", "免费用户历史保留(天)", "number"),
    # sms — 短信（阿里云 + 腾讯云）
    ("sms_active_provider", "aliyun", "sms", "当前启用渠道", "string"),
    ("sms_code_expire_seconds", "300", "sms", "验证码有效期(秒)", "number"),
    ("sms_rate_limit_seconds", "60", "sms", "发送间隔(秒)", "number"),
    ("sms_code_max_failures", "5", "sms", "验证码最大失败次数", "number"),
    ("sms_code_fail_window_seconds", "900", "sms", "验证码失败计数窗口(秒)", "number"),
    ("aliyun_sms_access_key_id", "", "sms", "阿里云 AccessKeyId", "secret"),
    ("aliyun_sms_access_key_secret", "", "sms", "阿里云 AccessKeySecret", "secret"),
    ("aliyun_sms_sign_name", "", "sms", "阿里云 SignName", "string"),
    ("aliyun_sms_tpl_login", "", "sms", "阿里云 TemplateCode-登录", "string"),
    ("aliyun_sms_tpl_register", "", "sms", "阿里云 TemplateCode-注册", "string"),
    ("aliyun_sms_tpl_reset_password", "", "sms", "阿里云 TemplateCode-找回密码", "string"),
    ("aliyun_sms_tpl_bind_phone", "", "sms", "阿里云 TemplateCode-绑定手机", "string"),
    ("tencent_sms_secret_id", "", "sms", "腾讯云 SecretId", "secret"),
    ("tencent_sms_secret_key", "", "sms", "腾讯云 SecretKey", "secret"),
    ("tencent_sms_sdk_app_id", "", "sms", "腾讯云 SmsSdkAppId", "string"),
    ("tencent_sms_sign_name", "", "sms", "腾讯云 SignName", "string"),
    ("tencent_sms_region", "ap-guangzhou", "sms", "腾讯云 Region", "string"),
    ("tencent_sms_template_param_count", "2", "sms", "腾讯云 TemplateParamSet 个数", "string"),
    ("tencent_sms_tpl_login", "", "sms", "腾讯云 TemplateId-登录", "string"),
    ("tencent_sms_tpl_register", "", "sms", "腾讯云 TemplateId-注册", "string"),
    ("tencent_sms_tpl_reset_password", "", "sms", "腾讯云 TemplateId-找回密码", "string"),
    ("tencent_sms_tpl_bind_phone", "", "sms", "腾讯云 TemplateId-绑定手机", "string"),
    # payment — 支付（按渠道）
    ("balance_pay_enabled", "true", "payment", "启用余额支付", "boolean"),
    ("wechat_pay_enabled", "false", "payment", "启用微信支付", "boolean"),
    ("wechat_pay_app_id", "", "payment", "微信 AppID", "string"),
    ("wechat_mch_id", "", "payment", "微信商户号", "string"),
    ("wechat_api_v3_key", "", "payment", "APIv3 密钥", "secret"),
    ("wechat_cert_serial_no", "", "payment", "商户证书序列号", "string"),
    ("wechat_mch_private_key", "", "payment", "商户私钥(PEM)", "secret"),
    ("wechat_pay_notify_url", "", "payment", "微信支付回调 URL", "string"),
    ("wechat_platform_cert_pem", "", "payment", "微信支付平台证书(PEM)", "text"),
    ("wechat_pay_public_key_pem", "", "payment", "微信支付公钥(PEM)", "text"),
    ("wechat_pay_public_key_id", "", "payment", "微信支付公钥 ID", "string"),
    ("alipay_enabled", "false", "payment", "启用支付宝", "boolean"),
    ("alipay_app_id", "", "payment", "支付宝 AppID", "string"),
    ("alipay_private_key", "", "payment", "应用私钥(RSA2)", "secret"),
    ("alipay_public_key", "", "payment", "支付宝公钥", "text"),
    ("alipay_notify_url", "", "payment", "支付宝回调 URL", "string"),
    ("douyin_pay_enabled", "false", "payment", "启用抖音支付", "boolean"),
    ("douyin_pay_app_id", "", "payment", "抖音 AppID", "string"),
    ("douyin_pay_merchant_id", "", "payment", "抖音商户号", "string"),
    ("douyin_pay_salt", "", "payment", "抖音支付 Salt", "secret"),
    ("douyin_pay_token", "", "payment", "抖音支付 Token", "secret"),
    ("douyin_pay_notify_url", "", "payment", "抖音支付回调 URL", "string"),
    # pc / h5 / 小程序 / 原生端 — 平台配置
    ("pc_enabled", "true", "pc", "启用 PC 端", "boolean"),
    ("pc_site_url", "http://localhost:8080", "pc", "PC 站点地址", "string"),
    ("pc_seo_title", "得律AI - 法律咨询、法规检索与合同审查", "pc", "SEO 标题", "string"),
    ("pc_seo_keywords", "得律AI,法律AI,法律咨询,法规检索,案例检索,合同审查,文书生成,类案分析,企业法务", "pc", "SEO 关键词", "string"),
    ("pc_seo_description", "得律AI为个人和企业法务提供法律咨询、法规案例检索、合同审查、文书生成和类案分析。在电脑上注册即可使用全功能演示，生成内容仅供法律信息参考。", "pc", "SEO 描述", "textarea"),
    ("pc_share_title", "得律AI｜法律咨询与合同审查", "pc", "分享标题", "string"),
    ("pc_share_desc", "查法规、审合同、写文书，在电脑工作台一次完成。打开即可注册体验。", "pc", "分享描述", "textarea"),
    ("pc_og_image", "https://app.example.com/og-share.jpg", "pc", "分享预览图（Open Graph）", "image"),
    ("pc_robots", "index, follow", "pc", "Robots 策略", "string"),
    ("pc_baidu_site_verification", "", "pc", "百度站点验证码", "string"),
    ("pc_google_site_verification", "", "pc", "Google 站点验证码", "string"),
    ("pc_redirect_mobile_enabled", "true", "pc", "手机打开电脑站时跳转到 H5", "boolean"),
    ("h5_enabled", "true", "h5", "启用 H5 端", "boolean"),
    ("h5_site_url", "http://localhost:8081", "h5", "H5 站点地址", "string"),
    ("h5_seo_title", "得律AI - 手机上的法律咨询与合同工具", "h5", "SEO 标题", "string"),
    ("h5_seo_keywords", "得律AI,法律咨询,手机法律,法规检索,合同审查,文书生成,企业法务", "h5", "SEO 关键词", "string"),
    ("h5_seo_description", "用手机打开得律AI，可以法律咨询、检索法规案例、审查合同和生成文书。注册即可体验，回答只作法律信息参考，不代替律师意见。", "h5", "SEO 描述", "textarea"),
    ("h5_share_title", "得律AI，法律问题手机上就能办", "h5", "分享标题", "string"),
    ("h5_share_desc", "咨询、查案例、审合同、写文书。打开链接注册即可使用演示。", "h5", "分享描述", "textarea"),
    ("h5_og_image", "https://m.example.com/static/og-share.jpg", "h5", "分享预览图", "image"),
    ("h5_theme_color", "#10b981", "h5", "浏览器主题色", "string"),
    ("h5_apple_touch_icon", "", "h5", "添加到主屏幕图标", "image"),
    ("h5_pwa_name", "", "h5", "PWA / 主屏幕名称", "string"),
    ("h5_robots", "index, follow", "h5", "Robots 策略", "string"),
    ("h5_redirect_desktop_enabled", "true", "h5", "电脑打开手机站时跳转到 PC", "boolean"),
    ("wechat_mp_enabled", "true", "wechat_mp", "启用微信小程序对接", "boolean"),
    ("wechat_mp_app_id", "", "wechat_mp", "小程序 AppID", "string"),
    ("wechat_mp_app_secret", "", "wechat_mp", "小程序 AppSecret", "secret"),
    ("wechat_mp_original_id", "", "wechat_mp", "小程序原始 ID（gh_ 开头）", "string"),
    ("wechat_mp_request_legal_domain", "", "wechat_mp", "request 合法域名（每行一个 https 域名，不含路径）", "textarea"),
    ("wechat_mp_socket_legal_domain", "", "wechat_mp", "socket 合法域名（每行一个 wss 域名，不含路径）", "textarea"),
    ("wechat_mp_upload_legal_domain", "", "wechat_mp", "uploadFile 合法域名（每行一个 https 域名）", "textarea"),
    ("wechat_mp_download_legal_domain", "", "wechat_mp", "downloadFile 合法域名（每行一个 https 域名）", "textarea"),
    ("wechat_mp_udp_legal_domain", "", "wechat_mp", "UDP 合法域名（可选，每行一个）", "textarea"),
    ("wechat_mp_tcp_legal_domain", "", "wechat_mp", "TCP 合法域名（可选，每行一个）", "textarea"),
    ("wechat_mp_business_domain", "", "wechat_mp", "业务域名（webview，每行一个，须 ICP 备案）", "textarea"),
    ("wechat_mp_msg_push_url", "", "wechat_mp", "消息推送 URL", "string"),
    ("wechat_mp_msg_token", "", "wechat_mp", "消息推送 Token", "secret"),
    ("wechat_mp_msg_encoding_aes_key", "", "wechat_mp", "消息推送 EncodingAESKey（43 位）", "secret"),
    ("wechat_mp_msg_encrypt_mode", "safe", "wechat_mp", "消息加解密方式", "string"),
    ("wechat_mp_msg_data_format", "JSON", "wechat_mp", "消息推送数据格式", "string"),
    ("wechat_mp_subscribe_template_ids", "", "wechat_mp", "订阅消息模板 ID（每行一个）", "textarea"),
    ("wechat_mp_env_version", "release", "wechat_mp", "默认打开版本", "string"),
    ("wechat_official_enabled", "true", "wechat_official", "启用微信公众号对接", "boolean"),
    ("wechat_official_app_id", "", "wechat_official", "公众号 AppID", "string"),
    ("wechat_official_app_secret", "", "wechat_official", "公众号 AppSecret", "secret"),
    ("wechat_official_original_id", "", "wechat_official", "公众号原始 ID（gh_ 开头）", "string"),
    ("wechat_official_type", "service", "wechat_official", "公众号类型", "string"),
    ("wechat_official_server_url", "", "wechat_official", "服务器配置 URL", "string"),
    ("wechat_official_token", "", "wechat_official", "服务器配置 Token", "secret"),
    ("wechat_official_encoding_aes_key", "", "wechat_official", "EncodingAESKey（43 位）", "secret"),
    ("wechat_official_encrypt_mode", "safe", "wechat_official", "消息加解密方式", "string"),
    ("wechat_official_oauth_domain", "", "wechat_official", "网页授权域名（不含协议与路径）", "string"),
    ("wechat_official_jsapi_domains", "", "wechat_official", "JS 接口安全域名（每行一个，不含协议）", "textarea"),
    ("wechat_official_ip_whitelist", "", "wechat_official", "IP 白名单（服务器出口 IP，每行一个）", "textarea"),
    ("douyin_mp_enabled", "true", "douyin_mp", "启用抖音小程序", "boolean"),
    ("douyin_mp_app_id", "", "douyin_mp", "小程序 AppID（tt 开头，须与开发者工具一致）", "string"),
    ("douyin_mp_app_secret", "", "douyin_mp", "小程序 AppSecret（仅服务端 code2session，勿泄露）", "secret"),
    ("douyin_mp_app_name", "", "douyin_mp", "小程序名称", "string"),
    ("douyin_mp_original_id", "", "douyin_mp", "小程序原始 ID", "string"),
    ("douyin_mp_sandbox_enabled", "false", "douyin_mp", "使用沙盒环境（code2session 调试）", "boolean"),
    (
        "douyin_mp_server_domain",
        "",
        "douyin_mp",
        "request 合法域名（不含协议与路径，填开放平台域名管理）",
        "string",
    ),
    ("douyin_mp_upload_legal_domain", "", "douyin_mp", "uploadFile 合法域名（每行一个，不含协议）", "textarea"),
    ("douyin_mp_download_legal_domain", "", "douyin_mp", "downloadFile 合法域名（每行一个，不含协议）", "textarea"),
    ("douyin_mp_socket_legal_domain", "", "douyin_mp", "socket 合法域名（每行一个，不含协议）", "textarea"),
    ("douyin_mp_webview_domain", "", "douyin_mp", "webview 业务域名（每行一个，须备案）", "textarea"),
    ("douyin_mp_msg_url", "", "douyin_mp", "消息推送 / 服务器 URL", "string"),
    ("douyin_mp_msg_token", "", "douyin_mp", "消息推送 Token", "secret"),
    ("android_enabled", "true", "android", "启用安卓端", "boolean"),
    ("android_app_name", "", "android", "应用名称", "string"),
    ("android_package_name", "com.falitong.app", "android", "Android 包名", "string"),
    ("android_min_sdk", "21", "android", "最低 Android SDK", "string"),
    ("android_min_version", "1.0.0", "android", "最低支持版本", "string"),
    ("android_latest_version", "1.0.0", "android", "最新版本号", "string"),
    ("android_version_code", "1", "android", "Version Code", "string"),
    ("android_force_update", "false", "android", "强制更新", "boolean"),
    ("android_update_message", "", "android", "更新说明", "textarea"),
    ("android_sha256_cert", "", "android", "签名 SHA-256 指纹", "string"),
    ("android_applink_host", "", "android", "App Links 域名（不含协议）", "string"),
    ("ios_enabled", "true", "ios", "启用 iOS 端", "boolean"),
    ("ios_app_name", "", "ios", "应用名称", "string"),
    ("ios_bundle_id", "com.falitong.app", "ios", "iOS Bundle ID", "string"),
    ("ios_app_store_id", "", "ios", "App Store ID", "string"),
    ("ios_team_id", "", "ios", "Apple Team ID", "string"),
    ("ios_min_version", "1.0.0", "ios", "最低支持版本", "string"),
    ("ios_latest_version", "1.0.0", "ios", "最新版本号", "string"),
    ("ios_build_number", "1", "ios", "Build Number", "string"),
    ("ios_force_update", "false", "ios", "强制更新", "boolean"),
    ("ios_update_message", "", "ios", "更新说明", "textarea"),
    ("ios_universal_link", "", "ios", "Universal Link 域名（不含协议）", "string"),
    # open_api — 在开放 API 页配置
    ("open_api_enabled", "true", "open_api", "启用开放 API", "boolean"),
    ("open_api_rate_limit_per_minute", "60", "open_api", "默认 API 限流(次/分)", "number"),
    ("open_api_chat_unit_price", "0.95", "open_api", "法律咨询单价(元/次)", "number"),
    ("open_api_search_law_unit_price", "0.45", "open_api", "法规检索单价(元/次)", "number"),
    ("open_api_search_case_unit_price", "1.10", "open_api", "案例检索单价(元/次)", "number"),
    ("open_api_search_unit_price", "0.45", "open_api", "检索单价(元/次·兼容)", "number"),
    ("open_api_document_unit_price", "0.85", "open_api", "文书单价(元/次)", "number"),
    ("open_api_analysis_unit_price", "1.20", "open_api", "类案分析单价(元/次)", "number"),
    ("open_api_contract_unit_price", "5.50", "open_api", "合同审查单价(元/次)", "number"),
    ("open_api_contract_extract_unit_price", "4.00", "open_api", "合同抽取单价(元/次)", "number"),
    (
        "open_api_discount_tiers",
        '[{"min_units":0,"discount":1},{"min_units":5000,"discount":0.95},{"min_units":20000,"discount":0.90},{"min_units":100000,"discount":0.85}]',
        "open_api",
        "用量折扣阶梯",
        "json",
    ),
    # legal_page — 用户协议、隐私政策、关于平台、联系我们（管理后台「协议政策」维护）
    ("user_agreement_html", "", "legal_page", "用户协议", "html"),
    ("privacy_policy_html", "", "legal_page", "隐私政策", "html"),
    ("about_platform_html", "", "legal_page", "关于平台", "html"),
    ("contact_us_html", "", "legal_page", "联系我们", "html"),
    ("contract_review_help_html", "", "legal_page", "合同审查使用说明", "html"),
    ("contract_extract_help_html", "", "legal_page", "合同抽取使用说明", "html"),
    # billing — 钱包与积分（P0+）
    ("points_display_name", "法理豆", "billing", "积分展示名称", "string"),
    ("points_default_validity_days", "90", "billing", "积分默认有效期(天)", "number"),
    ("points_to_yuan_rate", "100", "billing", "积分抵扣汇率(积分/元)", "number"),
    ("billing_consume_order", "quota,points,balance", "billing", "扣费顺序", "string"),
    ("refund_clawback_enabled", "true", "billing", "退款扣回积分", "boolean"),
    ("refund_clawback_prefer_balance", "true", "billing", "已用积分优先扣余额", "boolean"),
    ("refund_clawback_allow_negative_lot", "true", "billing", "不足记负积分批次", "boolean"),
    ("register_gift_points", "100", "billing", "新人注册礼包积分", "number"),
    ("checkin_base_points", "5", "billing", "签到基础积分", "number"),
    ("checkin_streak_bonus_per_day", "2", "billing", "连续签到每日加成", "number"),
    ("checkin_max_streak_bonus_days", "7", "billing", "签到加成上限天数", "number"),
    ("referral_first_recharge_points", "200", "billing", "推荐首充奖励积分", "number"),
    ("referral_first_vip_points", "500", "billing", "推荐首购VIP奖励积分", "number"),
    ("referral_reward_delay_hours", "24", "billing", "推荐奖励延迟小时", "number"),
    ("order_pending_timeout_hours", "2", "billing", "待支付订单超时(小时)", "number"),
    ("order_payment_reminder_minutes", "30", "billing", "待支付订单提醒(分钟)", "number"),
    ("referral_register_gift_points", "50", "billing", "填写邀请码奖励积分", "number"),
    ("referral_poster_bg", "", "billing", "邀请海报背景图", "image"),
    ("referral_poster_title", "邀请你一起使用得律AI", "billing", "邀请海报标题", "string"),
    ("referral_poster_subtitle", "注册即可体验法律咨询、检索与文书", "billing", "邀请海报副标题", "string"),
    ("referral_poster_layout", "", "billing", "邀请海报排版", "text"),
    ("membership_default_bonus_points", "0", "billing", "购会员默认赠积分", "number"),
    # push — 消息推送配置
    ("push_auto_enabled", "true", "push", "启用自动推送", "boolean"),
    ("push_channel_site", "true", "push", "站内信渠道", "boolean"),
    ("push_channel_app", "true", "push", "App 推送渠道", "boolean"),
    ("push_channel_email", "false", "push", "邮件推送渠道", "boolean"),
    # ai_chat — 法律咨询回复操作与头像
    ("ai_reply_avatar", "", "ai_chat", "AI 回复头像", "image"),
    ("ai_action_copy", "true", "ai_chat", "显示复制", "boolean"),
    ("ai_action_regenerate", "true", "ai_chat", "显示重新生成", "boolean"),
    ("ai_action_like", "true", "ai_chat", "显示赞", "boolean"),
    ("ai_action_dislike", "true", "ai_chat", "显示踩", "boolean"),
    ("ai_action_speak", "true", "ai_chat", "显示朗读", "boolean"),
    ("ai_action_share", "true", "ai_chat", "显示分享", "boolean"),
]

PUBLIC_SETTING_KEYS = {
    "platform_name", "ai_nav_label", "logo_url",
    "member_badge_vip_url", "member_badge_svip_url", "member_badge_enterprise_url",
    "favicon_url", "support_qr_url", "wechat_official_qr_url",
    "icp_number", "police_icp_number", "support_phone", "support_email", "company_address",
    "site_title", "site_keywords", "site_description", "og_image",
    "pc_enabled", "pc_site_url", "pc_seo_title", "pc_seo_keywords", "pc_seo_description",
    "pc_share_title", "pc_share_desc",
    "pc_og_image",     "pc_robots", "pc_baidu_site_verification", "pc_google_site_verification",
    "pc_redirect_mobile_enabled",
    "h5_enabled", "h5_site_url", "h5_seo_title", "h5_seo_keywords", "h5_seo_description",
    "h5_share_title", "h5_share_desc", "h5_og_image", "h5_theme_color",
    "h5_apple_touch_icon", "h5_pwa_name", "h5_robots", "h5_redirect_desktop_enabled",
    "wechat_mp_enabled", "wechat_mp_app_id", "wechat_mp_original_id", "wechat_mp_env_version",
    "wechat_official_enabled", "wechat_official_app_id", "wechat_official_original_id",
    "wechat_official_type", "wechat_official_oauth_domain",
    "douyin_mp_enabled", "douyin_mp_app_id", "douyin_mp_app_name", "douyin_mp_original_id",
    "douyin_mp_server_domain", "douyin_mp_upload_legal_domain", "douyin_mp_download_legal_domain",
    "douyin_mp_socket_legal_domain", "douyin_mp_webview_domain",
    "app_version", "force_update", "update_message", "download_url_android", "download_url_ios",
    "android_enabled", "android_app_name", "android_package_name", "android_min_sdk",
    "android_min_version", "android_latest_version", "android_version_code",
    "android_force_update", "android_update_message", "android_applink_host",
    "ios_enabled", "ios_app_name", "ios_bundle_id", "ios_app_store_id",
    "ios_min_version", "ios_latest_version", "ios_build_number",
    "ios_force_update", "ios_update_message", "ios_universal_link",
    "feature_voice_enabled", "feature_video_enabled", "feature_esign_enabled",
    "wechat_pay_enabled", "alipay_enabled", "douyin_pay_enabled", "balance_pay_enabled",
    "open_api_enabled",
    "auth_login_phone_enabled", "auth_login_phone_sms_enabled",
    "auth_login_email_enabled", "auth_login_email_sms_enabled",
    "auth_login_wechat_enabled",
    "auth_login_douyin_enabled",
    "auth_register_phone_enabled", "auth_register_email_enabled", "auth_invite_code_enabled",
    "auth_require_phone_bind", "auth_require_email_bind",
    "points_display_name",
}

IMAGE_SETTING_KEYS = {
    "logo_url", "favicon_url", "og_image", "support_qr_url", "wechat_official_qr_url",
    "referral_poster_bg",
    "ai_reply_avatar",
    "member_badge_vip_url", "member_badge_svip_url", "member_badge_enterprise_url",
    "pc_og_image", "h5_og_image", "h5_apple_touch_icon",
}

SECRET_KEYS = {k for k, _, _, _, vt in CONFIG_DEFAULTS if vt == "secret"}

# 会话/安全策略：后台保存后须各 worker 立即读到新值
SESSION_POLICY_KEYS = frozenset({
    "access_token_expire_minutes",
    "refresh_token_expire_days",
    "admin_session_idle_minutes",
    "login_fail_lock_count",
})

RUNTIME_TOGGLE_KEYS = frozenset({
    "ai_mock_enabled",
    "feature_voice_enabled",
    "feature_video_enabled",
    "feature_esign_enabled",
    "wechat_pay_enabled",
    "alipay_enabled",
    "douyin_pay_enabled",
    "balance_pay_enabled",
})

EMAIL_RUNTIME_KEYS = frozenset({
    "email_enabled",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_from",
    "smtp_use_tls",
})

EMAIL_SETTING_KEYS = EMAIL_RUNTIME_KEYS | {"smtp_password"}

# (code, name, category, description, base_url, api_key, api_secret, extra_json)
INTEGRATION_DEFAULTS: list[tuple] = [
    (
        "farui",
        "通义法睿 API",
        "ai",
        "阿里云百炼·法睿 OpenAPI（ROA 签名，非 DashScope Bearer）",
        "https://farui.cn-beijing.aliyuncs.com",
        None,
        None,
        '{"workspace_id":"","region_id":"cn-beijing","endpoint":"farui.cn-beijing.aliyuncs.com"}',
    ),
    ("deepseek", "DeepSeek API", "ai", "复杂推理 Chat Completions", "https://api.deepseek.com/v1", None, None, '{"model":"deepseek-chat"}'),
    ("qwen_vl", "Qwen-VL", "ai", "多模态视觉理解", "https://dashscope.aliyuncs.com/api/v1", None, None, '{"model":"qwen-vl-max"}'),
    ("paraformer", "Paraformer", "voice", "语音识别 ASR（DashScope 实时 WebSocket，仅 API Key）", "https://dashscope.aliyuncs.com/api/v1", None, None, '{"model":"paraformer-realtime-v2"}'),
    (
        "mimo_asr",
        "小米 MiMo ASR",
        "voice",
        "语音识别 MiMo-V2.5-ASR（OpenAI 兼容）",
        "https://api.xiaomimimo.com/v1",
        None,
        None,
        '{"model":"mimo-v2.5-asr","language":"zh"}',
    ),
    (
        "mimo_tts",
        "小米 MiMo TTS",
        "voice",
        "语音合成 MiMo-V2.5-TTS（OpenAI 兼容）",
        "https://api.xiaomimimo.com/v1",
        None,
        None,
        '{"model":"mimo-v2.5-tts","voice":"冰糖","format":"wav","style":"专业、清晰、沉稳的中文普通话，适合法律咨询场景，语速适中。"}',
    ),
    ("cosyvoice", "CosyVoice", "voice", "语音合成 TTS（DashScope WebSocket，仅 API Key）", "https://dashscope.aliyuncs.com/api/v1", None, None, '{"model":"cosyvoice-v3-flash","voice":"longanyang"}'),
    ("artc", "阿里云 ARTC", "av", "直播控制台 AppId 与 AppKey，服务端按 SHA256 签发入会 Token", "", None, None, '{"app_id":"","app_key":"","token_expire":3600}'),
    ("lingjing", "灵境数字人", "av", "工单参数：租户 ID、交互配置 ID、鉴权 AK、鉴权 SK。由阿里云实时工作流数字人节点使用", "", None, None, '{"tenant_id":"","interaction_config_id":"","access_key":"","access_secret":""}'),
    ("unipush", "uni-push 2.0", "push", "个推 REST v2：AppId、AppKey、MasterSecret，先 POST /auth 换 token", "https://restapi.getui.com/v2", None, None, '{"app_key":""}'),
    ("esign", "e签宝", "esign", "AppId 与 AppSecret，先 GET /v1/oauth2/access_token", "https://openapi.esign.cn", None, None, "{}"),
]


def invalidate_cache() -> None:
    _settings_cache.clear()
    _ai_cache.clear()
    try:
        from app.core.redis import reset_redis_client
        reset_redis_client()
    except Exception:
        pass


def feature_enabled(db: Session, key: str, default: bool = True) -> bool:
    raw = (get_setting(db, key, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_setting(db: Session, key: str, default: str | None = None) -> str | None:
    # 密钥与会话策略不进程内缓存，避免多 worker 下后台保存后其它 worker 仍用旧值
    no_cache = key in SECRET_KEYS or key in SESSION_POLICY_KEYS or key in EMAIL_RUNTIME_KEYS or key in RUNTIME_TOGGLE_KEYS
    if not no_cache and key in _settings_cache:
        return _settings_cache[key]
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row and row.value is not None:
        if not no_cache:
            _settings_cache[key] = row.value
        return row.value
    return default


def get_platform_name(db: Session) -> str:
    return (get_setting(db, "platform_name") or "").strip()


def get_ai_nav_label(db: Session) -> str:
    return (get_setting(db, "ai_nav_label") or "").strip()


def get_bool_setting(db: Session, key: str, default: bool = False) -> bool:
    val = get_setting(db, key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def safe_decrypt_secret(value: str | None) -> str:
    """解密失败时返回空字符串，避免一项坏密钥拖垮设置页和健康检查。"""
    if not value:
        return ""
    token = value[4:] if value.startswith("enc:") else value
    if not token.startswith("v2:"):
        return "" if value.startswith("enc:") else value
    try:
        return decrypt_secret(token)
    except Exception:
        logger.warning("secret decrypt failed")
        return ""


def decrypt_setting_value(value: str) -> str:
    return safe_decrypt_secret(value)


def encrypt_setting_value(value: str) -> str:
    if not value:
        return ""
    return "enc:" + encrypt_secret(value)


def _json_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value.encode("utf-8", "replace").decode("utf-8")


def _mask_setting_value(key: str, value: str | None) -> str | None:
    if not value or key not in SECRET_KEYS:
        return _json_text(value)
    try:
        plain = decrypt_setting_value(value)
    except Exception:
        logger.warning("setting %s cannot be decrypted, ask admin to save it again", key)
        return "******"
    return mask_secret(plain) if plain else ""


def get_public_settings(db: Session) -> dict[str, str]:
    from app.services.storage_service import public_base_url
    from app.utils.file_tokens import refresh_signed_file_url
    from app.utils.public_url import ensure_https_asset_url, normalize_public_base

    base = public_base_url(db)
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(PUBLIC_SETTING_KEYS)).all()
    out: dict[str, str] = {}
    for r in rows:
        if r.key not in PUBLIC_SETTING_KEYS:
            continue
        val = r.value or ""
        if r.key == "pc_site_url":
            val = normalize_public_base(val)
        elif r.key in IMAGE_SETTING_KEYS:
            val = refresh_signed_file_url(val, public_base=base)
            val = ensure_https_asset_url(val)
        out[r.key] = val
    return out


def list_settings(db: Session, category: str | None = None) -> list[SystemSetting]:
    q = db.query(SystemSetting)
    if category:
        q = q.filter(SystemSetting.category == category)
    return q.order_by(SystemSetting.category, SystemSetting.key).all()


def list_settings_for_admin(db: Session, category: str | None = None) -> list[dict]:
    from app.services.storage_service import public_base_url
    from app.utils.file_tokens import refresh_signed_file_url

    try:
        base = public_base_url(db)
    except Exception:
        logger.exception("public base url unavailable while listing settings")
        base = ""
    rows = list_settings(db, category)
    existing_keys = {row.key for row in rows}
    result = []
    for row in rows:
        try:
            val = _mask_setting_value(row.key, row.value)
            if row.key in IMAGE_SETTING_KEYS and val:
                val = refresh_signed_file_url(val, public_base=base)
            result.append({
                "key": row.key,
                "value": val,
                "category": _json_text(row.category) or "basic",
                "label": _json_text(row.label),
                "value_type": _json_text(row.value_type) or "string",
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "is_secret": row.key in SECRET_KEYS,
            })
        except Exception:
            logger.exception("skip unreadable setting key=%s", row.key)
    if category:
        for key, value, cat, label, value_type in CONFIG_DEFAULTS:
            if cat != category or key in existing_keys:
                continue
            result.append({
                "key": key,
                "value": value,
                "category": cat,
                "label": label,
                "value_type": value_type,
                "updated_at": None,
                "is_secret": key in SECRET_KEYS,
            })
    return result


def upsert_settings(db: Session, items: list[dict], operator_id: int | None = None) -> list[SystemSetting]:
    from app.services.audit_service import log_action

    updated: list[SystemSetting] = []
    for item in items:
        key = item["key"]
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not row:
            row = SystemSetting(key=key, category=item.get("category", "basic"))
            db.add(row)
        raw_value = str(item.get("value", "")).strip() if key in SECRET_KEYS else str(item.get("value", ""))
        if key in SECRET_KEYS:
            if raw_value and "****" not in raw_value:
                row.value = encrypt_setting_value(raw_value)
            elif not row.value:
                row.value = ""
        else:
            if key.endswith("_html") or item.get("value_type") == "html":
                from app.utils.sanitize_html import sanitize_html

                row.value = sanitize_html(raw_value)
            else:
                row.value = raw_value
            if key in IMAGE_SETTING_KEYS and row.value:
                from app.utils.file_tokens import normalize_stored_file_ref

                row.value = normalize_stored_file_ref(row.value)
        if item.get("value_type"):
            row.value_type = item["value_type"]
        if item.get("label"):
            row.label = item["label"]
        if item.get("category"):
            row.category = item["category"]
        updated.append(row)
    db.commit()
    invalidate_cache()
    if operator_id:
        log_action(db, user_id=operator_id, action="update_settings", resource="system_settings", detail={"keys": [i["key"] for i in items]})
    return updated


def list_ai_providers(db: Session, category: str | None = None) -> list[dict]:
    q = db.query(AiProviderConfig).order_by(AiProviderConfig.category, AiProviderConfig.id)
    if category:
        q = q.filter(AiProviderConfig.category == category)
    rows = q.all()
    result = []
    for r in rows:
        plain = safe_decrypt_secret(r.api_key_enc)
        secret_plain = safe_decrypt_secret(r.api_secret_enc)
        result.append({
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "category": r.category or "ai",
            "description": r.description,
            "api_key_masked": mask_secret(plain),
            "api_secret_masked": mask_secret(secret_plain) if secret_plain else "",
            "has_api_key": bool(plain),
            "has_api_secret": r.code == "farui" or bool(secret_plain),
            "base_url": r.base_url,
            "extra_json": r.extra_json or "{}",
            "enabled": r.enabled,
            "daily_limit": r.daily_limit,
            "call_count_today": r.call_count_today,
            "updated_at": r.updated_at,
        })
    return result


def get_integration(db: Session, code: str) -> dict | None:
    cache_key = f"int:{code}"
    if cache_key in _ai_cache:
        return _ai_cache[cache_key]
    row = db.query(AiProviderConfig).filter(AiProviderConfig.code == code).first()
    if not row or not row.enabled:
        return None
    extra = {}
    if row.extra_json:
        try:
            extra = json.loads(row.extra_json)
        except json.JSONDecodeError:
            extra = {}
    cfg = {
        "code": row.code,
        "api_key": safe_decrypt_secret(row.api_key_enc) or None,
        "api_secret": safe_decrypt_secret(row.api_secret_enc) or None,
        "base_url": row.base_url,
        "extra": extra,
        "enabled": row.enabled,
    }
    _ai_cache[cache_key] = cfg
    return cfg


def get_ai_provider_key(db: Session, code: str) -> str | None:
    cfg = get_integration(db, code)
    return cfg.get("api_key") if cfg else None


def get_ai_base_url(db: Session, code: str, env_default: str) -> str:
    cfg = get_integration(db, code)
    if cfg and cfg.get("base_url"):
        return cfg["base_url"]
    return env_default


def update_ai_provider(db: Session, provider_id: int, data: dict, operator_id: int | None = None) -> AiProviderConfig:
    from app.services.audit_service import log_action

    row = db.query(AiProviderConfig).filter(AiProviderConfig.id == provider_id).first()
    if not row:
        raise ValueError("AI 接口不存在")
    if "name" in data and data["name"]:
        row.name = data["name"]
    if "base_url" in data:
        row.base_url = data["base_url"]
    if "enabled" in data:
        row.enabled = data["enabled"]
    if "daily_limit" in data:
        row.daily_limit = data["daily_limit"]
    if "description" in data:
        row.description = data["description"]
    if "extra_json" in data:
        row.extra_json = data["extra_json"]
    if data.get("api_key"):
        row.api_key_enc = encrypt_secret(data["api_key"])
    if data.get("api_secret"):
        row.api_secret_enc = encrypt_secret(data["api_secret"])
    db.commit()
    db.refresh(row)
    invalidate_cache()
    if operator_id:
        log_action(db, user_id=operator_id, action="update_ai_provider", resource="ai_provider", resource_id=str(provider_id), detail={"code": row.code})
    return row


async def test_ai_provider(db: Session, provider_id: int) -> dict:
    import time

    import httpx

    from app.services.integration_config import ai_mock_enabled

    row = db.query(AiProviderConfig).filter(AiProviderConfig.id == provider_id).first()
    if not row:
        raise ValueError("服务集成不存在")
    api_key = safe_decrypt_secret(row.api_key_enc)
    api_secret = safe_decrypt_secret(row.api_secret_enc)

    from commercial.services.integration_probe import PROBE_CODES, probe_provider

    if row.code in PROBE_CODES:
        result = await probe_provider(db, row.code, require_enabled=False)
        return {
            "success": bool(result.get("ok")),
            "latency_ms": int(result.get("latency_ms") or 0),
            "message": result.get("detail") or "",
        }

    if row.category in ("storage", "sms", "push", "esign", "av", "voice"):
        configured = bool(api_key or api_secret or row.extra_json)
        if configured or ai_mock_enabled(db):
            return {"success": True, "latency_ms": 0, "message": f"{row.name} 配置已就绪（Mock/已填参）"}
        return {"success": False, "latency_ms": 0, "message": "请填写 API Key / Secret 或扩展参数"}

    if not api_key and ai_mock_enabled(db):
        return {"success": True, "latency_ms": 0, "message": "Mock 模式，未配置 Key 也可使用"}
    if not api_key:
        return {"success": False, "latency_ms": 0, "message": "未配置 API Key"}
    start = time.perf_counter()

    if row.code == "farui":
        import json as _json

        from commercial.services.ai import farui_sdk
        from app.services.integration_config import ai_mock_enabled

        extra = {}
        try:
            extra = _json.loads(row.extra_json or "{}")
        except _json.JSONDecodeError:
            pass
        if ai_mock_enabled(db) and not api_secret:
            return {"success": True, "latency_ms": 0, "message": "Mock 模式"}
        if api_key.startswith("sk-") and not api_secret:
            return {
                "success": False,
                "latency_ms": 0,
                "message": "检测到 DashScope API Key（sk- 开头）。法睿 OpenAPI 需 RAM AccessKey ID（LTAI）+ Secret，见 deploy/FARUI.md",
            }
        c = farui_sdk.resolve_config(db)
        latency = int((time.perf_counter() - start) * 1000)
        if not c.get("enabled"):
            return {
                "success": False,
                "latency_ms": latency,
                "message": "通义法睿未启用：请打开编辑弹窗中的「启用」开关并保存",
            }
        if c.get("mock"):
            from app.core.ai_config import ai_mock_block_reason

            reason = ai_mock_block_reason(c.get("access_key_id"), db) or "AI Mock 已开启"
            return {
                "success": False,
                "latency_ms": latency,
                "message": f"已开启 AI Mock：{reason}。关闭后重试测试连接",
            }
        missing = []
        if not c.get("access_key_id"):
            missing.append("AccessKey ID")
        if not c.get("access_key_secret"):
            missing.append("AccessKey Secret")
        wid = (c.get("workspace_id") or extra.get("workspace_id") or extra.get("workspaceId") or "").strip()
        if not wid:
            missing.append("workspace_id")
        if missing:
            return {
                "success": False,
                "latency_ms": latency,
                "message": "缺少: " + ", ".join(missing),
            }
        try:
            farui_sdk.create_client(c)
            latency = int((time.perf_counter() - start) * 1000)
            ep = c.get("endpoint") or "farui.cn-beijing.aliyuncs.com"
            return {
                "success": True,
                "latency_ms": latency,
                "message": f"法睿 SDK 就绪（{ep}，workspace={c.get('workspace_id', '')[:12]}…）",
            }
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return {"success": False, "latency_ms": latency, "message": str(e)}

    base = row.base_url or "https://api.deepseek.com/v1"
    url = f"{base.rstrip('/')}/models" if "deepseek" in row.code else base
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        latency = int((time.perf_counter() - start) * 1000)
        ok = resp.status_code < 500
        return {"success": ok, "latency_ms": latency, "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        latency = int((time.perf_counter() - start) * 1000)
        return {"success": False, "latency_ms": latency, "message": str(e)}


def _migrate_legacy_settings(db: Session) -> None:
    """迁移旧配置键与分类，保证升级兼容。"""
    copy_map = [
        ("sms_access_key_id", "aliyun_sms_access_key_id"),
        ("sms_access_key_secret", "aliyun_sms_access_key_secret"),
        ("sms_sign_name", "aliyun_sms_sign_name"),
        ("sms_template_code", "aliyun_sms_tpl_login"),
        ("wechat_app_id", "wechat_pay_app_id"),
        ("douyin_app_id", "douyin_pay_app_id"),
        ("wechat_pay_api_key", "wechat_api_v3_key"),
        ("oss_access_key_id", "aliyun_oss_access_key_id"),
        ("oss_access_key_secret", "aliyun_oss_access_key_secret"),
        ("oss_bucket", "aliyun_oss_bucket"),
        ("oss_endpoint", "aliyun_oss_endpoint"),
        ("oss_base_url", "aliyun_oss_base_url"),
    ]
    for old_key, new_key in copy_map:
        old_row = db.query(SystemSetting).filter(SystemSetting.key == old_key).first()
        new_row = db.query(SystemSetting).filter(SystemSetting.key == new_key).first()
        if old_row and new_row and old_row.value and not (new_row.value or "").strip():
            new_row.value = old_row.value

    provider_row = db.query(SystemSetting).filter(SystemSetting.key == "upload_provider").first()
    active_row = db.query(SystemSetting).filter(SystemSetting.key == "upload_active_provider").first()
    if provider_row and active_row and provider_row.value and not (active_row.value or "").strip():
        legacy = provider_row.value.lower()
        active_row.value = "aliyun" if legacy in ("oss", "aliyun") else "local"

    category_migrate = {
        "seo": "general",
        "upload": "basic",
        "cache": "basic",
        "security": "basic",
        "version": "basic",
        "feature": "basic",
        "billing": "basic",
    }
    for old_cat, new_cat in category_migrate.items():
        db.query(SystemSetting).filter(SystemSetting.category == old_cat).update(
            {SystemSetting.category: new_cat}, synchronize_session=False
        )

    for key in ("wechat_official_app_id", "wechat_official_app_secret"):
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row and row.category == "wechat_mp":
            row.category = "wechat_official"
            meta = next((item for item in CONFIG_DEFAULTS if item[0] == key), None)
            if meta:
                row.label = meta[3]
                row.value_type = meta[4]

    for key in EMAIL_SETTING_KEYS:
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row and row.category != "email":
            row.category = "email"

    idle = db.query(SystemSetting).filter(SystemSetting.key == "admin_session_idle_minutes").first()
    if idle:
        idle.label = "管理员闲置退出(分钟)"
        if (idle.value or "").strip() in ("", "0"):
            idle.value = "30"

    mock_row = db.query(SystemSetting).filter(SystemSetting.key == "ai_mock_enabled").first()
    if mock_row:
        mock_row.label = "开发模式"

    seo_defaults = {key: value for key, value, *_rest in CONFIG_DEFAULTS if key.startswith(("pc_seo_", "pc_share_", "pc_og_", "h5_seo_", "h5_share_", "h5_og_"))}
    for key, default in seo_defaults.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row and not (row.value or "").strip() and (default or "").strip():
            row.value = default

    label_updates = {k: lbl for k, _, _, lbl, _ in CONFIG_DEFAULTS}
    for row in db.query(SystemSetting).all():
        if row.key in label_updates and not row.label:
            row.label = label_updates[row.key]


def _legal_page_setting_meta(key: str) -> tuple[str, str, str] | None:
    for k, _, category, label, value_type in CONFIG_DEFAULTS:
        if k == key:
            return category, label, value_type
    return None


def _find_setting(db: Session, key: str) -> SystemSetting | None:
    """autoflush 关闭时，未提交的新增行不会出现在查询结果里。"""
    for obj in db.new:
        if isinstance(obj, SystemSetting) and obj.key == key:
            return obj
    return db.query(SystemSetting).filter(SystemSetting.key == key).first()


def _ensure_legal_page_row(db: Session, key: str) -> SystemSetting | None:
    row = _find_setting(db, key)
    if row:
        return row
    meta = _legal_page_setting_meta(key)
    if not meta:
        return None
    category, label, value_type = meta
    row = SystemSetting(key=key, value="", category=category, label=label, value_type=value_type)
    db.add(row)
    db.flush()
    return row


def _seed_legal_pages_if_empty(db: Session) -> None:
    """legal_page 四类正文：库中为空时写入默认模板，不覆盖后台已编辑内容。"""
    sync_legal_pages_from_defaults(db, force=False)


def sync_legal_pages_from_defaults(
    db: Session,
    keys: list[str] | None = None,
    *,
    force: bool = True,
    operator_id: int | None = None,
) -> list[str]:
    """将 legal_page_defaults 中的 HTML 写入 system_settings。force=False 时仅填充空值。"""
    from app.content.legal_page_defaults import LEGAL_PAGE_DEFAULTS
    from app.utils.sanitize_html import sanitize_html

    target_keys = keys or list(LEGAL_PAGE_DEFAULTS.keys())
    updated_keys: list[str] = []
    for key in target_keys:
        html = LEGAL_PAGE_DEFAULTS.get(key)
        if not html:
            continue
        row = _ensure_legal_page_row(db, key)
        if not row:
            continue
        if not force and (row.value or "").strip():
            continue
        row.value = sanitize_html(html)
        updated_keys.append(key)
    if updated_keys:
        db.commit()
        invalidate_cache()
        if operator_id:
            from app.services.audit_service import log_action

            log_action(
                db,
                user_id=operator_id,
                action="sync_legal_pages_defaults",
                resource="system_settings",
                detail={"keys": updated_keys, "force": force},
            )
    return updated_keys


def seed_defaults(db: Session) -> None:
    from sqlalchemy.exc import IntegrityError

    last_error: IntegrityError | None = None
    for _ in range(3):
        try:
            _apply_seed_defaults(db)
            return
        except IntegrityError as exc:
            last_error = exc
            logger.warning("启动配置种子遇到重复键，回滚后重试")
            db.rollback()
    if last_error:
        raise last_error


def _apply_seed_defaults(db: Session) -> None:
    for key, value, category, label, value_type in CONFIG_DEFAULTS:
        existing = _find_setting(db, key)
        if not existing:
            db.add(SystemSetting(
                key=key, value=value, category=category, label=label, value_type=value_type,
            ))
        else:
            if existing.category in ("seo", "email", "upload", "cache", "security", "version", "feature", "billing"):
                pass  # handled by _migrate_legacy_settings
            if not existing.label:
                existing.label = label
            if not existing.value_type or existing.value_type == "string":
                existing.value_type = value_type
    _migrate_legacy_settings(db)
    _seed_legal_pages_if_empty(db)
    ai_defaults = [
        (code, name, cat, desc, base_url, api_key, api_secret, extra)
        for code, name, cat, desc, base_url, api_key, api_secret, extra in INTEGRATION_DEFAULTS
    ]
    for code, name, cat, desc, base_url, api_key, api_secret, extra in ai_defaults:
        existing = db.query(AiProviderConfig).filter(AiProviderConfig.code == code).first()
        if not existing:
            db.add(AiProviderConfig(
                code=code,
                name=name,
                category=cat,
                description=desc,
                base_url=base_url or None,
                api_key_enc=encrypt_secret(api_key) if api_key else None,
                api_secret_enc=encrypt_secret(api_secret) if api_secret else None,
                extra_json=extra or "{}",
                enabled=True,
            ))
        else:
            if not existing.category:
                existing.category = cat
            if not existing.description:
                existing.description = desc
    db.commit()


def get_role_permissions() -> dict:
    from app.core.casbin_enforcer import get_enforcer

    enforcer = get_enforcer()
    roles = ["super_admin", "operator", "content_editor", "viewer"]
    modules = [
        "stats", "users", "content", "push", "plans", "settings", "ai", "orders",
        "enterprise", "conversations", "audit_logs", "banners", "feedbacks", "document_templates", "open_api",
        "legal_search", "legal_contract", "legal_documents", "lawyers",
    ]
    actions = ["read", "write"]
    matrix: dict[str, dict[str, list[str]]] = {}
    for role in roles:
        matrix[role] = {}
        for obj in modules:
            allowed = [act for act in actions if enforcer.enforce(role, obj, act)]
            if allowed:
                matrix[role][obj] = allowed
    return {"roles": roles, "modules": modules, "actions": actions, "matrix": matrix}


def update_role_permissions(matrix: dict[str, dict[str, list[str]]], operator_id: int, db) -> dict:
    from app.core.casbin_enforcer import clear_enforcer_cache, get_enforcer
    from app.services.audit_service import log_action

    enforcer = get_enforcer()
    roles = ["operator", "content_editor", "viewer"]
    modules = [
        "stats", "users", "content", "push", "plans", "settings", "ai", "orders",
        "enterprise", "conversations", "audit_logs", "banners", "feedbacks", "document_templates", "open_api",
        "legal_search", "legal_contract", "legal_documents", "lawyers",
    ]
    actions = ["read", "write"]

    for role in roles:
        enforcer.remove_filtered_policy(0, role)

    for role in roles:
        role_perms = matrix.get(role, {})
        for mod in modules:
            for act in role_perms.get(mod, []):
                if act in actions:
                    enforcer.add_policy(role, mod, act)

    enforcer.save_policy()
    clear_enforcer_cache()
    log_action(
        db,
        user_id=operator_id,
        action="update_role_permissions",
        resource="roles",
        detail={"roles": list(matrix.keys())},
    )
    return get_role_permissions()
