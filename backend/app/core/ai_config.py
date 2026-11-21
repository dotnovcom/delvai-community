from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.integration_config import ai_mock_enabled


def ai_mock_block_reason(api_key: str | None = None, db: Session | None = None) -> str | None:
    """返回启用开发模式的原因；关闭时返回 None。未填密钥不会单独打开开发模式。"""
    del api_key
    session = db
    close = False
    if session is None:
        session = SessionLocal()
        close = True
    try:
        if settings.AI_MOCK_MODE:
            if settings.APP_ENV == "production":
                return "环境变量 AI_MOCK_MODE=true（请在服务器 .env 设为 false 并重启 backend）"
            return "环境变量 AI_MOCK_MODE=true"
        if ai_mock_enabled(session):
            return "后台已开启开发模式（基础配置 → 功能开关）"
        return None
    finally:
        if close:
            session.close()


def use_ai_mock(api_key: str | None = None, db: Session | None = None) -> bool:
    """仅当环境变量或后台「开发模式」打开时返回模拟内容。保存后立即生效。"""
    return ai_mock_block_reason(api_key, db) is not None
