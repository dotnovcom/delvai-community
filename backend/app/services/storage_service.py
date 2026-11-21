"""统一文件存储：本地 / 阿里云 OSS / 腾讯云 COS / 七牛云 Kodo。"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.runtime_config import get_str
from app.utils.file_tokens import build_signed_file_url
from app.utils.public_url import _is_local_host, normalize_public_base

logger = logging.getLogger(__name__)

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


def resolve_local_path(folder: str, filename: str) -> Path:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise ValueError("invalid filename")
    root = UPLOAD_ROOT.resolve()
    path = (UPLOAD_ROOT / folder.strip().lower() / safe_name).resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("path traversal")
    return path


def _ensure_local_dir(subpath: str) -> Path:
    path = UPLOAD_ROOT / subpath
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _object_key(folder: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return f"{folder}/{datetime.utcnow():%Y%m%d}/{uuid.uuid4().hex}{ext}"


def _public_base(db: Session) -> str:
    """浏览器可访问的站点根。localhost 不能拿来拼头像地址，改为返回空，使用当前站点相对路径。"""
    url = (get_str(db, "pc_site_url") or "").strip()
    if url and not _is_local_host(url):
        return normalize_public_base(url)
    from app.core.config import settings

    env = (settings.FRONTEND_BASE_URL or "").strip()
    if env and not _is_local_host(env):
        return normalize_public_base(env)
    return ""


def present_file_url(db: Session, url: str | None) -> str | None:
    """把头像等本地文件地址改成当前站点可打开的链接。"""
    raw = (url or "").strip()
    if not raw:
        return url
    refreshed = refresh_asset_url(db, raw)
    if _is_local_host(refreshed):
        from app.utils.file_tokens import refresh_signed_file_url

        refreshed = refresh_signed_file_url(raw, public_base="")
    return refreshed or raw


def public_base_url(db: Session) -> str:
    return _public_base(db)


def refresh_asset_url(db: Session, url: str) -> str:
    from app.utils.file_tokens import refresh_signed_file_url
    from app.utils.public_url import ensure_https_asset_url

    refreshed = refresh_signed_file_url(url or "", public_base=_public_base(db))
    return ensure_https_asset_url(refreshed)


def get_active_provider(db: Session) -> str:
    raw = (get_str(db, "upload_active_provider", "local") or "local").lower()
    legacy = (get_str(db, "upload_provider", "") or "").lower()
    if raw == "local" and legacy == "oss":
        return "aliyun"
    if raw in ("aliyun", "tencent", "qiniu", "local"):
        return raw
    return "local"


def _aliyun_config(db: Session) -> dict:
    return {
        "access_key_id": get_str(db, "aliyun_oss_access_key_id") or get_str(db, "oss_access_key_id"),
        "access_key_secret": _plain_secret(db, "aliyun_oss_access_key_secret", "oss_access_key_secret"),
        "bucket": get_str(db, "aliyun_oss_bucket") or get_str(db, "oss_bucket"),
        "endpoint": get_str(db, "aliyun_oss_endpoint") or get_str(db, "oss_endpoint"),
        "region": get_str(db, "aliyun_oss_region", "oss-cn-hangzhou"),
        "base_url": get_str(db, "aliyun_oss_base_url") or get_str(db, "oss_base_url"),
    }


def _tencent_config(db: Session) -> dict:
    return {
        "secret_id": get_str(db, "tencent_cos_secret_id"),
        "secret_key": _plain_secret(db, "tencent_cos_secret_key"),
        "bucket": get_str(db, "tencent_cos_bucket"),
        "region": get_str(db, "tencent_cos_region", "ap-guangzhou"),
        "base_url": get_str(db, "tencent_cos_base_url"),
    }


def _qiniu_config(db: Session) -> dict:
    return {
        "access_key": get_str(db, "qiniu_access_key"),
        "secret_key": _plain_secret(db, "qiniu_secret_key"),
        "bucket": get_str(db, "qiniu_bucket"),
        "region": get_str(db, "qiniu_region", "z0"),
        "domain": get_str(db, "qiniu_domain"),
    }


def _plain_secret(db: Session, primary_key: str, legacy_key: str | None = None) -> str | None:
    from app.services import config_service

    raw = config_service.get_setting(db, primary_key)
    if not raw and legacy_key:
        raw = config_service.get_setting(db, legacy_key)
    if not raw:
        return None
    return config_service.decrypt_setting_value(raw)


def upload_bytes(db: Session, content: bytes, filename: str, folder: str = "files") -> str:
    provider = get_active_provider(db)
    key = _object_key(folder, filename or "file.bin")

    if provider == "aliyun":
        cfg = _aliyun_config(db)
        if cfg["access_key_id"] and cfg["access_key_secret"] and cfg["bucket"] and cfg["endpoint"]:
            try:
                return _upload_aliyun(content, key, cfg)
            except Exception:
                logger.exception("Aliyun OSS upload failed, fallback to local")
        else:
            logger.warning("Aliyun OSS not fully configured, fallback to local")
    elif provider == "tencent":
        cfg = _tencent_config(db)
        if cfg["secret_id"] and cfg["secret_key"] and cfg["bucket"] and cfg["region"]:
            try:
                return _upload_tencent(content, key, cfg)
            except Exception:
                logger.exception("Tencent COS upload failed, fallback to local")
        else:
            logger.warning("Tencent COS not fully configured, fallback to local")
    elif provider == "qiniu":
        cfg = _qiniu_config(db)
        if cfg["access_key"] and cfg["secret_key"] and cfg["bucket"] and cfg["domain"]:
            try:
                return _upload_qiniu(content, key, cfg)
            except ValueError:
                raise
            except Exception:
                logger.exception("Qiniu upload failed, fallback to local")
        else:
            logger.warning("Qiniu Kodo not fully configured, fallback to local")

    return _upload_local(db, content, key, folder)


def _upload_local(db: Session, content: bytes, object_key: str, folder: str) -> str:
    filename = object_key.split("/")[-1]
    dest = _ensure_local_dir(f"{folder}/{filename}")
    dest.write_bytes(content)
    return build_signed_file_url(folder, filename, public_base=_public_base(db))


def _upload_aliyun(content: bytes, object_key: str, cfg: dict) -> str:
    import oss2

    auth = oss2.Auth(cfg["access_key_id"], cfg["access_key_secret"])
    bucket = oss2.Bucket(auth, cfg["endpoint"], cfg["bucket"])
    bucket.put_object(object_key, content)
    if cfg.get("base_url"):
        return f"{cfg['base_url'].rstrip('/')}/{object_key}"
    endpoint = cfg["endpoint"].replace("https://", "").replace("http://", "")
    return f"https://{cfg['bucket']}.{endpoint}/{object_key}"


def _upload_tencent(content: bytes, object_key: str, cfg: dict) -> str:
    from qcloud_cos import CosConfig, CosS3Client

    cos_cfg = CosConfig(
        Region=cfg["region"],
        SecretId=cfg["secret_id"],
        SecretKey=cfg["secret_key"],
        Scheme="https",
    )
    client = CosS3Client(cos_cfg)
    client.put_object(Bucket=cfg["bucket"], Body=content, Key=object_key)
    if cfg.get("base_url"):
        return f"{cfg['base_url'].rstrip('/')}/{object_key}"
    return f"https://{cfg['bucket']}.cos.{cfg['region']}.myqcloud.com/{object_key}"


def _upload_qiniu(content: bytes, object_key: str, cfg: dict) -> str:
    from qiniu import Auth, put_data

    auth = Auth(cfg["access_key"], cfg["secret_key"])
    token = auth.upload_token(cfg["bucket"], object_key)
    ret, info = put_data(token, object_key, content)
    if info.status_code >= 400:
        raise ValueError(f"七牛云上传失败: {info}")
    domain = cfg["domain"].rstrip("/")
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    return f"{domain}/{object_key}"
