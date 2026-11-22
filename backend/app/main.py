import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin, auth, chat, chat_admin, cms, conversations, files, platform_config, users
from app.core.config import settings
from app.core.startup_checks import validate_settings
from app.core.database import SessionLocal
from app.core.exceptions import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.middleware.binding_guard import BindingGuardMiddleware
from app.services import admin_service

logger = logging.getLogger(__name__)

_PRODUCTION_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_PRODUCTION_CORS_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Request-Id",
    "X-API-Key",
]

app = FastAPI(
    title=settings.APP_NAME,
    description="得律AI - 多模态法律AI智能服务平台",
    version="1.0.14",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=_PRODUCTION_CORS_METHODS if settings.APP_ENV == "production" else ["*"],
    allow_headers=_PRODUCTION_CORS_HEADERS if settings.APP_ENV == "production" else ["*"],
)
app.add_middleware(BindingGuardMiddleware)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["认证"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["用户"])
app.include_router(conversations.router, prefix=f"{settings.API_V1_PREFIX}/conversations", tags=["对话"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["聊天"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["运营后台"])
app.include_router(chat_admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["对话互动"])
app.include_router(cms.router, prefix=f"{settings.API_V1_PREFIX}/cms", tags=["CMS"])
app.include_router(platform_config.router, prefix=f"{settings.API_V1_PREFIX}/config", tags=["平台配置"])
app.include_router(files.router, prefix=settings.API_V1_PREFIX, tags=["文件"])

try:
    from commercial import register as register_commercial
except ImportError:
    register_commercial = None

if register_commercial is not None:
    register_commercial(app)

upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(upload_dir, exist_ok=True)
if settings.ALLOW_PUBLIC_UPLOADS:
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.on_event("startup")
def bootstrap_admin():
    validate_settings()
    if settings.ADMIN_BOOTSTRAP_PHONE and settings.ADMIN_BOOTSTRAP_PASSWORD:
        db = SessionLocal()
        try:
            admin_service.ensure_admin_user(
                db, settings.ADMIN_BOOTSTRAP_PHONE, settings.ADMIN_BOOTSTRAP_PASSWORD
            )
        finally:
            db.close()

    db = SessionLocal()
    try:
        from app.services.config_service import seed_defaults
        from app.services.cms_service import seed_cms_defaults

        seed_defaults(db)
        seed_cms_defaults(db)
    except Exception:
        logger.exception("启动种子数据初始化失败")
        if settings.APP_ENV == "production":
            raise
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }
