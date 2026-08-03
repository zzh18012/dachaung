"""自动指标：13 项 + 计时占位。

设计原则：
- 纯函数：输入是已解析的 document dict（来自 process_single 返回的 Document.to_dict()）
  或 None（pipeline 失败），输出 metrics dict
- 缺数据时返回 null + reason，不伪造
- 比例指标分母为 0 时返回 null + reason，不返回 1.0
- text_char_multiset_* 用 Counter（多集合）保留重复字符信息
- 不修改 document
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

from app.chunkers.structural import normalize_text

# 文本元素类型（参与"不丢不重"文本比对；image 不参与）
_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")
# 需要 bbox 的 PDF 文本类型
_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")

_NOT_EVALUATED = "not_evaluated"


def _null(reason: str) -> dict[str, Any]:
    """构造一个 null 指标项：{value: null, reason: ...}。"""
    return {"value": None, "reason": reason}


def _ratio(value: float) -> dict[str, Any]:
    """构造一个 ratio 指标项：{value: 0.0..1.0}。"""
    return {"value": float(value), "reason": None}


def _bool_metric(value: bool) -> dict[str, Any]:
    return {"value": bool(value), "reason": None}


def _int_metric(value: int) -> dict[str, Any]:
    return {"value": int(value), "reason": None}


def compute_automatic_metrics(
    document: dict[str, Any] | None,
    error: dict[str, Any] | None,
    source_type: str,
    expectations: dict[str, Any] | None,
    image_base_dir: Path | None = None,
) -> dict[str, Any]:
    """计算一份文档的全部自动指标。

    Args:
        document: process_single 成功时返回的 Document.to_dict()；失败时 None
        error: 失败时的 ErrorRecord.to_dict()；成功时 None
        source_type: "pdf" 或 "docx"
        expectations: manifest 中该文档的 expectations 子节点（可为 None）
        image_base_dir: 图片资源根目录（用于校验 resource_path 是否存在）；
            若 None，则用 resource_path 字符串原样校验（按相对/绝对原值）
    """
    metrics: dict[str, Any] = {}

    # 1. pipeline_success + 3. error_code
    pipeline_success = error is None and document is not None
    metrics["pipeline_success"] = _bool_metric(pipeline_success)
    metrics["error_code"] = (
        {"value": error["code"] if error else None, "reason": None}
    )

    # 2. schema_valid：仅当 document 存在时才校验
    if document is None:
        metrics["schema_valid"] = _null("pipeline_failed")
    else:
        # 延迟 import 避免循环依赖
        from evaluation.schema_validation import document_passes_schema
        try:
            ok = document_passes_schema(document)
            metrics["schema_valid"] = _bool_metric(ok)
        except Exception as e:
            metrics["schema_valid"] = {
                "value": False,
                "reason": f"schema_check_exception:{type(e).__name__}",
            }

    # 后续指标都需要 document；失败时统一返回 null
    if document is None:
        for name in (
            "element_count_total",
            "element_count_by_type",
            "pdf_locator_valid_ratio",
            "docx_locator_valid_ratio",
            "image_resource_exists_ratio",
            "chunk_reference_intact_ratio",
            "text_preservation_equal",
            "text_char_multiset_precision",
            "text_char_multiset_recall",
            "heading_boundary_compliance",
            "silent_drop_count",
        ):
            metrics[name] = _null("pipeline_failed")
        return metrics

    elements = document.get("elements", [])
    chunks = document.get("chunks", [])

    # 4. element_count_total
    metrics["element_count_total"] = _int_metric(len(elements))

    # 5. element_count_by_type
    by_type: dict[str, int] = {}
    for e in elements:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    metrics["element_count_by_type"] = {"value": by_type, "reason": None}

    # 6. pdf_locator_valid_ratio
    if source_type == "pdf":
        metrics["pdf_locator_valid_ratio"] = _pdf_locator_ratio(elements)
    else:
        metrics["pdf_locator_valid_ratio"] = _null("not_pdf_document")

    # 7. docx_locator_valid_ratio
    if source_type == "docx":
        metrics["docx_locator_valid_ratio"] = _docx_locator_ratio(elements)
    else:
        metrics["docx_locator_valid_ratio"] = _null("not_docx_document")

    # 8. image_resource_exists_ratio
    metrics["image_resource_exists_ratio"] = _image_resource_ratio(
        elements, image_base_dir
    )

    # 9. chunk_reference_intact_ratio
    metrics["chunk_reference_intact_ratio"] = _chunk_reference_ratio(elements, chunks)

    # 10/11/12. 文本保留
    text_metrics = _text_preservation(elements, chunks)
    metrics["text_preservation_equal"] = text_metrics["equal"]
    metrics["text_char_multiset_precision"] = text_metrics["precision"]
    metrics["text_char_multiset_recall"] = text_metrics["recall"]

    # 13. heading_boundary_compliance
    metrics["heading_boundary_compliance"] = _heading_boundary_ratio(elements, chunks)

    # 14. silent_drop_count
    metrics["silent_drop_count"] = _silent_drop_count(by_type, expectations)

    return metrics


# ---------- 子函数 ----------


def _pdf_locator_ratio(elements: list[dict]) -> dict[str, Any]:
    """PDF：page≥1（所有元素）；文本类型还需要 bbox=4 个有限数。"""
    if not elements:
        return _null("no_elements")
    valid = 0
    for e in elements:
        loc = e.get("source_locator") or {}
        page = loc.get("page")
        if not isinstance(page, int) or page < 1:
            continue
        if e.get("type") in _PDF_BBOX_REQUIRED_TYPES:
            bbox = loc.get("bbox")
            if not _is_valid_bbox(bbox):
                continue
        valid += 1
    return _ratio(valid / len(elements))


def _docx_locator_ratio(elements: list[dict]) -> dict[str, Any]:
    """DOCX：locator 不能有 page/bbox；至少一个结构键。"""
    if not elements:
        return _null("no_elements")
    structural_keys = (
        "section",
        "paragraph_index",
        "run_index",
        "table_index",
        "row_index",
        "col_index",
        "relationship_id",
    )
    valid = 0
    for e in elements:
        loc = e.get("source_locator") or {}
        if "page" in loc or "bbox" in loc:
            continue
        if not any(k in loc for k in structural_keys):
            continue
        valid += 1
    return _ratio(valid / len(elements))


def _is_valid_bbox(bbox: Any) -> bool:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return False
    for v in bbox:
        if isinstance(v, bool):
            return False
        if not isinstance(v, (int, float)):
            return False
        if not math.isfinite(v):
            return False
    return True


def _image_resource_ratio(
    elements: list[dict], image_base_dir: Path | None
) -> dict[str, Any]:
    """image element 的 resource_path 文件实存率。

    parser 保存图片时把完整相对路径（或绝对路径）写入 resource_path，
    所以默认直接用 Path(rp)；如果失败再尝试用 image_base_dir 拼接（应对只写文件名的情况）。
    """
    images = [e for e in elements if e.get("type") == "image"]
    if not images:
        return _null("no_image_elements")
    valid = 0
    for img in images:
        rp = img.get("resource_path")
        if not rp:
            continue
        candidates: list[Path] = [Path(rp)]
        # 如果原始 rp 不是绝对路径，且 image_base_dir 给了，也尝试拼接（兼容只写文件名的 parser）
        if image_base_dir is not None:
            candidates.append(image_base_dir / Path(rp).name)
        ok = False
        for p in candidates:
            try:
                if p.is_file() and p.stat().st_size > 0:
                    ok = True
                    break
            except OSError:
                continue
        if ok:
            valid += 1
    return _ratio(valid / len(images))


def _chunk_reference_ratio(
    elements: list[dict], chunks: list[dict]
) -> dict[str, Any]:
    if not chunks:
        return _null("no_chunks")
    elem_ids = {e.get("element_id") for e in elements}
    valid = 0
    for c in chunks:
        ids = c.get("source_element_ids") or []
        if ids and all(sid in elem_ids for sid in ids):
            valid += 1
    return _ratio(valid / len(chunks))


def _text_preservation(
    elements: list[dict], chunks: list[dict]
) -> dict[str, Any]:
    """文本保留：完全相等 + 字符多集合 precision/recall。

    image 不参与（chunker._element_text 返回 ""）。
    """
    expected = " ".join(
        e.get("content") or ""
        for e in elements
        if e.get("type") != "image"
    )
    actual = " ".join(c.get("text") or "" for c in chunks)

    norm_expected = normalize_text(expected)
    norm_actual = normalize_text(actual)

    # 完全相等
    equal = norm_expected == norm_actual
    equal_metric = _bool_metric(equal)

    # 字符多集合
    if not norm_expected and not norm_actual:
        # 都为空：precision/recall 形式上为 1，但语义上"无内容可比"，记 null
        precision_metric = _null("empty_expected_and_actual")
        recall_metric = _null("empty_expected_and_actual")
    else:
        c_expected = Counter(norm_expected)
        c_actual = Counter(norm_actual)
        # 多集合交集：每个字符取 min
        common = sum((c_expected & c_actual).values())
        # precision = common / |actual|
        if sum(c_actual.values()) == 0:
            precision_metric = _null("empty_actual")
        else:
            precision_metric = _ratio(common / sum(c_actual.values()))
        # recall = common / |expected|
        if sum(c_expected.values()) == 0:
            recall_metric = _null("empty_expected")
        else:
            recall_metric = _ratio(common / sum(c_expected.values()))

    return {
        "equal": equal_metric,
        "precision": precision_metric,
        "recall": recall_metric,
    }


def _heading_boundary_ratio(
    elements: list[dict], chunks: list[dict]
) -> dict[str, Any]:
    """heading → chunk 起始的合规率。

    一个 heading 视为"合规"当且仅当存在某个 chunk，其 source_element_ids
    非空且第一个等于该 heading 的 element_id（heading 是 chunk 的首元素）。
    """
    headings = [e for e in elements if e.get("type") == "heading"]
    if not headings:
        return _null("no_heading_elements")
    # 收集每个 chunk 的首个 source_element_id
    chunk_first_ids = set()
    for c in chunks:
        ids = c.get("source_element_ids") or []
        if ids:
            chunk_first_ids.add(ids[0])
    matched = sum(1 for h in headings if h.get("element_id") in chunk_first_ids)
    return _ratio(matched / len(headings))


def _silent_drop_count(
    by_type: dict[str, int], expectations: dict[str, Any] | None
) -> dict[str, Any]:
    """silent_drop_count = Σ max(0, expected - actual) over types。

    无 expectations 时返回 null。
    """
    if not expectations:
        return _null("no_expectations")
    expected_counts = expectations.get("element_count_by_type") or {}
    if not expected_counts:
        return _null("no_expectations_element_count")
    drops = 0
    for t, exp in expected_counts.items():
        actual = by_type.get(t, 0)
        if actual < exp:
            drops += (exp - actual)
    return _int_metric(drops)


__all__ = ["compute_automatic_metrics"]
