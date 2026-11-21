"""解析 OpenAI / DashScope 兼容 SSE 流，提取文本增量与 token 用量。"""

from __future__ import annotations

import json
from typing import Any


def parse_sse_data_line(data: str) -> tuple[str, int]:
    """从单条 SSE data 行解析 (text_delta, total_tokens)。"""
    if not data or data == "[DONE]":
        return "", 0
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return data, 0

    tokens = _extract_tokens(obj)
    text = _extract_text(obj)
    return text, tokens


def _extract_tokens(obj: dict[str, Any]) -> int:
    usage = obj.get("usage") or {}
    if isinstance(usage, dict):
        total = usage.get("total_tokens") or usage.get("output_tokens")
        if total:
            return int(total)
    output = obj.get("output") or {}
    if isinstance(output, dict):
        u = output.get("usage") or {}
        if isinstance(u, dict) and u.get("total_tokens"):
            return int(u["total_tokens"])
    return 0


def _extract_text(obj: dict[str, Any]) -> str:
    # OpenAI chat/completions stream
    choices = obj.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        delta = choice.get("delta") or {}
        if isinstance(delta, dict) and delta.get("content"):
            return str(delta["content"])
        msg = choice.get("message") or {}
        if isinstance(msg, dict) and msg.get("content"):
            return str(msg["content"])

    # DashScope generation stream
    output = obj.get("output") or {}
    if isinstance(output, dict):
        text = output.get("text")
        if text:
            return str(text)
        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") or {}
            if isinstance(msg, dict) and msg.get("content"):
                return str(msg["content"])

    return ""
