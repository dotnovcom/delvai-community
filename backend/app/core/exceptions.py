import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _normalize_detail(detail: Any) -> dict:
    if isinstance(detail, dict) and "message" in detail:
        return {"detail": detail}
    if isinstance(detail, str):
        return {"detail": ErrorDetail(code="HTTP_ERROR", message=detail).model_dump()}
    return {"detail": ErrorDetail(code="HTTP_ERROR", message=str(detail)).model_dump()}


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    body = _normalize_detail(exc.detail)
    return JSONResponse(status_code=exc.status_code, content=body)


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = _json_safe(exc.errors())
    message = "; ".join(
        f"{e.get('loc', [])}: {e.get('msg')}" for e in errors[:3] if isinstance(e, dict)
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail=ErrorDetail(code="VALIDATION_ERROR", message=message or "参数校验失败"),
            errors=errors if isinstance(errors, list) else [errors],
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail=ErrorDetail(code="INTERNAL_ERROR", message="服务器内部错误"),
        ).model_dump(),
    )
