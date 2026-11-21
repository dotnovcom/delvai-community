"""聊天附件正文提取，供 AI 对话上下文使用。"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.schemas.conversation import SendMessageRequest

try:
    from commercial.services.ai.farui_review import extract_text as _commercial_extract_text
except ImportError:
    _commercial_extract_text = None
from app.services.storage_service import refresh_asset_url, resolve_local_path
from app.utils.file_tokens import parse_local_file_ref

logger = logging.getLogger(__name__)

MAX_EXTRACT_CHARS = 12000


async def fetch_upload_bytes(db: Session, file_url: str) -> tuple[bytes, str]:
    ref = parse_local_file_ref(file_url)
    if ref:
        folder, filename = ref
        try:
            path = resolve_local_path(folder, filename)
            if path.is_file():
                return path.read_bytes(), filename
        except ValueError:
            pass

    url = refresh_asset_url(db, file_url)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        name = url.split("/")[-1].split("?")[0] or "file"
        return resp.content, name


def extract_attachment_text(content: bytes, filename: str) -> str:
    if _commercial_extract_text is None:
        try:
            text = content.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = ""
    else:
        text = _commercial_extract_text(content, filename).strip()
    if not text:
        return ""
    if len(text) > MAX_EXTRACT_CHARS:
        return text[:MAX_EXTRACT_CHARS] + "\n\n…（正文已截断）"
    return text


async def resolve_ai_content_with_attachment(db: Session, data: SendMessageRequest) -> str:
    raw, fname = await fetch_upload_bytes(db, data.file_url or "")
    name = data.file_name or fname
    excerpt = extract_attachment_text(raw, name)
    if not excerpt:
        return (
            f"{data.content}\n\n（附件《{name}》未能提取可读正文，请结合文件名与用户问题作答。）"
        )
    return f"{data.content}\n\n--- 附件《{name}》正文摘录 ---\n{excerpt}"


async def try_resolve_ai_content(db: Session, data: SendMessageRequest) -> str:
    if data.content_type != "file" or not data.file_url:
        return data.content
    try:
        return await resolve_ai_content_with_attachment(db, data)
    except Exception as exc:
        logger.warning("chat attachment extract failed: %s", exc)
        name = data.file_name or "附件"
        return f"{data.content}\n\n（附件《{name}》解析失败，请根据用户问题作一般性法律分析。）"
