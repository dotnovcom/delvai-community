"""PII 脱敏：手机号、身份证号等。"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.services.runtime_config import get_bool

_PHONE_RE = re.compile(r"(?<!\d)(1\d{2})\d{4}(\d{4})(?!\d)")
_ID_RE = re.compile(r"(?<!\d)\d{6}(\d{8})\d{3}[\dXx](?!\d)")


def mask_text(db: Session | None, text: str) -> str:
    if db is not None and not get_bool(db, "pii_mask_enabled", True):
        return text
    if db is None:
        return text
    out = _PHONE_RE.sub(r"\1****\2", text)
    out = _ID_RE.sub(r"******\1****", out)
    return out
