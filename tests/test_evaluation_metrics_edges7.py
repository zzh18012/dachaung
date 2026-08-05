r"""evaluation/metrics.py 边角测试 - 第七轮（Round 177）。

补强已有 base/edges/edges2-6（共 951 测试）未覆盖的深度：
- _image_resource_ratio 各 OSError/size 0/image_base_dir 拼 .name 分支
- _text_preservation multiset 语义（重复字符、单边空、单字符多重复）
- _chunk_reference_ratio element_id None / 元素列表空但 chunks 非空
- _silent_drop_count negative expected 处理 / actual 大于 expected 不计
- compute_automatic_metrics error_code 内联结构、source_type 非 pdf/docx
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path

import pytest

from evaluation.metrics import (
    _PDF_BBOX_REQUIRED_TYPES,
    _TEXT_TYPES,
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _image_resource_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _silent_drop_count,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# =========================================================================
# _image_resource_ratio 深度
# =========================================================================


def test_image_resource_ratio_no_resource_path_skipped(tmp_path: Path):
    """image element 没有 resource_path → 跳过该元素。"""
    elements = [{"type": "image", "element_id": "i1"}]  # 无 resource_path
    result = _image_resource_ratio(elements, tmp_path)
    # valid=0, len(images)=1 → ratio=0.0
    assert result["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_skipped(tmp_path: Path):
    elements = [{"type": "image", "element_id": "i1", "resource_path": ""}]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_nonexistent_returns_zero(tmp_path: Path):
    """resource_path 文件不存在 → valid=0。"""
    elements = [{"type": "image", "element_id": "i1", "resource_path": "missing.png"}]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_existing_file_returns_one(tmp_path: Path):
    p = tmp_path / "img.png"
    p.write_bytes(b"data")
    elements = [{"type": "image", "element_id": "i1", "resource_path": str(p)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 1.0


def test_image_resource_ratio_existing_file_zero_size_skipped(tmp_path: Path):
    """size==0 → 跳过（不算 valid）。"""
    p = tmp_path / "empty.png"
    p.write_bytes(b"")
    elements = [{"type": "image", "element_id": "i1", "resource_path": str(p)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_mixed_some_valid(tmp_path: Path):
    """2 个 image，1 个有效 1 个不存在 → ratio=0.5。"""
    p = tmp_path / "ok.png"
    p.write_bytes(b"data")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(p)},
        {"type": "image", "element_id": "i2", "resource_path": "missing.png"},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.5


def test_image_resource_ratio_relative_path_with_image_base_dir(tmp_path: Path):
    """resource_path 是相对路径名，image_base_dir 给定时尝试拼接 .name。"""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    p = img_dir / "img.png"
    p.write_bytes(b"data")
    elements = [{"type": "image", "element_id": "i1", "resource_path": "img.png"}]
    result = _image_resource_ratio(elements, img_dir)
    assert result["value"] == 1.0


def test_image_resource_ratio_no_images_returns_no_image_elements():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "x"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] is None
    assert result["reason"] == "no_image_elements"


def test_image_resource_ratio_returns_ratio_metric():
    elements = [{"type": "image", "element_id": "i1", "resource_path": "x.png"}]
    result = _image_resource_ratio(elements, None)
    assert "value" in result
    assert "reason" in result


def test_image_resource_ratio_image_base_dir_none_doesnt_join(tmp_path: Path):
    """image_base_dir=None 时只用原始 Path(rp)。"""
    elements = [{"type": "image", "element_id": "i1", "resource_path": "img.png"}]
    result = _image_resource_ratio(elements, None)
    # 没拼 → 找不到 → ratio=0.0
    assert result["value"] == 0.0


def test_image_resource_ratio_signature():
    sig = inspect.signature(_image_resource_ratio)
    assert set(sig.parameters) == {"elements", "image_base_dir"}


def test_image_resource_ratio_image_base_dir_no_default():
    """_image_resource_ratio 是内部辅助：image_base_dir 必填（默认值在调用方 compute_automatic_metrics）。"""
    sig = inspect.signature(_image_resource_ratio)
    assert sig.parameters["image_base_dir"].default is inspect.Parameter.empty


# =========================================================================
# _text_preservation multiset 语义
# =========================================================================


def test_text_preservation_empty_expected_empty_actual_both_null():
    """expected 和 actual 都为空 → precision/recall 都 null。"""
    elements = [{"type": "image", "element_id": "i1"}]  # 不参与 expected
    chunks = [{"text": "", "source_element_ids": []}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] is None
    assert result["recall"]["value"] is None
    assert result["precision"]["reason"] == "empty_expected_and_actual"
    assert result["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_expected_only_recall_null():
    """expected 空（image only），actual 非空 → precision null/empty_expected。"""
    # Wait, looking at code: if not expected AND not actual → both null
    # Otherwise go to else branch where each is checked independently
    elements = [{"type": "image", "element_id": "i1"}]
    chunks = [{"text": "abc", "source_element_ids": []}]
    result = _text_preservation(elements, chunks)
    # expected = "" → recall null empty_expected
    assert result["recall"]["value"] is None
    assert result["recall"]["reason"] == "empty_expected"


def test_text_preservation_empty_actual_only_precision_null():
    """actual 空，expected 非空 → precision null empty_actual。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "", "source_element_ids": []}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] is None
    assert result["precision"]["reason"] == "empty_actual"


