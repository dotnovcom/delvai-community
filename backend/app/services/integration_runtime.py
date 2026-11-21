"""兼容层：统一从 integration_config 读取 DB 配置。"""

from sqlalchemy.orm import Session

from app.services import integration_config
from app.services.storage_service import _aliyun_config


def get_oss_config(db: Session | None = None) -> dict:
    session, close = integration_config._session(db)
    try:
        return _aliyun_config(session)
    finally:
        if close:
            session.close()


def get_sms_integration(db: Session | None = None) -> dict:
    """保留兼容；短信运行时请直接用 sms_service + system_settings。"""
    session, close = integration_config._session(db)
    try:
        from app.services.runtime_config import get_secret, get_str

        return {
            "access_key_id": get_str(session, "aliyun_sms_access_key_id"),
            "access_key_secret": get_secret(session, "aliyun_sms_access_key_secret"),
            "sign_name": get_str(session, "aliyun_sms_sign_name"),
            "template_code": get_str(session, "aliyun_sms_tpl_login"),
        }
    finally:
        if close:
            session.close()


def get_unipush_config(db: Session | None = None) -> dict:
    return integration_config.get_unipush_config(db)


def get_esign_config(db: Session | None = None) -> dict:
    return integration_config.get_esign_config(db)


def get_artc_config(db: Session | None = None) -> dict:
    return integration_config.get_artc_config(db)


def get_lingjing_config(db: Session | None = None) -> dict:
    return integration_config.get_lingjing_config(db)


def get_voice_api_key(code: str, db: Session | None = None) -> str | None:
    return integration_config.get_voice_api_key(code, db)
