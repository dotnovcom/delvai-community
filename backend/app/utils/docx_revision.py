"""在原生 docx OOXML 上应用文本修订，保留 run/段落/表格版式。"""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from app.utils.contract_revision import (
    is_applicable_revision,
    locate_text_span_in_sources,
    revision_needle,
)
from app.utils.contract_text import extract_docx_text, normalize_contract_plain_text

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS = {"w": _W_NS}

_DOCX_PARTS = (
    "word/document.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
)
_HEADER_FOOTER_RE = re.compile(r"^word/(header|footer)\d+\.xml$")

ET.register_namespace("w", _W_NS)


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1] if "}" in el.tag else el.tag


@dataclass
class _CharRef:
    elem: ET.Element
    offset: int


@dataclass
class _DocxPart:
    name: str
    root: ET.Element
    plain: str = ""
    refs: list[_CharRef | None] = field(default_factory=list)


def _para_plain_and_refs(para: ET.Element) -> tuple[str, list[_CharRef | None]]:
    plain_parts: list[str] = []
    refs: list[_CharRef | None] = []

    def append_char(ch: str, elem: ET.Element, offset: int) -> None:
        plain_parts.append(ch)
        refs.append(_CharRef(elem, offset))

    def append_virtual(ch: str) -> None:
        plain_parts.append(ch)
        refs.append(None)

    for node in para.iter():
        tag = _tag(node)
        if tag == "t" and node.text:
            for i, ch in enumerate(node.text):
                append_char(ch, node, i)
        elif tag == "tab":
            append_virtual("\t")
        elif tag in ("br", "cr"):
            append_virtual("\n")

    return "".join(plain_parts), refs


def _table_plain_and_refs(table: ET.Element) -> tuple[str, list[_CharRef | None]]:
    parts: list[str] = []
    refs: list[_CharRef | None] = []
    for row in table.findall("w:tr", _NS):
        for cell in row.findall("w:tc", _NS):
            cell_paras = cell.findall("w:p", _NS)
            for pi, para in enumerate(cell_paras):
                p_plain, p_refs = _para_plain_and_refs(para)
                if p_plain:
                    parts.append(p_plain)
                    refs.extend(p_refs)
                if pi < len(cell_paras) - 1:
                    parts.append("\n")
                    refs.append(None)
    return "".join(parts), refs


def _body_plain_and_refs(body: ET.Element) -> tuple[str, list[_CharRef | None]]:
    parts: list[str] = []
    refs: list[_CharRef | None] = []

    def append_block(plain: str, block_refs: list[_CharRef | None]) -> None:
        if not plain and not block_refs:
            return
        if parts:
            parts.append("\n\n")
            refs.extend([None, None])
        parts.append(plain)
        refs.extend(block_refs)

    for child in body:
        tag = _tag(child)
        if tag == "p":
            p_plain, p_refs = _para_plain_and_refs(child)
            append_block(p_plain, p_refs)
        elif tag == "tbl":
            t_plain, t_refs = _table_plain_and_refs(child)
            append_block(t_plain, t_refs)

    return "".join(parts), refs


def _header_footer_plain(root: ET.Element) -> tuple[str, list[_CharRef | None]]:
    parts: list[str] = []
    refs: list[_CharRef | None] = []
    for para in root.findall("w:p", _NS):
        p_plain, p_refs = _para_plain_and_refs(para)
        if not p_plain:
            continue
        if parts:
            parts.append("\n\n")
            refs.extend([None, None])
        parts.append(p_plain)
        refs.extend(p_refs)
    return "".join(parts), refs


def _load_docx_parts(content: bytes) -> list[_DocxPart]:
    parts: list[_DocxPart] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = sorted(
            n
            for n in zf.namelist()
            if n in _DOCX_PARTS or _HEADER_FOOTER_RE.match(n)
        )
        for name in names:
            root = ET.fromstring(zf.read(name))
            body = root.find("w:body", _NS)
            if body is None:
                plain, refs = _header_footer_plain(root)
            else:
                plain, refs = _body_plain_and_refs(body)
            if plain:
                parts.append(_DocxPart(name=name, root=root, plain=plain, refs=refs))
    return parts


