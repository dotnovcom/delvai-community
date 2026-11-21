import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.services import config_service
from app.services.runtime_config import get_int, sms_code_expire_seconds, sms_rate_limit_seconds

logger = logging.getLogger(__name__)

SMS_CODE_PREFIX = "sms:code:"
SMS_RATE_PREFIX = "sms:rate:"
SMS_FAIL_PREFIX = "sms:fail:"


class SmsRateLimitError(ValueError):
    """同一手机号+用途在冷却期内重复请求。"""

    def __init__(self, ttl: int):
        self.ttl = max(int(ttl), 1)
        super().__init__(f"发送过于频繁，请 {self.ttl} 秒后重试")

PURPOSE_TEMPLATE_KEYS = {
    "login": "tpl_login",
    "register": "tpl_register",
    "reset_password": "tpl_reset_password",
    "bind_phone": "tpl_bind_phone",
}


def _generate_code(length: int = 6) -> str:
    import random
    import string
    return "".join(random.choices(string.digits, k=length))


def _code_key(phone: str, purpose: str) -> str:
    return f"{SMS_CODE_PREFIX}{purpose}:{phone}"


def _fail_key(phone: str, purpose: str) -> str:
    return f"{SMS_FAIL_PREFIX}{purpose}:{phone}"


def _fail_limits(db: Session | None) -> tuple[int, int]:
    if db is None:
        return 5, 900
    return (
        get_int(db, "sms_code_max_failures", 5),
        get_int(db, "sms_code_fail_window_seconds", 900),
    )


def _get_provider(db: Session | None) -> str:
    session = db
    close = False
    if session is None:
        session = SessionLocal()
        close = True
    try:
        return (config_service.get_setting(session, "sms_active_provider", "aliyun") or "aliyun").lower()
    finally:
        if close:
            session.close()


def normalize_cn_phone_e164(phone: str) -> str:
    """国内手机号 → E.164（腾讯云 PhoneNumberSet 要求 +86 前缀）。"""
    raw = phone.strip().replace(" ", "").replace("-", "")
    if raw.startswith("+"):
        return raw
    if raw.startswith("0086"):
        raw = raw[4:]
    elif raw.startswith("86") and len(raw) >= 13:
        raw = raw[2:]
    if len(raw) == 11 and raw.isdigit():
        return f"+86{raw}"
    raise ValueError("手机号格式不正确，请使用 11 位中国大陆手机号")


def _load_sms_config(db: Session | None, purpose: str = "login") -> dict:
    session = db
    close = False
    if session is None:
        session = SessionLocal()
        close = True
    try:
        provider = _get_provider(session)
        tpl_suffix = PURPOSE_TEMPLATE_KEYS.get(purpose, "tpl_login")
        tpl_key = f"{provider}_sms_{tpl_suffix}"

        if provider == "tencent":
            sk_raw = config_service.get_setting(session, "tencent_sms_secret_key")
            sid_raw = config_service.get_setting(session, "tencent_sms_secret_id")
            secret_id = config_service.decrypt_setting_value(sid_raw).strip() if sid_raw else None
            secret_key = config_service.decrypt_setting_value(sk_raw).strip() if sk_raw else None
            return {
                "provider": provider,
                "expire": sms_code_expire_seconds(session),
                "rate": sms_rate_limit_seconds(session),
                "secret_id": secret_id or None,
                "secret_key": secret_key or None,
                "sdk_app_id": config_service.get_setting(session, "tencent_sms_sdk_app_id"),
                "sign": config_service.get_setting(session, "tencent_sms_sign_name"),
                "region": config_service.get_setting(session, "tencent_sms_region", "ap-guangzhou"),
                "template_param_count": config_service.get_setting(session, "tencent_sms_template_param_count", "1"),
                "template": config_service.get_setting(session, tpl_key),
            }

        ak_raw = config_service.get_setting(session, "aliyun_sms_access_key_id")
        sk_raw = config_service.get_setting(session, "aliyun_sms_access_key_secret")
        ak = config_service.decrypt_setting_value(ak_raw).strip() if ak_raw else None
        sk = config_service.decrypt_setting_value(sk_raw).strip() if sk_raw else None
        template = config_service.get_setting(session, tpl_key)
        if not template:
            template = config_service.get_setting(session, "aliyun_sms_tpl_login")
        return {
            "provider": provider,
            "expire": sms_code_expire_seconds(session),
            "rate": sms_rate_limit_seconds(session),
            "ak": ak,
            "secret_key": sk,
            "sign": config_service.get_setting(session, "aliyun_sms_sign_name"),
            "template": template,
        }
    finally:
        if close:
            session.close()


