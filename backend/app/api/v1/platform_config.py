from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import config_service

router = APIRouter()


@router.get("/public")
def get_public_config(db: Session = Depends(get_db)):
    """前台可读配置（不含密钥）。"""
    return config_service.get_public_settings(db)


@router.get("/legal-pages")
def get_legal_pages(db: Session = Depends(get_db)):
    """注册页/页脚/设置页展示的用户协议、隐私政策、关于平台、联系我们。"""
    from app.content.legal_page_defaults import LEGAL_PAGE_DEFAULTS

    config_service._seed_legal_pages_if_empty(db)

    def _html(db_key: str) -> str:
        val = (config_service.get_setting(db, db_key, "") or "").strip()
        if not val:
            val = (LEGAL_PAGE_DEFAULTS.get(db_key) or "").strip()
        return val

    return {
        "user_agreement": _html("user_agreement_html"),
        "privacy_policy": _html("privacy_policy_html"),
        "about_platform": _html("about_platform_html"),
        "contact_us": _html("contact_us_html"),
        "contract_review_help": _html("contract_review_help_html"),
        "contract_extract_help": _html("contract_extract_help_html"),
    }


@router.get("/client/{platform}")
def get_client_config(platform: str, db: Session = Depends(get_db)):
    """移动端/多端配置。"""
    public = config_service.get_public_settings(db)
    keys_by_platform = {
        "pc": [
            "pc_enabled", "pc_site_url", "pc_seo_title", "pc_seo_keywords",
            "pc_seo_description", "pc_share_title", "pc_share_desc", "pc_og_image", "pc_robots",
        ],
        "h5": [
            "h5_enabled", "h5_site_url", "h5_seo_title", "h5_seo_keywords",
            "h5_seo_description", "h5_share_title", "h5_share_desc",
            "h5_og_image", "h5_theme_color", "h5_pwa_name", "h5_robots",
        ],
        "wechat_mp": [
            "wechat_mp_enabled",
            "wechat_mp_app_id",
            "wechat_mp_original_id",
            "wechat_mp_env_version",
            "auth_login_wechat_enabled",
        ],
        "wechat_official": [
            "wechat_official_enabled",
            "wechat_official_app_id",
            "wechat_official_original_id",
            "wechat_official_type",
            "wechat_official_oauth_domain",
        ],
        "douyin_mp": [
            "douyin_mp_enabled",
            "douyin_mp_app_id",
            "douyin_mp_app_name",
            "douyin_mp_original_id",
            "douyin_mp_server_domain",
            "auth_login_douyin_enabled",
        ],
        "android": [
            "android_enabled",
            "android_app_name",
            "android_package_name",
            "android_min_version",
            "android_latest_version",
            "android_version_code",
            "android_force_update",
            "android_update_message",
            "download_url_android",
        ],
        "ios": [
            "ios_enabled",
            "ios_app_name",
            "ios_bundle_id",
            "ios_app_store_id",
            "ios_min_version",
            "ios_latest_version",
            "ios_build_number",
            "ios_force_update",
            "ios_update_message",
            "download_url_ios",
        ],
        "version": ["app_version", "force_update", "update_message"],
    }
    selected = keys_by_platform.get(platform, [])
    result = {k: public.get(k, config_service.get_setting(db, k, "")) for k in selected}
    if platform == "version":
        result.update({k: public.get(k, "") for k in keys_by_platform["version"]})
    return result