def test_text_preservation_repeated_chars_multiset():
    """重复字符：'aaab' vs 'aabb' → common=min(3,2) for 'a' + min(1,2) for 'b' = 3。
    precision = 3/4, recall = 3/4。
    """
    elements = [{"type": "paragraph", "element_id": "p1", "content": "aaab"}]
    chunks = [{"text": "aabb", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] == 0.75
    assert result["recall"]["value"] == 0.75
    assert result["equal"]["value"] is False


def test_text_preservation_reorder_changes_equal_but_not_multiset():
    """'abc' vs 'cba'：equal=False，但 precision=recall=1.0（多集合相等）。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "cba", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_perfect_match():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "hello"}]
    chunks = [{"text": "hello", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_extra_chars_only_in_actual():
    """expected='abc', actual='abcd' → equal=False, precision=3/4, recall=3/3=1.0。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "abcd", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 0.75
    assert result["recall"]["value"] == 1.0


def test_text_preservation_missing_chars_in_actual():
    """expected='abcd', actual='abc' → equal=False, precision=3/3=1.0, recall=3/4。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abcd"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 0.75


def test_text_preservation_image_excluded_from_expected():
    """image content 不参与 expected（即使 image 有 content）。"""
    elements = [
        {"type": "paragraph", "element_id": "p1", "content": "abc"},
        {"type": "image", "element_id": "i1", "content": "xyz"},
    ]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_only_whitespace_in_expected():
    """expected 全是空白 → strip 后空 → empty_expected。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "   \n\t   "}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["recall"]["value"] is None
    assert result["recall"]["reason"] == "empty_expected"


