from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.user import UserPlatform, UserStatus

PHONE_PATTERN = r"^1[3-9]\d{9}$"


class UserBase(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    openid: Optional[str] = None
    unionid: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    platform: UserPlatform
    status: UserStatus
    is_admin: bool = False
    admin_role: Optional[str] = None
    binding_required_phone: bool = False
    binding_required_email: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=64)
    avatar: Optional[str] = Field(None, max_length=512)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("昵称不能为空")
        return v.strip() if v else v
