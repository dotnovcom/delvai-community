"""检索关键词规范化（长度截断、空白折叠）。"""

from __future__ import annotations

MAX_SEARCH_QUERY_LEN = 200
FARUI_SEARCH_QUERY_LEN = 128


def normalize_search_query(q: str, max_len: int = MAX_SEARCH_QUERY_LEN) -> str:
    text = " ".join((q or "").split()).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip()
