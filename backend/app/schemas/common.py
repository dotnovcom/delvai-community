from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str = "ERROR"
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail | str
    errors: Optional[list[dict[str, Any]]] = None
