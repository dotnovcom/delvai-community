"""合同修订匹配逻辑（与 web/src/utils/contractRevision.ts 对齐）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

RevisionStatus = Literal["pending", "accepted", "rejected"]

MIN_REVISION_MATCH_LEN = 8
PARTY_INFO_RE = re.compile(r"^(甲方|乙方)[：:]|法定代表人|地址[：:]|电话[：:]|邮箱[：:]")
CLAUSE_NUM_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)")


def revision_needle(ann: dict[str, Any]) -> str:
    return (ann.get("match_text") or ann.get("text") or "").strip()


def _extract_clause_prefix(text: str) -> str | None:
    m = CLAUSE_NUM_PREFIX_RE.match(text.strip())
    return m.group(1) if m else None


def is_revision_pair_consistent(original: str, suggestion: str) -> bool:
    orig = original.strip()
    nxt = suggestion.strip()
    if not orig or not nxt:
        return False
    o_prefix = _extract_clause_prefix(orig)
    s_prefix = _extract_clause_prefix(nxt)
    if o_prefix and s_prefix and o_prefix != s_prefix:
        orig_is_heading_only = bool(re.match(r"^[\d.]+\s*[\u4e00-\u9fa5]{0,8}[：:]\s*$", orig))
        if not orig_is_heading_only:
            return False
    if PARTY_INFO_RE.search(orig) and CLAUSE_NUM_PREFIX_RE.search(nxt):
        return False
    return True


def is_applicable_revision(ann: dict[str, Any]) -> bool:
    if ann.get("revision_applicable") is False:
        return False
    text = revision_needle(ann)
    suggestion = (ann.get("suggestion") or "").strip()
    if not suggestion or suggestion == text:
        return False
    if len(text) < MIN_REVISION_MATCH_LEN:
        return False
    result_type = ann.get("result_type")
    if result_type and result_type in ("通过", "需删除"):
        return False
    return is_revision_pair_consistent(text, suggestion)


def _normalize_punctuation(text: str) -> str:
    return (
        text.replace(""", '"')
        .replace(""", '"')
        .replace("'", "'")
        .replace("'", "'")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("；", ";")
        .replace("，", ",")
        .replace("。", ".")
    )


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_for_compare(text: str) -> str:
    return _collapse_spaces(_normalize_punctuation(text))


def _needle_candidates(needle: str) -> list[str]:
    raw = (needle or "").strip()
    if not raw or len(raw) < MIN_REVISION_MATCH_LEN:
        return []
    out: list[str] = []

    def add(v: str | None) -> None:
        t = (v or "").strip()
        if t and len(t) >= MIN_REVISION_MATCH_LEN and t not in out:
            out.append(t)

    add(raw)
    add(_normalize_punctuation(raw))
    add(_collapse_spaces(raw))
    add(_collapse_spaces(_normalize_punctuation(raw)))
    return out


def _has_trusted_offset(start: int | None, end: int | None) -> bool:
    return start is not None and end is not None and start > 0 and end > start


def verify_text_span(haystack: str, start: int, end: int, needle: str) -> bool:
    if start < 0 or end <= start or end > len(haystack):
        return False
    slice_ = haystack[start:end]
    if not slice_.strip():
        return False
    norm_slice = _normalize_for_compare(slice_)
    norm_needle = _normalize_for_compare(needle)
    if not norm_needle:
        return False
    if norm_slice == norm_needle:
        return True
    if norm_slice in norm_needle or norm_needle in norm_slice:
        shorter = min(len(norm_slice), len(norm_needle))
        longer = max(len(norm_slice), len(norm_needle))
        return shorter / longer >= 0.85
    return False


def _find_exact_matches(haystack: str, candidate: str) -> list[tuple[int, int]]:
    matches: list[tuple[int, int]] = []
    from_idx = 0
    while from_idx < len(haystack):
        idx = haystack.find(candidate, from_idx)
        if idx < 0:
            break
        matches.append((idx, idx + len(candidate)))
        from_idx = idx + 1
    return matches


def _find_regex_matches(haystack: str, candidate: str) -> list[tuple[int, int]]:
    pattern = re.escape(candidate).replace(r"\ ", r"\s+")
    matches: list[tuple[int, int]] = []
    for m in re.finditer(pattern, haystack):
        matches.append((m.start(), m.end()))
    return matches


def _pick_unique_verified_span(
    haystack: str,
    matches: list[tuple[int, int]],
    needle: str,
) -> tuple[int, int] | None:
    verified = [span for span in matches if verify_text_span(haystack, span[0], span[1], needle)]
    if len(verified) == 1:
        return verified[0]
    return None


def locate_text_span(
    haystack: str,
    needle: str,
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> tuple[int, int] | None:
    if not haystack or not (needle or "").strip():
        return None
    raw = needle.strip()
    if len(raw) < MIN_REVISION_MATCH_LEN:
        return None

    if _has_trusted_offset(start_offset, end_offset):
        assert start_offset is not None and end_offset is not None
        if end_offset <= len(haystack) and verify_text_span(haystack, start_offset, end_offset, raw):
            return start_offset, end_offset

    for candidate in _needle_candidates(raw):
        exact = _pick_unique_verified_span(haystack, _find_exact_matches(haystack, candidate), raw)
        if exact:
            return exact
        regex = _pick_unique_verified_span(haystack, _find_regex_matches(haystack, candidate), raw)
        if regex:
            return regex
    return None


def locate_text_span_in_sources(
    needle: str,
    sources: list[tuple[str, int | None, int | None]],
) -> tuple[str, tuple[int, int]] | None:
    """在多个文本源中定位 needle，返回 (haystack, span)。"""
    for haystack, start_offset, end_offset in sources:
        if not haystack:
            continue
        span = locate_text_span(haystack, needle, start_offset, end_offset)
        if span and verify_text_span(haystack, span[0], span[1], needle):
            return haystack, span
    return None


@dataclass
class RevisionSpan:
    ann_id: str
    start: int
    end: int
    replacement: str


def collect_revision_spans(
    contract_text: str,
    annotations: list[dict[str, Any]],
    statuses: dict[str, str],
    *,
    extra_haystacks: list[str] | None = None,
) -> list[RevisionSpan]:
    to_apply = [
        ann
        for ann in annotations
        if statuses.get(str(ann.get("id", ""))) == "accepted" and is_applicable_revision(ann)
    ]
    if not to_apply:
        return []

    sources: list[tuple[str, int | None, int | None]] = [(contract_text, None, None)]
    for alt in extra_haystacks or []:
        if alt and alt not in [s[0] for s in sources]:
            sources.append((alt, None, None))

    matched: list[tuple[dict[str, Any], str, tuple[int, int]]] = []
    for ann in to_apply:
        needle = revision_needle(ann)
        located = locate_text_span_in_sources(
            needle,
            [(contract_text, ann.get("start_offset"), ann.get("end_offset"))]
            + [(alt, None, None) for alt in (extra_haystacks or []) if alt],
        )
        if located:
            haystack, span = located
            matched.append((ann, haystack, span))

    matched.sort(key=lambda x: x[2][0], reverse=True)

    used: list[tuple[int, int]] = []
    spans: list[RevisionSpan] = []

    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    for ann, _haystack, (start, end) in matched:
        if any(overlaps((start, end), u) for u in used):
            continue
        replacement = (ann.get("suggestion") or "").strip()
        if not replacement:
            continue
        spans.append(RevisionSpan(ann_id=str(ann.get("id")), start=start, end=end, replacement=replacement))
        used.append((start, end))
    return spans
