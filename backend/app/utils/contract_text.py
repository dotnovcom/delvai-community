"""合同正文从 Word/PDF 解析与格式化。"""

from __future__ import annotations

import html as html_module
import io
import re
import zipfile
import xml.etree.ElementTree as ET

_W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_CLAUSE_HEADING_RE = re.compile(r"^第[一二三四五六七八九十百零\d]+条")
_FIELD_LABEL_RE = re.compile(
    r"^(甲方|乙方|法定代表人|地址|电话|邮箱|联系人|统一社会信用代码|开户银行|账号|签订时间|签署时间|日期)[：:]",
)
_SIGN_FOOTER_RE = re.compile(r"(盖章|签字|签署|签订|日期|年月日)")


def _is_short_fragment(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _FIELD_LABEL_RE.match(t):
        return False
    if _SIGN_FOOTER_RE.search(t) and len(t) <= 12:
        return False
    if len(t) <= 2:
        return True
    if len(t) <= 4 and not re.search(r"[。！？；!?;:：]$", t):
        return True
    return False


def _extract_paragraph_text(para: ET.Element) -> str:
    parts: list[str] = []
    for node in para.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag in ("br", "cr"):
            parts.append("\n")
    return "".join(parts).strip()


def _cell_paragraph_texts(cell: ET.Element) -> list[str]:
    texts: list[str] = []
    for para in cell.findall("w:p", _W_NS):
        t = _extract_paragraph_text(para)
        if t:
            texts.append(t)
    return texts


def _extract_table_paragraphs(table: ET.Element) -> list[str]:
    """表格按单元格逐段输出，避免 tab 拼接在富文本编辑器中丢失列内容。"""
    out: list[str] = []
    for row in table.findall("w:tr", _W_NS):
        for cell in row.findall("w:tc", _W_NS):
            cell_texts = _cell_paragraph_texts(cell)
            if not cell_texts:
                continue
            if len(cell_texts) == 1:
                out.append(cell_texts[0])
            else:
                out.extend(cell_texts)
    return out


def _assemble_paragraphs(paragraphs: list[str]) -> str:
    """合并 docx 单字段落，保留条款/段落空行。"""
    merged_lines: list[str] = []
    short_buf = ""

    def flush_short() -> None:
        nonlocal short_buf
        if short_buf:
            merged_lines.append(short_buf)
            short_buf = ""

    for raw in paragraphs:
        line = raw.strip()
        if not line:
            flush_short()
            merged_lines.append("")
            continue
        if _is_short_fragment(line):
            short_buf += line
        else:
            flush_short()
            merged_lines.append(line)
    flush_short()

    blocks: list[str] = []
    block: list[str] = []
    for line in merged_lines:
        if not line:
            if block:
                blocks.append("\n".join(block))
                block = []
        else:
            block.append(line)
    if block:
        blocks.append("\n".join(block))

    return "\n\n".join(blocks)


def extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find("w:body", _W_NS)
    if body is None:
        return ""

    paragraphs: list[str] = []

    def walk(element: ET.Element) -> None:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        if tag == "p":
            text = _extract_paragraph_text(element)
            if text:
                paragraphs.append(text)
            return
        if tag == "tbl":
            paragraphs.extend(_extract_table_paragraphs(element))
            return
        for child in element:
            walk(child)

    for child in body:
        walk(child)

    return _assemble_paragraphs(paragraphs)


_ALIGN_MAP = {
    "center": "center",
    "right": "right",
    "both": "justify",
    "left": "left",
    "start": "left",
    "end": "right",
}


def _escape_html(text: str) -> str:
    return html_module.escape(text, quote=False)


def _run_style_flags(rpr: ET.Element | None) -> dict[str, bool]:
    if rpr is None:
        return {"bold": False, "italic": False, "underline": False}
    return {
        "bold": rpr.find("w:b", _W_NS) is not None,
        "italic": rpr.find("w:i", _W_NS) is not None,
        "underline": rpr.find("w:u", _W_NS) is not None,
    }


def _wrap_run_html(text: str, flags: dict[str, bool]) -> str:
    if not text:
        return ""
    out = _escape_html(text)
    if flags.get("underline"):
        out = f"<u>{out}</u>"
    if flags.get("italic"):
        out = f"<em>{out}</em>"
    if flags.get("bold"):
        out = f"<strong>{out}</strong>"
    return out


def _twips_to_em(twips: int) -> float:
    """Word 首行缩进 twips → em（按 12pt 字号近似）。"""
    return round(twips / 240.0, 2)


def _para_style_attr(para: ET.Element) -> str:
    ppr = para.find("w:pPr", _W_NS)
    if ppr is None:
        return ""
    styles: list[str] = []
    jc = ppr.find("w:jc", _W_NS)
    if jc is not None:
        val = jc.get(f"{{{_W_NS['w']}}}val") or jc.get("w:val") or ""
        align = _ALIGN_MAP.get(val, "")
        if align:
            styles.append(f"text-align:{align}")
    ind = ppr.find("w:ind", _W_NS)
    if ind is not None:
        first_line = ind.get(f"{{{_W_NS['w']}}}firstLine") or ind.get("w:firstLine")
        if first_line:
            try:
                em = _twips_to_em(int(first_line))
                if em > 0:
                    styles.append(f"text-indent:{em}em")
            except ValueError:
                pass
    spacing = ppr.find("w:spacing", _W_NS)
    if spacing is not None:
        before = spacing.get(f"{{{_W_NS['w']}}}before") or spacing.get("w:before")
        after = spacing.get(f"{{{_W_NS['w']}}}after") or spacing.get("w:after")
        if before:
            try:
                styles.append(f"margin-top:{_twips_to_em(int(before))}em")
            except ValueError:
                pass
        if after:
            try:
                styles.append(f"margin-bottom:{_twips_to_em(int(after))}em")
            except ValueError:
                pass
    if not styles:
        return ""
    return f' style="{"; ".join(styles)}"'


def _run_inner_html(run: ET.Element) -> str:
    flags = _run_style_flags(run.find("w:rPr", _W_NS))
    chunks: list[str] = []
    for node in run.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag == "t" and node.text:
            chunks.append(node.text)
        elif tag == "tab":
            chunks.append("\t")
        elif tag in ("br", "cr"):
            chunks.append("\n")
    raw = "".join(chunks)
    if not raw:
        return ""
    parts: list[str] = []
    for segment in raw.split("\n"):
        if segment:
            parts.append(_wrap_run_html(segment.replace("\t", "    "), flags))
        parts.append("<br>")
    if parts and parts[-1] == "<br>":
        parts.pop()
    return "".join(parts)


def _para_to_html(para: ET.Element) -> str:
    inner = "".join(_run_inner_html(r) for r in para.findall("w:r", _W_NS))
    if not inner.strip() and "<br>" not in inner:
        return ""
    style = _para_style_attr(para)
    return f"<p{style}>{inner}</p>"


def _cell_to_html(cell: ET.Element) -> str:
    blocks: list[str] = []
    for para in cell.findall("w:p", _W_NS):
        inner = "".join(_run_inner_html(r) for r in para.findall("w:r", _W_NS))
        if inner.strip() or "<br>" in inner:
            style = _para_style_attr(para)
            blocks.append(f"<p{style}>{inner}</p>")
    return "".join(blocks) if blocks else "<p><br></p>"


def _table_to_html(table: ET.Element) -> str:
    rows: list[str] = []
    for tr in table.findall("w:tr", _W_NS):
        cells = "".join(f"<td>{_cell_to_html(tc)}</td>" for tc in tr.findall("w:tc", _W_NS))
        rows.append(f"<tr>{cells}</tr>")
    return f'<table class="contract-doc-table">{"".join(rows)}</table>'


def _walk_body_to_html(body: ET.Element) -> str:
    parts: list[str] = []

    def walk(element: ET.Element) -> None:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        if tag == "p":
            ph = _para_to_html(element)
            if ph:
                parts.append(ph)
            return
        if tag == "tbl":
            parts.append(_table_to_html(element))
            return
        for child in element:
            walk(child)

    for child in body:
        walk(child)
    return "".join(parts)


def extract_docx_html(content: bytes) -> str:
    """从 docx 提取保留段落对齐、加粗与表格结构的 HTML。"""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find("w:body", _W_NS)
    if body is None:
        return ""
    return _walk_body_to_html(body)


def _plain_to_simple_html(text: str) -> str:
    plain = normalize_contract_plain_text(text)
    if not plain:
        return ""
    blocks = plain.split("\n\n")
    parts: list[str] = []
    for block in blocks:
        lines = block.split("\n")
        inner = "<br>".join(_escape_html(line) for line in lines if line.strip() or len(lines) == 1)
        if inner:
            parts.append(f"<p>{inner}</p>")
    return "".join(parts)


def extract_document_html(content: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "docx":
        try:
            return extract_docx_html(content)
        except Exception:
            return _plain_to_simple_html(extract_docx_text(content))
    if ext in ("txt", "md"):
        return _plain_to_simple_html(content.decode("utf-8", errors="ignore"))
    if ext == "pdf":
        return ""
    return _plain_to_simple_html(content.decode("utf-8", errors="ignore")[:8000])


def normalize_contract_plain_text(text: str) -> str:
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


_CLAUSE_NUM_RE = re.compile(r"第([一二三四五六七八九十百零\d]+)条")
_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _chinese_num_to_int(token: str) -> int | None:
    if not token:
        return None
    if token.isdigit():
        return int(token)
    if token == "十":
        return 10
    if token.startswith("十"):
        tail = token[1:]
        return 10 + (_chinese_num_to_int(tail) or 0)
    if "十" in token:
        left, _, right = token.partition("十")
        tens = _chinese_num_to_int(left) if left else 1
        ones = _chinese_num_to_int(right) if right else 0
        return (tens or 0) * 10 + (ones or 0)
    if len(token) == 1 and token in _CN_DIGIT:
        return _CN_DIGIT[token]
    return None


def parse_clause_index(text: str) -> int | None:
    m = _CLAUSE_NUM_RE.search(text or "")
    if not m:
        return None
    return _chinese_num_to_int(m.group(1))


def _annotation_position_in_text(text: str, needle: str) -> int | None:
    needle = (needle or "").strip()
    if not needle or not text:
        return None
    idx = text.find(needle)
    if idx >= 0:
        return idx
    collapsed = re.sub(r"\s+", " ", needle)
    if len(collapsed) >= 8:
        idx = text.find(collapsed)
        if idx >= 0:
            return idx
    return None


def sort_contract_annotations(annotations: list, contract_text: str) -> list:
    """按风险原文在合同中的出现顺序排序（前→后）。"""

    def sort_key(item: tuple[int, object]) -> tuple:
        index, ann = item
        text = getattr(ann, "text", None) or (ann.get("text") if isinstance(ann, dict) else "") or ""
        category = getattr(ann, "category", None) or (ann.get("category") if isinstance(ann, dict) else "") or ""
        page = getattr(ann, "page", None) or (ann.get("page") if isinstance(ann, dict) else 0) or 0
        paragraph = getattr(ann, "paragraph", None) or (ann.get("paragraph") if isinstance(ann, dict) else 0) or 0

        pos = _annotation_position_in_text(contract_text, text)
        if pos is not None:
            return (0, pos)
        clause = parse_clause_index(category) or parse_clause_index(text)
        if clause is not None:
            return (1, clause)
        return (2, page, paragraph, index)

    indexed = list(enumerate(annotations))
    indexed.sort(key=sort_key)
    return [ann for _, ann in indexed]


def _ann_needle(ann) -> str:
    match = getattr(ann, "match_text", None) or (ann.get("match_text") if isinstance(ann, dict) else None)
    text = getattr(ann, "text", None) or (ann.get("text") if isinstance(ann, dict) else "") or ""
    return (match or text or "").strip()


def _normalize_dedup(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _text_overlap_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if shorter in longer:
        return len(shorter) / len(longer)
    common = 0
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            break
        common += 1
    return common / max(len(a), len(b))


def _revision_applicable(ann) -> bool:
    if isinstance(ann, dict):
        if ann.get("revision_applicable") is False:
            return False
        return bool((ann.get("suggestion") or "").strip())
    if getattr(ann, "revision_applicable", True) is False:
        return False
    return bool((getattr(ann, "suggestion", None) or "").strip())


def deduplicate_contract_annotations(annotations: list, contract_text: str) -> list:
    """去除宽泛条目对子条款的重复覆盖，保留更精确的一条。"""
    sorted_ann = sort_contract_annotations(annotations, contract_text)
    kept: list = []

    for ann in sorted_ann:
        needle = _normalize_dedup(_ann_needle(ann))
        if len(needle) < 8:
            kept.append(ann)
            continue

        dominated = False
        for i in range(len(kept) - 1, -1, -1):
            existing = kept[i]
            exist_needle = _normalize_dedup(_ann_needle(existing))
            if len(exist_needle) < 8:
                continue

            if len(needle) > len(exist_needle) and exist_needle in needle:
                dominated = True
                break
            if len(needle) < len(exist_needle) and needle in exist_needle:
                kept.pop(i)
                continue

            overlap = _text_overlap_ratio(needle, exist_needle)
            if overlap >= 0.65:
                if len(needle) > len(exist_needle):
                    dominated = True
                    break
                if len(needle) < len(exist_needle):
                    kept.pop(i)
                elif _revision_applicable(existing) and not _revision_applicable(ann):
                    dominated = True
                    break
                elif not _revision_applicable(existing) and _revision_applicable(ann):
                    kept.pop(i)
                else:
                    dominated = True
                    break

        if not dominated:
            kept.append(ann)

    return kept
