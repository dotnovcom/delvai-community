import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.storage_service import resolve_local_path
from app.utils.file_tokens import AUTH_FOLDERS, PUBLIC_FOLDERS, verify_file_access

router = APIRouter()

_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def _safe_name(name: str) -> str:
    base = Path(name).name
    if not base or base != name or not _FILENAME_RE.match(base):
        raise HTTPException(status_code=400, detail="非法文件名")
    return base


@router.get("/files/{folder}/{filename}")
def download_file(
    folder: str,
    filename: str,
    exp: int = Query(..., ge=1),
    sig: str = Query(..., min_length=8),
):
    folder = folder.strip().lower()
    filename = _safe_name(filename)
    if folder not in PUBLIC_FOLDERS and folder not in AUTH_FOLDERS:
        raise HTTPException(status_code=404, detail="Not found")

    if not verify_file_access(folder, filename, exp, sig):
        raise HTTPException(status_code=403, detail="链接已失效或无效")

    try:
        path = resolve_local_path(folder, filename)
    except ValueError:
        raise HTTPException(status_code=404, detail="文件不存在") from None

    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(path)
