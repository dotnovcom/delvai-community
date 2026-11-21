import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.user import UserResponse

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_phone(v: str) -> str:
    if not PHONE_PATTERN.match(v):
        raise ValueError("手机号格式不正确")
    return v


def validate_email(v: str) -> str:
    email = v.strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValueError("邮箱格式不正确")
    return email


class EnterpriseSsoExchangeRequest(BaseModel):
    code: str = Field(..., min_length=8, max_length=128)


class EnterpriseSsoPublicItem(BaseModel):
    id: int
    name: str
    email_domain: str
    provider: str = "oidc"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class WechatLoginRequest(BaseModel):
    code: str = Field(..., min_length=1)
    ticket: Optional[str] = None


class DouyinLoginRequest(BaseModel):
    code: str = Field(..., min_length=1)


class WechatOauthLoginRequest(BaseModel):
    code: str = Field(..., min_length=1)


class WechatOauthAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str
    redirect_uri: str


class SendSmsRequest(BaseModel):
    phone: str
    purpose: Literal["login", "register", "reset_password", "bind_phone"] = "login"

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)


class PhoneLoginRequest(BaseModel):
    phone: str
    login_type: Literal["sms", "password"] = "sms"
    code: Optional[str] = None
    password: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)

    @model_validator(mode="after")
    def check_login_fields(self):
        if self.login_type == "sms" and not self.code:
            raise ValueError("验证码不能为空")
        if self.login_type == "password" and not self.password:
            raise ValueError("密码不能为空")
        return self


class AdminLoginRequest(BaseModel):
    """管理端帐号：手机号或独立用户名（如 manage），不走前台手机号校验。"""

    phone: str = Field(..., min_length=2, max_length=64)
    login_type: Literal["password"] = "password"
    password: str = Field(..., min_length=1, max_length=64)

    @field_validator("phone")
    @classmethod
    def check_account(cls, v: str) -> str:
        account = (v or "").strip()
        if not account:
            raise ValueError("账号不能为空")
        return account


class RegisterRequest(BaseModel):
    phone: str
    password: str = Field(..., min_length=6, max_length=64)
    code: str = Field(..., min_length=4, max_length=8)
    invite_code: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)


class QrcodeCreateResponse(BaseModel):
    ticket: str
    expire_seconds: int
    qrcode_url: str


class QrcodeStatusResponse(BaseModel):
    status: Literal["pending", "scanned", "confirmed", "expired"]
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[UserResponse] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class ResetPasswordRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6, max_length=64)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


class SendEmailRequest(BaseModel):
    email: str
    purpose: Literal["login", "register", "reset_password", "bind_email"] = "login"

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class EmailLoginRequest(BaseModel):
    email: str
    login_type: Literal["sms", "password"] = "sms"
    code: Optional[str] = None
    password: Optional[str] = None

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)

    @model_validator(mode="after")
    def check_login_fields(self):
        if self.login_type == "sms" and not self.code:
            raise ValueError("验证码不能为空")
        if self.login_type == "password" and not self.password:
            raise ValueError("密码不能为空")
        return self


class EmailRegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6, max_length=64)
    code: str = Field(..., min_length=4, max_length=8)
    invite_code: Optional[str] = None

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class ResetPasswordEmailRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6, max_length=64)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class BindPhoneRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=8)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)


class BindEmailRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=4, max_length=8)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email(v)


class WechatBindRequest(BaseModel):
    code: str = Field(..., min_length=1)
    ticket: str = Field(..., min_length=1)