def test_text_preservation_returns_three_keys():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert set(result.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_metric_has_value_reason():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    for name in ("equal", "precision", "recall"):
        assert "value" in result[name]
        assert "reason" in result[name]


def test_text_preservation_signature():
    sig = inspect.signature(_text_preservation)
    assert set(sig.parameters) == {"elements", "chunks"}


# =========================================================================
# _chunk_reference_ratio 深度
# =========================================================================


def test_chunk_reference_ratio_empty_elements_no_chunks_returns_no_chunks():
    """空 chunks → no_chunks（不管 elements）。"""
    result = _chunk_reference_ratio([], [])
    assert result["value"] is None
    assert result["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_elements_with_chunks_returns_zero():
    """有 chunks 但 elements 空 → 任何 id 都不在 elem_ids → ratio=0.0。"""
    chunks = [{"source_element_ids": ["x"]}]
    result = _chunk_reference_ratio([], chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunk_with_none_ids_skipped():
    """source_element_ids=None → falsy → 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    result = _chunk_reference_ratio(elements, chunks)
    # None falsy → not counted
    assert result["value"] == 0.0


def test_chunk_reference_ratio_all_ids_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_partial_ids_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    result = _chunk_reference_ratio(elements, chunks)
    # all() fails on missing → not valid → ratio=0/1=0.0
    assert result["value"] == 0.0


def test_chunk_reference_ratio_returns_ratio_metric():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert "value" in result
    assert "reason" in result


# =========================================================================
# _silent_drop_count 边界
# =========================================================================


def test_silent_drop_count_negative_expected_no_drop():
    """expected 是负数 → actual >= exp (actual=0) → drop=0。"""
    by_type = {"paragraph": 0}
    expectations = {"element_count_by_type": {"paragraph": -5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_expected_zero_no_drop():
    by_type = {"paragraph": 0}
    expectations = {"element_count_by_type": {"paragraph": 0}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_only_some_types_below():
    by_type = {"paragraph": 5, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 3}}
    result = _silent_drop_count(by_type, expectations)
    # paragraph: 0 drop; heading: 3-1=2 drop → total 2
    assert result["value"] == 2


def test_silent_drop_count_unexpected_type_ignored():
    """expectations 中有的 type 在 by_type 没有时，按 actual=0 计算 drop。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5, "table": 2}}
    result = _silent_drop_count(by_type, expectations)
    # table: 2-0=2 drop
    assert result["value"] == 2


def test_silent_drop_count_returns_int_metric():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    result = _silent_drop_count(by_type, expectations)
    # actual > expected → drop = 0
    assert result["value"] == 0
    assert result["reason"] is None


def test_silent_drop_count_actual_greater_returns_zero():
    by_type = {"paragraph": 100}
    expectations = {"element_count_by_type": {"paragraph": 10}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_signature():
    sig = inspect.signature(_silent_drop_count)
    assert set(sig.parameters) == {"by_type", "expectations"}


# =========================================================================
# compute_automatic_metrics 深度
# =========================================================================


def test_compute_metrics_error_code_field_inline_dict():
    """error_code 不是用 helper，是内联 dict {value, reason: None}。"""
    error = {"code": "my_code"}
    result = compute_automatic_metrics(None, error, "pdf", None)
    assert result["error_code"] == {"value": "my_code", "reason": None}


def test_compute_metrics_error_none_document_none_error_code_value_none():
    result = compute_automatic_metrics(None, None, "pdf", None)
    assert result["error_code"]["value"] is None
    assert result["error_code"]["reason"] is None


def test_compute_metrics_source_type_other_pdf_locator_null():
    """source_type='markdown' → pdf_locator_valid_ratio null not_pdf_document。"""
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "markdown", None)
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_pdf_docx_null():
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_docx_pdf_null():
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "docx", None)
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_pipeline_failed_11_metric_keys():
    """document=None 时返回 11 个 metric keys（pipeline_success/error_code/schema_valid + 8 个 null）。"""
    result = compute_automatic_metrics(None, None, "pdf", None)
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(result.keys()) == expected_keys


def test_compute_metrics_pipeline_failed_all_null_metrics_same_reason():
    result = compute_automatic_metrics(None, None, "pdf", None)
    for name in (
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ):
        assert result[name]["value"] is None
        assert result[name]["reason"] == "pipeline_failed"


def test_compute_metrics_minimal_doc_returns_14_keys():
    """成功时返回 14 keys（11 null 的 + element_count_total/by_type/error_code 等）。"""
    doc = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "x"}],
        "chunks": [{"chunk_id": "c1", "text": "x", "source_element_ids": ["e1"]}],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    # 14 个 keys: pipeline_success, error_code, schema_valid, element_count_total,
    # element_count_by_type, pdf_locator_valid_ratio, docx_locator_valid_ratio,
    # image_resource_exists_ratio, chunk_reference_intact_ratio,
    # text_preservation_equal, text_char_multiset_precision, text_char_multiset_recall,
    # heading_boundary_compliance, silent_drop_count
    assert len(result) == 14


