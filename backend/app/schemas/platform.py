from datetime import datetime

from pydantic import BaseModel, Field


class PublicArticleItem(BaseModel):
    id: int
    title: str
    summary: str | None = None
    category: str
    cover_url: str | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublicArticleDetail(PublicArticleItem):
    content: str


class PaginatedPublicArticles(BaseModel):
    total: int
    items: list[PublicArticleItem]


class AdminProfileUpdate(BaseModel):
    nickname: str | None = None


class AdminPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class OpenApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=2)
    owner_user_id: int
    enterprise_id: int | None = None
    rate_limit_per_minute: int | None = None
    budget_limit: float | None = Field(None, ge=0, description="累计计费上限(元)，空为不限")
    api_key: str | None = Field(None, min_length=16, description="可选，自定义 Key，须以 ft_live_ 开头")


class OpenApiKeyUpdate(BaseModel):
    name: str | None = None
    owner_user_id: int | None = None
    api_key: str | None = Field(None, min_length=16, description="更换 Key，须以 ft_live_ 开头")
    status: str | None = None
    rate_limit_per_minute: int | None = None
    budget_limit: float | None = Field(None, ge=0, description="累计计费上限(元)，空为不限")
    enterprise_id: int | None = None
