from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "得律AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: Optional[str] = None
    ALLOW_PAYMENT_MOCK: bool = False
    ALLOW_DEV_PAYMENT_CONFIRM: bool = False
    ALLOW_PUBLIC_UPLOADS: bool = False
    ALLOW_ESIGN_CALLBACK_WITHOUT_SECRET: bool = False
    ESIGN_CALLBACK_SECRET: Optional[str] = None
    FILE_URL_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"]
    )

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://falitong:falitong@localhost:5432/falitong"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg2_driver(cls, value: object) -> object:
        """镜像只安装了 psycopg2。新版 SQLAlchemy 会把 postgresql:// 当成 psycopg3。"""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql+psycopg2://"):
            return value
        if value.startswith("postgresql://"):
            return "postgresql+psycopg2://" + value[len("postgresql://") :]
        if value.startswith("postgres://"):
            return "postgresql+psycopg2://" + value[len("postgres://") :]
        return value

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "falitong"
    ELASTICSEARCH_ENABLED: bool = True

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # SMS
    SMS_CODE_EXPIRE_SECONDS: int = 300
    SMS_RATE_LIMIT_SECONDS: int = 60

    # Aliyun
    ALIYUN_ACCESS_KEY_ID: Optional[str] = None
    ALIYUN_ACCESS_KEY_SECRET: Optional[str] = None
    # Aliyun OSS
    ALIYUN_OSS_BUCKET: Optional[str] = None
    ALIYUN_OSS_ENDPOINT: Optional[str] = None
    ALIYUN_OSS_REGION: str = "oss-cn-hangzhou"
    ALIYUN_OSS_BASE_URL: Optional[str] = None

    # Aliyun ARTC (实时音视频)
    ARTC_APP_ID: Optional[str] = None
    ARTC_APP_KEY: Optional[str] = None
    ARTC_TOKEN_EXPIRE_SECONDS: int = 3600

    # 语音服务
    PARAFORMER_API_KEY: Optional[str] = None
    COSYVOICE_API_KEY: Optional[str] = None

    # 数字人灵境
    LINGJING_APP_ID: Optional[str] = None
    LINGJING_API_KEY: Optional[str] = None

    # Aliyun SMS
    ALIYUN_SMS_SIGN_NAME: Optional[str] = None
    ALIYUN_SMS_TEMPLATE_CODE: Optional[str] = None

    # AI APIs
    FARUI_API_KEY: Optional[str] = None
    FARUI_API_BASE: str = "https://dashscope.aliyuncs.com/api/v1"
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    QWEN_VL_API_KEY: Optional[str] = None
    AI_MOCK_MODE: bool = False

    # WeChat Mini Program
    WECHAT_APP_ID: Optional[str] = None
    WECHAT_APP_SECRET: Optional[str] = None

    # Alipay Mini Program
    ALIPAY_APP_ID: Optional[str] = None

    # Douyin Mini Program
    DOUYIN_APP_ID: Optional[str] = None

    # eSign
    ESIGN_API_KEY: Optional[str] = None
    ESIGN_API_SECRET: Optional[str] = None
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"

    # uni-push
    UNIPUSH_APP_ID: Optional[str] = None
    UNIPUSH_APP_KEY: Optional[str] = None
    UNIPUSH_MASTER_SECRET: Optional[str] = None

    # Admin bootstrap
    ADMIN_BOOTSTRAP_PHONE: Optional[str] = None
    ADMIN_BOOTSTRAP_PASSWORD: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
