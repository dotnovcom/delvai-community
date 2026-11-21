"""从数据库读取第三方集成与系统运行时配置（唯一标准，不写死在业务代码）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services import config_service
from app.services.runtime_config import get_bool, get_int, get_secret, get_str


def _session(db: Session | None) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    return SessionLocal(), True


def get_ai_integration(db: Session | None, code: str) -> dict:
    """AiProvider 表：api_key / api_secret / base_url / extra / enabled。"""
    session, close = _session(db)
    try:
        cfg = config_service.get_integration(session, code)
        if not cfg:
            return {"code": code, "enabled": False, "api_key": None, "api_secret": None, "base_url": "", "extra": {}}
        return {
            "code": code,
            "enabled": bool(cfg.get("enabled")),
            "api_key": cfg.get("api_key"),
            "api_secret": cfg.get("api_secret"),
            "base_url": (cfg.get("base_url") or "").rstrip("/"),
            "extra": cfg.get("extra") or {},
        }
    finally:
        if close:
            session.close()


def balance_pay_enabled(db: Session) -> bool:
    return get_bool(db, "balance_pay_enabled", True)


def assert_balance_pay_enabled(db: Session) -> None:
    if not balance_pay_enabled(db):
        raise ValueError("余额支付未开通")


def assert_online_pay_enabled(db: Session, platform: str) -> None:
    """在线支付渠道关闭时拒绝下单。余额抵扣把应付现金降为 0 时不走这里。"""
    if platform in ("corporate",):
        return
    flags = {
        "wechat": ("wechat_pay_enabled", "微信支付"),
        "alipay": ("alipay_enabled", "支付宝"),
        "douyin": ("douyin_pay_enabled", "抖音支付"),
    }
    item = flags.get(platform)
    if not item:
        raise ValueError("不支持的支付方式")
    key, label = item
    if not get_bool(db, key, False):
        raise ValueError(f"{label}未开通")


def ai_mock_enabled(db: Session | None = None) -> bool:
    session, close = _session(db)
    try:
        return get_bool(session, "ai_mock_enabled", False)
    finally:
        if close:
            session.close()


def get_wechat_pay_config(db: Session | None = None) -> dict:
    session, close = _session(db)
    try:
        return {
            "enabled": get_bool(session, "wechat_pay_enabled"),
            "app_id": get_str(session, "wechat_pay_app_id"),
            "mch_id": get_str(session, "wechat_mch_id"),
            "api_v3_key": get_secret(session, "wechat_api_v3_key"),
            "cert_serial_no": get_str(session, "wechat_cert_serial_no"),
            "mch_private_key": get_secret(session, "wechat_mch_private_key"),
            "notify_url": get_str(session, "wechat_pay_notify_url"),
            "platform_cert_pem": get_str(session, "wechat_platform_cert_pem"),
            "pay_public_key_pem": get_str(session, "wechat_pay_public_key_pem"),
            "pay_public_key_id": get_str(session, "wechat_pay_public_key_id"),
        }
    finally:
        if close:
            session.close()


_WECHAT_PREPAY_CHECKS: tuple[tuple[str, str], ...] = (
    ("enabled", "启用微信支付"),
    ("app_id", "微信 AppID"),
    ("mch_id", "微信商户号"),
    ("api_v3_key", "APIv3 密钥"),
    ("cert_serial_no", "商户证书序列号"),
    ("mch_private_key", "商户私钥(PEM)"),
    ("notify_url", "支付回调 URL"),
)

_WECHAT_NOTIFY_CHECKS: tuple[tuple[str, str], ...] = (
    ("platform_cert_pem", "微信支付平台证书(PEM)"),
    ("pay_public_key_pem", "微信支付公钥(PEM)"),
)


def _cfg_field_present(cfg: dict, key: str) -> bool:
    if key == "enabled":
        return bool(cfg.get(key))
    val = cfg.get(key)
    return bool(val and str(val).strip())


def wechat_pay_prepay_missing(cfg: dict) -> list[str]:
    """下单（Native/JSAPI）必填项。"""
    return [label for key, label in _WECHAT_PREPAY_CHECKS if not _cfg_field_present(cfg, key)]


def wechat_pay_notify_missing(cfg: dict) -> list[str]:
    """支付回调验签额外必填项（平台证书 或 微信支付公钥 二选一）。"""
    platform_pem = (cfg.get("platform_cert_pem") or "").strip()
    has_platform_cert = _cfg_field_present(cfg, "platform_cert_pem") and "BEGIN PUBLIC KEY" not in platform_pem
    has_pay_public_key = _cfg_field_present(cfg, "pay_public_key_pem") or (
        "BEGIN PUBLIC KEY" in platform_pem or "BEGIN RSA PUBLIC KEY" in platform_pem
    )
    missing: list[str] = []
    if not has_platform_cert and not has_pay_public_key:
        missing.append("微信支付平台证书(PEM) 或 微信支付公钥(PEM)")
    if has_pay_public_key and not _cfg_field_present(cfg, "pay_public_key_id"):
        missing.append("微信支付公钥 ID（公钥模式推荐填写）")
    if not (cfg.get("api_v3_key") or "").strip():
        missing.append("APIv3 密钥")
    return missing


def wechat_pay_full_missing(cfg: dict) -> list[str]:
    return wechat_pay_prepay_missing(cfg) + wechat_pay_notify_missing(cfg)


def get_alipay_config(db: Session | None = None) -> dict:
    session, close = _session(db)
    try:
        return {
            "enabled": get_bool(session, "alipay_enabled"),
            "app_id": get_str(session, "alipay_app_id"),
            "private_key": get_secret(session, "alipay_private_key"),
            "public_key": get_str(session, "alipay_public_key"),
            "notify_url": get_str(session, "alipay_notify_url"),
        }
    finally:
        if close:
            session.close()


def get_douyin_pay_config(db: Session | None = None) -> dict:
    session, close = _session(db)
    try:
        return {
            "enabled": get_bool(session, "douyin_pay_enabled"),
            "app_id": get_str(session, "douyin_pay_app_id"),
            "merchant_id": get_str(session, "douyin_pay_merchant_id"),
            "salt": get_secret(session, "douyin_pay_salt"),
            "token": get_secret(session, "douyin_pay_token"),
            "notify_url": get_str(session, "douyin_pay_notify_url"),
        }
    finally:
        if close:
            session.close()


def get_wechat_mp_config(db: Session | None = None) -> dict:
    session, close = _session(db)
    try:
        return {
            "enabled": get_bool(session, "wechat_mp_enabled", True),
            "app_id": get_str(session, "wechat_mp_app_id"),
            "app_secret": get_secret(session, "wechat_mp_app_secret"),
            "original_id": get_str(session, "wechat_mp_original_id"),
            "request_legal_domain": get_str(session, "wechat_mp_request_legal_domain"),
            "socket_legal_domain": get_str(session, "wechat_mp_socket_legal_domain"),
            "upload_legal_domain": get_str(session, "wechat_mp_upload_legal_domain"),
            "download_legal_domain": get_str(session, "wechat_mp_download_legal_domain"),
            "udp_legal_domain": get_str(session, "wechat_mp_udp_legal_domain"),
            "tcp_legal_domain": get_str(session, "wechat_mp_tcp_legal_domain"),
            "business_domain": get_str(session, "wechat_mp_business_domain"),
            "msg_push_url": get_str(session, "wechat_mp_msg_push_url"),
            "msg_token": get_secret(session, "wechat_mp_msg_token"),
            "msg_encoding_aes_key": get_secret(session, "wechat_mp_msg_encoding_aes_key"),
            "msg_encrypt_mode": get_str(session, "wechat_mp_msg_encrypt_mode") or "safe",
            "msg_data_format": get_str(session, "wechat_mp_msg_data_format") or "JSON",
            "subscribe_template_ids": get_str(session, "wechat_mp_subscribe_template_ids"),
            "env_version": get_str(session, "wechat_mp_env_version") or "release",
        }
    finally:
        if close:
            session.close()


def get_wechat_official_config(db: Session | None = None) -> dict:
    session, close = _session(db)
    try:
        return {
            "enabled": get_bool(session, "wechat_official_enabled", True),
            "app_id": get_str(session, "wechat_official_app_id"),
            "app_secret": get_secret(session, "wechat_official_app_secret"),
            "original_id": get_str(session, "wechat_official_original_id"),
            "account_type": get_str(session, "wechat_official_type") or "service",
            "server_url": get_str(session, "wechat_official_server_url"),
            "token": get_secret(session, "wechat_official_token"),
            "encoding_aes_key": get_secret(session, "wechat_official_encoding_aes_key"),
            "encrypt_mode": get_str(session, "wechat_official_encrypt_mode") or "safe",
            "oauth_domain": get_str(session, "wechat_official_oauth_domain"),
            "jsapi_domains": get_str(session, "wechat_official_jsapi_domains"),
            "ip_whitelist": get_str(session, "wechat_official_ip_whitelist"),
        }
    finally:
        if close:
            session.close()


def get_douyin_mp_config(db: Session | None = None) -> dict:
    session, close = _session(db)
    try:
        return {
            "enabled": get_bool(session, "douyin_mp_enabled", True),
            "app_id": get_str(session, "douyin_mp_app_id"),
            "app_secret": get_secret(session, "douyin_mp_app_secret"),
            "app_name": get_str(session, "douyin_mp_app_name"),
            "original_id": get_str(session, "douyin_mp_original_id"),
            "sandbox": get_bool(session, "douyin_mp_sandbox_enabled"),
            "server_domain": get_str(session, "douyin_mp_server_domain"),
            "upload_legal_domain": get_str(session, "douyin_mp_upload_legal_domain"),
            "download_legal_domain": get_str(session, "douyin_mp_download_legal_domain"),
            "socket_legal_domain": get_str(session, "douyin_mp_socket_legal_domain"),
            "webview_domain": get_str(session, "douyin_mp_webview_domain"),
            "msg_url": get_str(session, "douyin_mp_msg_url"),
            "msg_token": get_secret(session, "douyin_mp_msg_token"),
        }
    finally:
        if close:
            session.close()


def get_redis_url(db: Session | None = None) -> str:
    session, close = _session(db)
    try:
        return get_str(session, "redis_url")
    finally:
        if close:
            session.close()


def get_unipush_config(db: Session | None = None) -> dict:
    cfg = get_ai_integration(db, "unipush")
    extra = cfg.get("extra") or {}
    return {
        "app_id": cfg.get("api_key") or "",
        "master_secret": cfg.get("api_secret") or "",
        "app_key": extra.get("app_key") or "",
        "base_url": cfg.get("base_url") or "https://restapi.getui.com/v2",
        "enabled": cfg.get("enabled", False),
    }


def get_esign_config(db: Session | None = None) -> dict:
    cfg = get_ai_integration(db, "esign")
    return {
        "api_key": cfg.get("api_key") or "",
        "api_secret": cfg.get("api_secret") or "",
        "base_url": cfg.get("base_url") or "https://openapi.esign.cn",
        "enabled": cfg.get("enabled", False),
    }


def get_artc_config(db: Session | None = None) -> dict:
    cfg = get_ai_integration(db, "artc")
    extra = cfg.get("extra") or {}
    return {
        "app_id": extra.get("app_id") or cfg.get("api_key") or "",
        "app_key": extra.get("app_key") or cfg.get("api_secret") or "",
        "token_expire": int(extra.get("token_expire") or 3600),
        "enabled": cfg.get("enabled", False),
    }


def get_lingjing_config(db: Session | None = None) -> dict:
    cfg = get_ai_integration(db, "lingjing")
    extra = cfg.get("extra") or {}
    return {
        "tenant_id": extra.get("tenant_id") or extra.get("app_id") or "",
        "interaction_config_id": extra.get("interaction_config_id") or "",
        "access_key": extra.get("access_key") or cfg.get("api_key") or "",
        "access_secret": extra.get("access_secret") or cfg.get("api_secret") or "",
        "base_url": cfg.get("base_url") or "",
        "enabled": cfg.get("enabled", False),
        "note": "参数用于阿里云智能媒体实时工作流的数字人节点，本服务不调用灵境 HTTP 接口",
    }


def get_voice_api_key(code: str, db: Session | None = None) -> str | None:
    cfg = get_ai_integration(db, code)
    return cfg.get("api_key") if cfg.get("enabled") else None
