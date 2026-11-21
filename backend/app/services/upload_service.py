import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.services.runtime_config import get_str, upload_max_size_bytes
from app.services.storage_service import upload_bytes

logger = logging.getLogger(__name__)


def _allowed_extensions(db: Session) -> set[str]:
    raw = get_str(db, "upload_allowed_types", "jpg,jpeg,png,gif,webp,pdf,doc,docx,xls,xlsx,txt")
    return {x.strip().lower().lstrip(".") for x in raw.split(",") if x.strip()}


def _validate_file(db: Session, file: UploadFile, content: bytes) -> None:
    max_size = upload_max_size_bytes(db)
    if len(content) > max_size:
        raise ValueError(f"文件大小超过限制 ({max_size // 1024 // 1024}MB)")

    allowed = _allowed_extensions(db)
    if not allowed:
        return

    ext = ""
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext and ext not in allowed:
        raise ValueError(f"不允许的文件类型: .{ext}")


async def save_upload(db: Session, file: UploadFile, subdir: str = "files") -> str:
    content = await file.read()
    _validate_file(db, file, content)
    return upload_bytes(db, content, file.filename or "file.bin", folder=subdir)
