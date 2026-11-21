"""未完成强制绑定时拦截业务 API（绑定相关路径除外）"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.deps import _resolve_user_from_token
from app.core.database import SessionLocal
from app.services import auth_binding

logger = logging.getLogger(__name__)


class BindingGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if auth_binding.is_path_allowed_for_incomplete_binding(
            request.url.path, request.method
        ):
            return await call_next(request)

        auth_header = request.headers.get("authorization") or ""
        if not auth_header.lower().startswith("bearer "):
            return await call_next(request)

        token = auth_header[7:].strip()
        if not token:
            return await call_next(request)

        db = SessionLocal()
        try:
            user = _resolve_user_from_token(db, token, strict_session=False)
            if not user or auth_binding.is_binding_complete(db, user):
                return await call_next(request)

            missing = auth_binding.get_missing_bindings(db, user)
            logger.info(
                "binding_required user_id=%s path=%s missing=%s",
                user.id,
                request.url.path,
                missing,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "code": "BINDING_REQUIRED",
                    "message": "请先完成账号绑定",
                    "missing": missing,
                },
            )
        finally:
            db.close()
