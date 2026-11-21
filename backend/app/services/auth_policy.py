"""登录/注册方式开关（系统配置）"""

from sqlalchemy.orm import Session

from app.services.config_service import get_bool_setting

AUTH_LOGIN_PHONE = "auth_login_phone_enabled"
AUTH_LOGIN_PHONE_SMS = "auth_login_phone_sms_enabled"
AUTH_LOGIN_EMAIL = "auth_login_email_enabled"
AUTH_LOGIN_EMAIL_SMS = "auth_login_email_sms_enabled"
AUTH_LOGIN_WECHAT = "auth_login_wechat_enabled"
AUTH_LOGIN_DOUYIN = "auth_login_douyin_enabled"
AUTH_REGISTER_PHONE = "auth_register_phone_enabled"
AUTH_REGISTER_EMAIL = "auth_register_email_enabled"
AUTH_REQUIRE_PHONE_BIND = "auth_require_phone_bind"
AUTH_REQUIRE_EMAIL_BIND = "auth_require_email_bind"


def login_phone_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_LOGIN_PHONE, True)


def login_phone_sms_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_LOGIN_PHONE_SMS, True)


def login_email_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_LOGIN_EMAIL, False)


def login_email_sms_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_LOGIN_EMAIL_SMS, True)


def login_wechat_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_LOGIN_WECHAT, True)


def login_douyin_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_LOGIN_DOUYIN, True)


def register_phone_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_REGISTER_PHONE, True)


def register_email_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_REGISTER_EMAIL, False)


def require_phone_bind_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_REQUIRE_PHONE_BIND, False)


def require_email_bind_enabled(db: Session) -> bool:
    return get_bool_setting(db, AUTH_REQUIRE_EMAIL_BIND, False)


def get_auth_public_config(db: Session) -> dict[str, bool]:
    return {
        "login_phone_enabled": login_phone_enabled(db),
        "login_phone_sms_enabled": login_phone_sms_enabled(db),
        "login_email_enabled": login_email_enabled(db),
        "login_email_sms_enabled": login_email_sms_enabled(db),
        "login_wechat_enabled": login_wechat_enabled(db),
        "login_douyin_enabled": login_douyin_enabled(db),
        "register_phone_enabled": register_phone_enabled(db),
        "register_email_enabled": register_email_enabled(db),
        "require_phone_bind": require_phone_bind_enabled(db),
        "require_email_bind": require_email_bind_enabled(db),
    }


def require_login_phone(db: Session) -> None:
    if not login_phone_enabled(db):
        raise ValueError("手机号登录未开启")


def require_login_phone_sms(db: Session) -> None:
    require_login_phone(db)
    if not login_phone_sms_enabled(db):
        raise ValueError("手机号验证码登录未开启")


def require_login_email(db: Session) -> None:
    if not login_email_enabled(db):
        raise ValueError("邮箱登录未开启")


def require_login_email_sms(db: Session) -> None:
    require_login_email(db)
    if not login_email_sms_enabled(db):
        raise ValueError("邮箱验证码登录未开启")


def require_login_wechat(db: Session) -> None:
    if not login_wechat_enabled(db):
        raise ValueError("微信登录未开启")


def require_login_douyin(db: Session) -> None:
    if not login_douyin_enabled(db):
        raise ValueError("抖音登录未开启")
    from app.services.integration_config import get_douyin_mp_config

    cfg = get_douyin_mp_config(db)
    if not cfg.get("enabled", True):
        raise ValueError("抖音小程序未启用")
    if not cfg.get("app_id") or not cfg.get("app_secret"):
        raise ValueError("请在平台配置中填写抖音小程序 AppID/AppSecret")


def require_register_phone(db: Session) -> None:
    if not register_phone_enabled(db):
        raise ValueError("手机号注册未开启")


def require_register_email(db: Session) -> None:
    if not register_email_enabled(db):
        raise ValueError("邮箱注册未开启")
