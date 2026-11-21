"""第三方集成与基础设施健康检查。"""

from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy.orm import Session

from app.core.redis import get_redis
from app.services import config_service
try:
    from commercial.services import es_client
except ImportError:
    es_client = None
from app.services.integration_config import (
    get_ai_integration,
    get_wechat_pay_config,
    wechat_pay_notify_missing,
    wechat_pay_prepay_missing,
)

logger = logging.getLogger(__name__)


def _status(ok: bool, detail: str = "", latency_ms: int = 0) -> dict:
    return {"ok": ok, "detail": detail, "latency_ms": latency_ms}


def _skipped(detail: str = "未开启") -> dict:
    """未开启的服务不探活，也不计入正常或异常。"""
    return {"ok": True, "skipped": True, "detail": detail, "latency_ms": 0}


async def check_redis() -> dict:
    started = time.perf_counter()
    try:
        client = get_redis()
        client.ping()
        return _status(True, "PONG", int((time.perf_counter() - started) * 1000))
    except Exception as exc:
        return _status(False, str(exc))


async def check_elasticsearch() -> dict:
    from app.core.config import settings

    if not settings.ELASTICSEARCH_ENABLED or es_client is None:
        return _skipped()
    started = time.perf_counter()
    try:
        es_client.get_es_client.cache_clear()
        es = es_client.get_es_client()
        if es:
            ok = es.ping()
            if ok:
                return _status(True, "ping ok", int((time.perf_counter() - started) * 1000))
        url = settings.ELASTICSEARCH_URL.rstrip("/")
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
        ok = resp.status_code == 200
        return _status(ok, f"HTTP {resp.status_code}", int((time.perf_counter() - started) * 1000))
    except Exception as exc:
        return _status(False, str(exc))


async def check_ai_provider(db: Session, code: str) -> dict:
    cfg = get_ai_integration(db, code)
    if not cfg.get("enabled"):
        return _skipped()
    if not cfg.get("api_key"):
        if code in ("mimo_asr", "mimo_tts", "paraformer", "cosyvoice"):
            from commercial.services.integration_probe import probe_provider

            return await probe_provider(db, code)
        from app.services.integration_config import ai_mock_enabled
        if ai_mock_enabled(db):
            return _status(True, "mock mode")
        return _status(False, "api_key not configured")
    started = time.perf_counter()
    extra = cfg.get("extra") or {}
    if code == "farui":
        from commercial.services.ai import farui_sdk

        c = farui_sdk.resolve_config(db)
        if c.get("mock"):
            return _status(True, "mock mode", int((time.perf_counter() - started) * 1000))
        if not farui_sdk.is_configured(c):
            missing = []
            if not cfg.get("api_key"):
                missing.append("AccessKey ID")
            if not cfg.get("api_secret"):
                missing.append("AccessKey Secret")
            if not extra.get("workspace_id"):
                missing.append("workspace_id")
            return _status(False, "missing: " + ", ".join(missing) or "not configured")
        try:
            farui_sdk.create_client(c)
            return _status(True, "SDK client ok", int((time.perf_counter() - started) * 1000))
        except Exception as exc:
            return _status(False, str(exc), int((time.perf_counter() - started) * 1000))
    if code in ("mimo_asr", "mimo_tts", "paraformer", "cosyvoice"):
        from commercial.services.integration_probe import probe_provider

        return await probe_provider(db, code)
    base = cfg.get("base_url") or "https://api.deepseek.com/v1"
    url = f"{base.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
        ok = 200 <= resp.status_code < 300
        if code == "farui" and resp.status_code == 404 and not extra.get("workspace_id"):
            ok = True
            detail = "HTTP 200 (key ok, workspace_id optional)"
        else:
            detail = f"HTTP {resp.status_code}"
        return _status(ok, detail, int((time.perf_counter() - started) * 1000))
    except Exception as exc:
        return _status(False, str(exc), int((time.perf_counter() - started) * 1000))


