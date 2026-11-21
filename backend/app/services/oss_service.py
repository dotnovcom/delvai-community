import logging

from app.services.storage_service import upload_bytes

logger = logging.getLogger(__name__)


async def upload_file(file_content: bytes, filename: str, folder: str = "files") -> str:
    """上传文件到当前启用的存储后端。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        return upload_bytes(db, file_content, filename, folder=folder)
    finally:
        db.close()


async def upload_pdf(content: bytes, filename: str) -> str:
    return await upload_file(content, filename, folder="reports")
