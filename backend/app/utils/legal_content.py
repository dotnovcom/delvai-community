"""法律咨询助手回复清洗（法睿 referInfo、引用 JSON 碎片）。"""

from __future__ import annotations

import re

# 标准 / 残缺 referInfo 标签块
_REFER_PAREN_BLOCK = re.compile(
    r"<referInfo[^>]*>\s*\([\s\S]*?\)\s*</referInfo\w*>?",
    re.IGNORECASE,
)
_REFER_BLOCK = re.compile(
    r"<referInfo[^>]*>[\s\S]*?</referInfo\w*>?",
    re.IGNORECASE,
)
_REFER_BLOCK_LOOSE = re.compile(
    r"<referInfo[^>]*>[\s\S]*?</referInfo",
    re.IGNORECASE,
)
_REFER_OPEN_TAIL = re.compile(r"<referInfo[^>]*>[\s\S]*$", re.IGNORECASE)
_ORPHAN_REFER_TAG = re.compile(r"</?referInfo\w*>?", re.IGNORECASE)

# {"type":"lawItem"|"case"|"law" ...} 或 {{"type":...}} 或 [{"type":"law",...}]
_CITE_JSON_START = re.compile(
    r'\{\{?\s*\{?"type"\s*:\s*"(?:lawItem|case|law)"',
    re.IGNORECASE,
)
_CITE_JSON_ARRAY_START = re.compile(
    r'\[\s*\{\s*"type"\s*:\s*"(?:lawItem|case|law)"',
    re.IGNORECASE,
)
_REFER_ARRAY_BLOCK = re.compile(
    r"<referInfo[^>]*>\s*\[[\s\S]*?\]\s*</referInfo\w*>?",
    re.IGNORECASE,
)
_REFER_ARRAY_OPEN = re.compile(
    r"<referInfo[^>]*>\s*\[[\s\S]*?(?:\]\s*(?:</referInfo\w*>?|$))",
    re.IGNORECASE,
)


def _brace_block_end(text: str, open_pos: int) -> int:
    """从 text[open_pos] 的 `{` 起匹配到成对闭合 `}`，失败返回 len(text)。"""
    if open_pos >= len(text) or text[open_pos] != "{":
        return open_pos
    depth = 0
    i = open_pos
    in_str: str | None = None
    escape = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def _strip_cite_json_array_blobs(text: str) -> str:
    """移除裸露的法睿引用 JSON 数组（如 [{\"type\":\"law\",...}]）。"""
    while True:
        m = _CITE_JSON_ARRAY_START.search(text)
        if not m:
            break
        start = m.start()
        depth = 0
        end = start
        in_str: str | None = None
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
                continue
            if ch in ('"', "'"):
                in_str = ch
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end <= start:
            text = text[: m.start()] + text[m.end() :]
            continue
        text = text[:start] + text[end:]
    return text


def _strip_cite_json_blobs(text: str) -> str:
    """移除裸露的法睿引用 JSON（含 {{...}}、半残缺片段）。"""
    while True:
        m = _CITE_JSON_START.search(text)
        if not m:
            break
        start = m.start()
        while start > 0 and text[start - 1] in "({":
            start -= 1
        brace_pos = text.find("{", start)
        if brace_pos < 0:
            text = text[: m.start()] + text[m.end() :]
            continue
        end = _brace_block_end(text, brace_pos)
        # 吞掉紧随其后的 ) 或 }}
        while end < len(text) and text[end] in ")} \t":
            if text[end] == ")":
                end += 1
                break
            if text[end] == "}":
                end += 1
                continue
            if text[end] in " \t":
                end += 1
                continue
            break
        text = text[:start] + text[end:]
    return text


def _strip_json_field_fragments(text: str) -> str:
    """清理 referInfo 被截断后残留的 key:value 碎片。"""
    patterns = [
        r',?\s*"(?:type|lawName|lawItemName|timeliness|lawItemId|caseNo|eContent|lawId|title|content)"\s*:\s*"[^"]*"',
        r',?\s*"(?:type|lawName|lawItemName|timeliness|lawItemId|caseNo|eContent|lawId|title|content)"\s*:\s*[^,\s\}]+',
        r'\w+":"[^"]*"(?=\s*[,，。\)]|$)',
    ]
    out = text
    for pat in patterns:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    return out


def normalize_legal_plain_text(text: str | None) -> str:
    """法规/案例正文：还原字面量换行符，去掉 null 等脏前缀。"""
    if text is None:
        return ""
    out = str(text).strip()
    if out.lower() in ("null", "undefined", "none"):
        return ""
    out = out.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n").replace("\\t", " ")
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = re.sub(r"^(?:null\s*)+", "", out, flags=re.IGNORECASE)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


_WIKI_CITE_OPEN = re.compile(r"\[\[([^\]]{1,200})\]\]\(")
_LAW_SOURCE_FIELD = re.compile(r'"lawSourceContent"\s*:\s*"((?:\\.|[^"\\])*)"')
_DETAIL_MARK = "<<<DETAIL>>>"


def _unescape_json_string(raw: str) -> str:
    return (
        raw.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", " ")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
        .strip()
    )


def _extract_law_source(blob: str) -> str:
    match = _LAW_SOURCE_FIELD.search(blob or "")
    if not match:
        return ""
    return _unescape_json_string(match.group(1))