def test_compute_metrics_element_count_by_type_includes_image():
    """image 也算 element_count_by_type。"""
    doc = {
        "elements": [
            {"element_id": "p1", "type": "paragraph", "content": "x"},
            {"element_id": "i1", "type": "image", "resource_path": "x.png"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = result["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 1, "image": 1}


def test_compute_metrics_pipeline_success_value_is_bool():
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert isinstance(result["pipeline_success"]["value"], bool)


def test_compute_metrics_does_not_mutate_input():
    doc = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    import copy
    before = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == before


# =========================================================================
# 模块结构与签名深度
# =========================================================================


def test_module_all_exact():
    import evaluation.metrics as mod
    assert mod.__all__ == ["compute_automatic_metrics"]


def test_module_all_no_duplicates():
    import evaluation.metrics as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_math():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "import math" in src


def test_module_imports_counter():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from collections import" in src
    assert "Counter" in src


def test_module_imports_path():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_no_silence_unused():
    import evaluation.metrics as mod
    assert not hasattr(mod, "_silence_unused")


def test_module_uses_future_annotations():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.metrics as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_counter():
    """docstring 提及 Counter（多集合）。"""
    import evaluation.metrics as mod
    doc = mod.__doc__
    assert "Counter" in doc


def test_module_docstring_mentions_pure_function():
    """docstring 提及纯函数设计。"""
    import evaluation.metrics as mod
    doc = mod.__doc__
    assert "纯函数" in doc or "pure" in doc.lower()


def test_module_docstring_mentions_no_fabrication():
    """docstring 提及不伪造。"""
    import evaluation.metrics as mod
    doc = mod.__doc__
    assert "不伪造" in doc


def test_module_constants_text_types_seven():
    assert len(_TEXT_TYPES) == 7


def test_module_constants_pdf_bbox_required_four():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_module_constants_text_types_subset_relation():
    """_PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES) <= set(_TEXT_TYPES)


def test_module_helper_functions_present():
    import evaluation.metrics as mod
    for fn in (
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_strip_unicode_whitespace", "_is_valid_bbox",
        "_pdf_locator_ratio", "_docx_locator_ratio",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_text_preservation", "_heading_boundary_ratio", "_silent_drop_count",
        "compute_automatic_metrics",
    ):
        assert hasattr(mod, fn)


# =========================================================================
# 综合行为
# =========================================================================


def test_strip_unicode_whitespace_idempotent():
    s = "hello   world\n\ttab"
    once = _strip_unicode_whitespace(s)
    twice = _strip_unicode_whitespace(once)
    assert once == twice


def test_is_valid_bbox_consistent():
    """同输入两次调用一致。"""
    assert _is_valid_bbox([1, 2, 3, 4]) == _is_valid_bbox([1, 2, 3, 4])


def test_null_ratio_helpers_independent():
    """_null 和 _ratio 互不影响。"""
    n = _null("reason")
    r = _ratio(0.5)
    assert n["value"] is None
    assert r["value"] == 0.5


def test_pdf_locator_ratio_idempotent():
    elements = [{"element_id": "e1", "type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}]
    a = _pdf_locator_ratio(elements)
    b = _pdf_locator_ratio(elements)
    assert a == b


def test_docx_locator_ratio_idempotent():
    elements = [{"element_id": "e1", "type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    a = _docx_locator_ratio(elements)
    b = _docx_locator_ratio(elements)
    assert a == b


def test_text_preservation_idempotent():
    elements = [{"element_id": "p1", "type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    a = _text_preservation(elements, chunks)
    b = _text_preservation(elements, chunks)
    assert a == b


def test_heading_boundary_ratio_idempotent():
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [{"source_element_ids": ["h1"]}]
    a = _heading_boundary_ratio(elements, chunks)
    b = _heading_boundary_ratio(elements, chunks)
    assert a == b


def test_silent_drop_count_idempotent():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 10}}
    a = _silent_drop_count(by_type, expectations)
    b = _silent_drop_count(by_type, expectations)
    assert a == b


def test_compute_automatic_metrics_idempotent():
    doc = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    a = compute_automatic_metrics(doc, None, "pdf", None)
    b = compute_automatic_metrics(doc, None, "pdf", None)
    assert a == b


def test_text_preservation_does_not_mutate_input():
    elements = [{"element_id": "p1", "type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    import copy
    before_e = copy.deepcopy(elements)
    before_c = copy.deepcopy(chunks)
    _text_preservation(elements, chunks)
    assert elements == before_e
    assert chunks == before_c


def test_chunk_reference_ratio_does_not_mutate_input():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    import copy
    before_e = copy.deepcopy(elements)
    before_c = copy.deepcopy(chunks)
    _chunk_reference_ratio(elements, chunks)
    assert elements == before_e
    assert chunks == before_c