def _combined_plain(parts: list[_DocxPart]) -> tuple[str, list[tuple[_DocxPart, int] | None]]:
    """全局 plain 与 (part, local_ref_index) 映射。"""
    plain_parts: list[str] = []
    mapping: list[tuple[_DocxPart, int] | None] = []

    for part in parts:
        if plain_parts:
            plain_parts.append("\n")
            mapping.append(None)
        plain_parts.append(part.plain)
        for i in range(len(part.refs)):
            mapping.append((part, i))
    return "".join(plain_parts), mapping


def _replace_span(mapping: list[tuple[_DocxPart, int] | None], start: int, end: int, replacement: str) -> bool:
    if start < 0 or end <= start or end > len(mapping):
        return False

    span = mapping[start:end]
    char_refs: list[_CharRef] = []
    for item in span:
        if item is None:
            continue
        part, local_idx = item
        ref = part.refs[local_idx]
        if ref is not None:
            char_refs.append(ref)
    if not char_refs:
        return False

    first = char_refs[0]
    first_elem = first.elem
    first_text = first_elem.text or ""
    start_in_first = first.offset

    last = char_refs[-1]
    last_elem = last.elem
    last_text = last_elem.text or ""
    end_in_last = last.offset + 1

    ordered_elems: list[ET.Element] = []
    seen: set[ET.Element] = set()
    for ref in char_refs:
        if ref.elem not in seen:
            seen.add(ref.elem)
            ordered_elems.append(ref.elem)

    if len(ordered_elems) == 1:
        first_elem.text = first_text[:start_in_first] + replacement + first_text[end_in_last:]
        return True

    first_elem.text = first_text[:start_in_first] + replacement
    for elem in ordered_elems[1:-1]:
        elem.text = ""
    if last_elem is first_elem:
        first_elem.text = first_text[:start_in_first] + replacement + first_text[end_in_last:]
    else:
        last_elem.text = last_text[end_in_last:]
    return True


def _serialize_part(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def apply_revisions_to_docx(
    content: bytes,
    contract_text: str,
    annotations: list[dict],
    statuses: dict[str, str],
) -> tuple[bytes, list[str], list[str]]:
    if not content.startswith(b"PK"):
        raise ValueError("仅支持 .docx 格式原生修订导出")

    parts = _load_docx_parts(content)
    if not parts:
        raise ValueError("docx 中未找到可修订的正文")

    docx_plain, mapping = _combined_plain(parts)
    extracted = normalize_contract_plain_text(extract_docx_text(content))
    haystacks = [h for h in [contract_text, extracted, docx_plain] if h]

    to_apply = [ann for ann in annotations if statuses.get(str(ann.get("id", ""))) == "accepted"]
    skipped_ids = [str(ann.get("id")) for ann in to_apply if not is_applicable_revision(ann)]
    applied_ids: list[str] = []

    pending: list[tuple[str, int, int, str]] = []
    for ann in to_apply:
        if not is_applicable_revision(ann):
            continue
        ann_id = str(ann.get("id"))
        needle = revision_needle(ann)
        sources = [
            (contract_text, ann.get("start_offset"), ann.get("end_offset")),
            (extracted, None, None),
            (docx_plain, None, None),
        ]
        located = locate_text_span_in_sources(needle, sources)
        if not located:
            skipped_ids.append(ann_id)
            continue
        _src, (start, end) = located
        if _src is not docx_plain:
            alt = locate_text_span_in_sources(needle, [(docx_plain, None, None)])
            if alt:
                _, (start, end) = alt
            else:
                skipped_ids.append(ann_id)
                continue
        replacement = (ann.get("suggestion") or "").strip()
        if not replacement:
            skipped_ids.append(ann_id)
            continue
        pending.append((ann_id, start, end, replacement))

    pending.sort(key=lambda x: x[1], reverse=True)
    used: list[tuple[int, int]] = []

    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    for ann_id, start, end, replacement in pending:
        if any(overlaps((start, end), u) for u in used):
            skipped_ids.append(ann_id)
            continue
        if _replace_span(mapping, start, end, replacement):
            applied_ids.append(ann_id)
            used.append((start, end))
        else:
            skipped_ids.append(ann_id)

    if not applied_ids:
        return content, applied_ids, skipped_ids

    modified_names = {p.name: p.root for p in parts}
    out_buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as zin, zipfile.ZipFile(out_buf, "w") as zout:
        for item in zin.infolist():
            if item.filename in modified_names:
                zout.writestr(item, _serialize_part(modified_names[item.filename]))
            else:
                zout.writestr(item, zin.read(item.filename))

    return out_buf.getvalue(), applied_ids, skipped_ids