def keep_latest_rewrite(text: str) -> str:
    """流式拼接会把法睿每次改写的全文再接一遍。保留最后一次完整稿。"""
    body = (text or "").strip()
    if len(body) < 80:
        return body
    sentence = re.match(r".{12,90}?。", body)
    anchor = sentence.group(0) if sentence else body[:24]
    if len(anchor) < 12:
        return body
    index = body.rfind(anchor)
    if index > 20:
        return body[index:].strip()
    return body


def lift_wiki_law_cites(text: str, *, attach_sources: bool = True) -> str:
    """把 [[法规]]({lawSourceContent}) 转成可读引用，条文全文放到详细依据。"""
    if "[[" not in text:
        return text
    parts: list[str] = []
    sources: list[tuple[str, str]] = []
    cursor = 0
    while True:
        match = _WIKI_CITE_OPEN.search(text, cursor)
        if not match:
            parts.append(text[cursor:])
            break
        parts.append(text[cursor : match.start()])
        label = re.sub(r"\s+", " ", match.group(1)).strip()
        pos = match.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos < len(text) and text[pos] == "{":
            end = _brace_block_end(text, pos)
            source = _extract_law_source(text[pos:end])
            if end < len(text) and text[end] == ")":
                end += 1
            cursor = end
        else:
            source = ""
            cursor = match.end()
        parts.append(f"《{label}》")
        if source:
            sources.append((label, source))
    body = "".join(parts)
    body = re.sub(r"《([^》]{1,200})》(?:\s*《\1》)+", r"《\1》", body)
    if not sources or not attach_sources:
        return body
    lines = [body.rstrip(), "", _DETAIL_MARK, "法条原文"]
    seen: set[str] = set()
    for label, source in sources:
        key = f"{label}\n{source}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"\n**{label}**\n\n{source}")
    return "\n".join(lines).strip()


def strip_refer_info_tags(text: str, *, strip_trailing_open: bool = False) -> str:
    """移除法睿 referInfo 与引用 JSON，保留可读正文。"""
    if not text:
        return ""
    cleaned = text
    for pat in (_REFER_PAREN_BLOCK, _REFER_ARRAY_BLOCK, _REFER_ARRAY_OPEN, _REFER_BLOCK, _REFER_BLOCK_LOOSE):
        cleaned = pat.sub("", cleaned)
    cleaned = _ORPHAN_REFER_TAG.sub("", cleaned)
    cleaned = _strip_cite_json_array_blobs(cleaned)
    cleaned = _strip_cite_json_blobs(cleaned)
    cleaned = _strip_json_field_fragments(cleaned)
    if strip_trailing_open:
        cleaned = _REFER_OPEN_TAIL.sub("", cleaned)
        cleaned = _strip_cite_json_array_blobs(cleaned)
        cleaned = _strip_cite_json_blobs(cleaned)
        cleaned = _strip_json_field_fragments(cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _clip_unclosed_wiki(text: str) -> str:
    open_pos = text.rfind("[[")
    if open_pos < 0:
        return text
    if "]]" not in text[open_pos:]:
        return text[:open_pos]
    return text


def prepare_stream_snapshot(text: str) -> str:
    """流式展示用：去掉未写完的引用代码，不把法条原文拼进正文。"""
    clipped = _clip_unclosed_wiki(text or "")
    lifted = lift_wiki_law_cites(clipped, attach_sources=False)
    cleaned = strip_refer_info_tags(lifted, strip_trailing_open=True)
    return keep_latest_rewrite(cleaned)


_SECOND_SECTION = re.compile(r"\n(?:#{1,3}[ \t]*)?二、")


def split_legal_answer(text: str) -> tuple[str, str]:
    """结论保留到全国性规则，地方补充和法条原文留给详情。"""
    raw = text or ""
    mark = raw.find(_DETAIL_MARK)
    if mark >= 0:
        body = raw[:mark].strip()
        appendix = raw[mark + len(_DETAIL_MARK) :].strip()
    else:
        body, appendix = raw.strip(), ""
    summary = body
    rest = ""
    heading = _SECOND_SECTION.search(body)
    if heading and heading.start() >= 180:
        summary = body[: heading.start()].strip()
        rest = body[heading.start() :].strip()
    detail = "\n\n".join(part for part in (rest, appendix) if part).strip()
    if not summary:
        summary = body or appendix
        if summary == appendix:
            detail = ""
    if detail.strip() == summary.strip():
        detail = ""
    return summary, detail


def polish_legal_assistant_content(text: str) -> str:
    """保存与 API 下发前统一清洗。"""
    normalized = keep_latest_rewrite(normalize_legal_plain_text(text))
    lifted = lift_wiki_law_cites(normalized)
    return strip_refer_info_tags(lifted, strip_trailing_open=False)


def truncate_legal_excerpt(text: str, max_len: int = 1200) -> str:
    """法规/案例摘要截断：尽量在句号处断开，避免条文显示半句。"""
    cleaned = polish_legal_assistant_content(text or "")
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len]
    for sep in ("。", "；", "\n", "，", ". "):
        pos = cut.rfind(sep)
        if pos >= max_len // 2:
            return cut[: pos + len(sep)].rstrip()
    return cut.rstrip() + "…"