def _build_tencent_template_param_set(code: str, cfg: dict) -> list[str]:
    """按模板 {1}/{2}… 变量个数构造 TemplateParamSet（与控制台审核模板一致）。"""
    raw = str(cfg.get("template_param_count") or "1").strip()
    try:
        count = max(0, int(raw))
    except ValueError:
        count = 1
    if count == 0:
        return []
    params: list[str] = [code]
    if count >= 2:
        expire = int(cfg.get("expire") or 300)
        params.append(str(max(1, expire // 60)))
    if count > len(params):
        raise ValueError(
            f"腾讯云模板参数个数配置为 {count}，当前仅支持自动填充验证码"
            f"{'及有效期分钟数' if count == 2 else ''}。"
            "请在控制台确认模板变量个数，或将「TemplateParamSet 个数」改为与模板一致。"
        )
    return params[:count]


def _tencent_template_param_hint(exc: Exception) -> str | None:
    msg = str(exc)
    if "TemplateParamSetNotMatchApprovedTemplate" in msg or "does not match the template content" in msg:
        return (
            "模板变量个数与 TemplateParamSet 不一致。"
            "请在短信控制台查看该 TemplateId 正文中有几个 {1}{2}…，"
            "并在「腾讯云短信 → TemplateParamSet 个数」设为相同数量"
            "（2 个变量时第 2 个自动填验证码有效分钟数）。"
        )
    return None


def _tencent_configured(cfg: dict) -> bool:
    return bool(
        cfg.get("secret_id")
        and cfg.get("secret_key")
        and cfg.get("sdk_app_id")
        and cfg.get("sign")
        and cfg.get("template")
    )


def _aliyun_configured(cfg: dict) -> bool:
    return bool(cfg.get("ak") and cfg.get("secret_key") and cfg.get("sign") and cfg.get("template"))


def _check_rate_limit(redis_client, rate_key: str) -> None:
    if not redis_client.exists(rate_key):
        return
    ttl = redis_client.ttl(rate_key)
    # -1：脏数据（无 TTL），-2：已过期但 exists 竞态；清理后放行
    if ttl <= 0:
        redis_client.delete(rate_key)
        return
    raise SmsRateLimitError(ttl)


def send_verification_code(phone: str, purpose: str = "login", db: Session | None = None) -> dict:
    cfg = _load_sms_config(db, purpose)
    redis_client = get_redis()
    rate_key = f"{SMS_RATE_PREFIX}{purpose}:{phone}"

    _check_rate_limit(redis_client, rate_key)

    code = _generate_code()
    code_key = _code_key(phone, purpose)

    configured = False
    if cfg["provider"] == "tencent":
        configured = _tencent_configured(cfg)
        if configured:
            _send_tencent_sms(phone, code, cfg)
    else:
        configured = _aliyun_configured(cfg)
        if configured:
            _send_aliyun_sms(phone, code, cfg["sign"], cfg["template"], cfg)

    if not configured:
        logger.info("[DEV] SMS code for %s (%s/%s): %s", phone, cfg["provider"], purpose, code)

    # 仅在发送成功（或开发/mock 模式）后写入 Redis，避免失败仍占冷却期
    redis_client.setex(code_key, cfg["expire"], code)
    redis_client.setex(rate_key, cfg["rate"], "1")

    result = {"message": "验证码已发送", "expire_seconds": cfg["expire"]}
    from app.services.integration_config import ai_mock_enabled

    if ai_mock_enabled(db) and not configured:
        result["debug_code"] = code
    return result


def verify_code(phone: str, code: str, purpose: str = "login", db: Session | None = None) -> bool:
    redis_client = get_redis()
    max_fail, fail_window = _fail_limits(db)
    fail_key = _fail_key(phone, purpose)
    fails = int(redis_client.get(fail_key) or 0)
    if fails >= max_fail:
        raise ValueError("验证失败次数过多，请稍后再试")

    code_key = _code_key(phone, purpose)
    stored = redis_client.get(code_key)

    if not stored or stored != code:
        new_fails = redis_client.incr(fail_key)
        if new_fails == 1:
            redis_client.expire(fail_key, fail_window)
        if new_fails >= max_fail:
            raise ValueError("验证失败次数过多，请稍后再试")
        return False

    redis_client.delete(code_key)
    redis_client.delete(fail_key)
    return True


def _send_aliyun_sms(
    phone: str,
    code: str,
    sign_name: str | None,
    template: str | None,
    cfg: dict | None = None,
) -> None:
    import json as _json
    import uuid
    from urllib.parse import quote

    if cfg is None:
        session = SessionLocal()
        try:
            cfg = _load_sms_config(session)
        finally:
            session.close()

    ak = cfg.get("ak")
    sk = cfg.get("secret_key")
    if not ak or not sk or not template or not sign_name:
        logger.warning("Aliyun SMS skipped (missing AccessKeyId/Secret/SignName/TemplateCode)")
        return

    params = {
        "AccessKeyId": ak,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone.strip(),
        "SignName": sign_name,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": uuid.uuid4().hex,
        "SignatureVersion": "1.0",
        "TemplateCode": template,
        "TemplateParam": _json.dumps({"code": code}, ensure_ascii=False),
        "Timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    sorted_items = sorted(params.items())
    canonical = "&".join(f"{quote(k, safe='~')}={quote(str(v), safe='~')}" for k, v in sorted_items)
    string_to_sign = f"GET&%2F&{quote(canonical, safe='~')}"
    import base64
    import hashlib
    import hmac

    signature = base64.b64encode(
        hmac.new((sk + "&").encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    params["Signature"] = signature
    query = "&".join(f"{quote(k, safe='~')}={quote(str(v), safe='~')}" for k, v in sorted(params.items()))
    url = f"https://dysmsapi.aliyuncs.com/?{query}"

    import httpx

    resp = httpx.get(url, timeout=15)
    logger.info("Aliyun SMS response %s: %s", phone, resp.text[:300])
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception as exc:
        raise ValueError("阿里云短信响应解析失败") from exc
    if data.get("Code") != "OK":
        raise ValueError(f"阿里云短信发送失败: {data.get('Message') or data.get('Code')}")


def _tencent_sdk_error_message(exc: Exception) -> str:
    try:
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

        if isinstance(exc, TencentCloudSDKException):
            code = exc.get_code() or type(exc).__name__
            message = exc.get_message() or str(exc)
            return f"腾讯云短信发送失败: {code} {message}".strip()
    except ImportError:
        pass
    if isinstance(exc, ImportError):
        return "腾讯云短信 SDK 未安装，请重建 backend 镜像（requirements.txt 含 tencentcloud-sdk-python）"
    return f"腾讯云短信发送失败: {exc}"


def _build_tencent_sms_client(secret_id: str, secret_key: str, region: str):
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.sms.v20210111 import sms_client

    cred = credential.Credential(secret_id, secret_key)
    http_profile = HttpProfile()
    http_profile.endpoint = "sms.tencentcloudapi.com"
    http_profile.reqMethod = "POST"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return sms_client.SmsClient(cred, region, client_profile)


def _send_tencent_sms(phone: str, code: str, cfg: dict) -> None:
    """调用腾讯云 SendSms（API 2021-01-11）。"""
    secret_id = cfg.get("secret_id")
    secret_key = cfg.get("secret_key")
    sdk_app_id = cfg.get("sdk_app_id")
    sign_name = cfg.get("sign") or ""
    template_id = cfg.get("template")
    region = cfg.get("region") or "ap-guangzhou"

    missing = []
    if not secret_id:
        missing.append("SecretId")
    if not secret_key:
        missing.append("SecretKey")
    if not sdk_app_id:
        missing.append("SmsSdkAppId")
    if not sign_name:
        missing.append("SignName")
    if not template_id:
        missing.append("TemplateId")
    if missing:
        logger.warning("Tencent SMS skipped (missing %s)", ", ".join(missing))
        return

    if not str(secret_id).startswith("AKID"):
        raise ValueError(
            "腾讯云 SecretId 格式不正确（应以 AKID 开头）。"
            "请在管理后台同时重新粘贴 CAM 密钥对（SecretId + SecretKey）后保存，并重启 backend。"
        )
    if len(str(secret_key)) < 16:
        raise ValueError(
            "腾讯云 SecretKey 长度异常，可能未正确保存。"
            "请在管理后台同时重新粘贴 CAM 密钥对（SecretId + SecretKey）后保存，并重启 backend。"
        )

    try:
        from tencentcloud.sms.v20210111 import models

        client = _build_tencent_sms_client(secret_id, secret_key, region)
        req = models.SendSmsRequest()
        req.SmsSdkAppId = str(sdk_app_id)
        req.SignName = sign_name
        req.TemplateId = str(template_id)
        req.PhoneNumberSet = [normalize_cn_phone_e164(phone)]
        req.TemplateParamSet = _build_tencent_template_param_set(code, cfg)

        resp = client.SendSms(req)
        statuses = resp.SendStatusSet or []
        if not statuses:
            raise ValueError("腾讯云短信无返回状态")
        for item in statuses:
            if item.Code != "Ok":
                raise ValueError(f"腾讯云短信发送失败: {item.Code} {item.Message or ''}".strip())
    except ValueError:
        raise
    except Exception as exc:
        logger.exception(
            "Tencent SMS API error phone=%s template=%s params=%s",
            phone,
            template_id,
            len(_build_tencent_template_param_set(code, cfg)) if cfg else 0,
        )
        hint = _tencent_template_param_hint(exc)
        base = _tencent_sdk_error_message(exc)
        raise ValueError(f"{base} {hint}".strip() if hint else base) from exc

    logger.info(
        "Tencent SMS sent to %s (SmsSdkAppId=%s, TemplateId=%s, Region=%s, param_count=%s)",
        phone,
        sdk_app_id,
        template_id,
        region,
        len(_build_tencent_template_param_set(code, cfg)),
    )