async def check_sms(db: Session) -> dict:
    provider = (config_service.get_setting(db, "sms_active_provider") or "aliyun").lower()
    started = time.perf_counter()
    if provider == "tencent":
        sid_raw = config_service.get_setting(db, "tencent_sms_secret_id")
        sk_raw = config_service.get_setting(db, "tencent_sms_secret_key")
        secret_id = config_service.decrypt_setting_value(sid_raw or "") if sid_raw else ""
        sdk_app_id = config_service.get_setting(db, "tencent_sms_sdk_app_id")
        sign_name = config_service.get_setting(db, "tencent_sms_sign_name")
        template_id = config_service.get_setting(db, "tencent_sms_tpl_login")
        region = config_service.get_setting(db, "tencent_sms_region", "ap-guangzhou")
        missing = []
        if not secret_id:
            missing.append("SecretId")
        if not sk_raw:
            missing.append("SecretKey")
        if not sdk_app_id:
            missing.append("SmsSdkAppId")
        if not sign_name:
            missing.append("SignName")
        if not template_id:
            missing.append("TemplateId")
        if missing:
            return _status(False, "缺少 SendSms 必填项：" + "、".join(missing))
        try:
            from app.services.sms_service import _build_tencent_sms_client

            sk = config_service.decrypt_setting_value(sk_raw or "")
            _build_tencent_sms_client(secret_id, sk, region)
            return _status(True, "SDK client ok", int((time.perf_counter() - started) * 1000))
        except Exception as exc:
            return _status(False, str(exc), int((time.perf_counter() - started) * 1000))

    ak_raw = config_service.get_setting(db, "aliyun_sms_access_key_id")
    sk_raw = config_service.get_setting(db, "aliyun_sms_access_key_secret")
    ak = config_service.decrypt_setting_value(ak_raw or "") if ak_raw else ""
    sign_name = config_service.get_setting(db, "aliyun_sms_sign_name")
    template_code = config_service.get_setting(db, "aliyun_sms_tpl_login")
    missing = []
    if not ak:
        missing.append("AccessKeyId")
    if not sk_raw:
        missing.append("AccessKeySecret")
    if not sign_name:
        missing.append("SignName")
    if not template_code:
        missing.append("TemplateCode")
    if missing:
        return _status(False, "缺少 SendSms 必填项：" + "、".join(missing))
    return _status(True, "configured", int((time.perf_counter() - started) * 1000))


async def check_wechat_pay(db: Session) -> dict:
    cfg = get_wechat_pay_config(db)
    if not cfg.get("enabled"):
        return _skipped()
    prepay_missing = wechat_pay_prepay_missing(cfg)
    if prepay_missing:
        return _status(False, "缺少：" + "、".join(prepay_missing))
    notify_missing = wechat_pay_notify_missing(cfg)
    if notify_missing:
        return _status(True, "可下单；回调验签缺少：" + "、".join(notify_missing))
    return _status(True, "production ready")


async def check_named_provider(db: Session, code: str) -> dict:
    from commercial.services.integration_probe import probe_provider

    return await probe_provider(db, code)


async def run_all_checks(db: Session) -> dict:
    names = (
        "redis",
        "elasticsearch",
        "farui",
        "deepseek",
        "mimo_asr",
        "mimo_tts",
        "paraformer",
        "cosyvoice",
        "lingjing",
        "artc",
        "esign",
        "unipush",
        "sms",
        "wechat_pay",
    )
    results = await _gather(
        check_redis(),
        check_elasticsearch(),
        check_ai_provider(db, "farui"),
        check_ai_provider(db, "deepseek"),
        check_ai_provider(db, "mimo_asr"),
        check_ai_provider(db, "mimo_tts"),
        check_ai_provider(db, "paraformer"),
        check_ai_provider(db, "cosyvoice"),
        check_named_provider(db, "lingjing"),
        check_named_provider(db, "artc"),
        check_named_provider(db, "esign"),
        check_named_provider(db, "unipush"),
        check_sms(db),
        check_wechat_pay(db),
    )
    items = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.exception("integration health %s failed", name, exc_info=result)
            items[name] = _status(False, "检查失败")
        else:
            items[name] = result
    checked = [v for v in items.values() if not v.get("skipped")]
    ok_count = sum(1 for v in checked if v.get("ok"))
    total = len(checked)
    return {"ok": ok_count == total, "ok_count": ok_count, "total": total, "items": items}


async def _gather(*coros):
    import asyncio
    return await asyncio.gather(*coros, return_exceptions=True)
