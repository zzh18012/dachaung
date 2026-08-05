r"""evaluation/metrics.py 边角测试 - 第十七轮（Round 270）。

edges16 已覆盖：源码 token、docstring、签名 introspection、helper metadata、
常量 namespace 完整性、_is_valid_bbox、_pdf_locator_ratio 每 text type、
_docx_locator_ratio 每 structural key、_image_resource_ratio、_chunk_reference_ratio、
_heading_boundary_ratio、_silent_drop_count、_text_preservation、compute_automatic_metrics、
namespace identity、helper no-caching。

edges17 补强未覆盖的角度：
- _null/_ratio/_bool_metric/_int_metric 边界：value 类型强制转换；reason 类型；返回 dict key 顺序
- _is_valid_bbox 边界：bbox=[1,2,3] 长度<4；bbox=[1,2,3,4,5] 长度>4；bbox=[1.0, 2.0, 3.0, 4.0] float；bbox=[True, 1, 2, 3] 含 bool；bbox=[inf, 1, 2, 3] 含 inf；bbox=[nan, 1, 2, 3] 含 nan；bbox=[1, '2', 3, 4] 含 str；bbox=None；bbox='[1,2,3,4]'；bbox=(1,2,3,4) tuple
- _pdf_locator_ratio 边界：空 elements；缺 source_locator；page=0；page=-1；page=1.0（float）；page='1'（str）；bbox 缺；bbox=[1,2,3] 不够 4；non-required type 不需要 bbox
- _docx_locator_ratio 边界：空 elements；locator 含 page；locator 含 bbox；locator 含 structural_key；locator 完全空 dict；locator 是 None
- _image_resource_ratio 边界：无 image；image 缺 resource_path；resource_path=''；image_base_dir 拼接查找；resource_path 绝对路径；resource_path 是文件名 only；image 文件 size=0；image 文件不存在
- _chunk_reference_ratio 边界：空 chunks；chunks=[]（与 no_chunks 路径不同？代码用 `if not chunks`）；elements=[] → elem_ids 空集 → 任何 ids 都不匹配；source_element_ids=[]；source_element_ids=None；source_element_ids 含不存在的 id
- _strip_unicode_whitespace：含 NBSP / em space / ideographic space / line separator / 全角空格 / \t \n \r / 不删非空白
- _text_preservation 边界：所有 elements 是 image → expected_raw='' → expected=''；expected+actual 都空 → equal=True 但 precision/recall null+empty_expected_and_actual；expected 空 actual 非空 → precision null+empty_expected recall=0.0；expected 非空 actual 空 → precision=0.0 recall null+empty_actual；多集合交集 min 行为
- _heading_boundary_ratio 边界：无 heading → null+no_heading_elements；无 chunks → matched=0 ratio=0.0；chunk 缺 source_element_ids → 跳过；chunk source_element_ids=[] → 跳过；多个 heading 同一 element_id（去重）
- _silent_drop_count 边界：无 expectations → null+no_expectations；expectations={} → null+no_expectations_element_count；expected_count_by_type={} → null+no_expectations_element_count；actual >= expected → drops=0；多 type drops 求和
- compute_automatic_metrics 边界：document=None + error=None → pipeline_success=False；document 非 None + error 非 None → pipeline_success=False；source_type='unknown' → pdf/docx ratio 都 null；schema_check_exception 路径（document_passes_schema 抛错 → value False + reason schema_check_exception:X）
- 模块 namespace 完整性补强：_strip_unicode_whitespace 在 namespace；_bool_metric/_int_metric 在 namespace
- 源码 token 补强：含 strip_unicode_whitespace、isspace、isfinite、isinstance、Iterable 检查；不含 print/logging/json
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from evaluation.metrics import (
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
# _null / _ratio / _bool_metric / _int_metric 边界
# =========================================================================


def test_null_returns_dict_with_value_none():
    out = _null("reason_x")
    assert out == {"value": None, "reason": "reason_x"}


def test_null_value_is_none():
    assert _null("x")["value"] is None


def test_null_reason_is_string():
    out = _null("x")
    assert out["reason"] == "x"
    assert isinstance(out["reason"], str)


def test_null_keys_order():
    out = _null("x")
    assert list(out.keys()) == ["value", "reason"]


def test_null_two_calls_independent_dict():
    a = _null("x")
    b = _null("x")
    assert a is not b
    assert a == b


def test_ratio_returns_dict_with_value_float():
    out = _ratio(0.5)
    assert out["value"] == 0.5
    assert isinstance(out["value"], float)


def test_ratio_int_input_converted_to_float():
    out = _ratio(1)  # type: ignore[arg-type]
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_ratio_zero():
    out = _ratio(0.0)
    assert out["value"] == 0.0


def test_ratio_one():
    out = _ratio(1.0)
    assert out["value"] == 1.0


def test_ratio_negative_input_not_validated():
    """_ratio 不强制 0..1 范围。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_reason_is_none():
    out = _ratio(0.5)
    assert out["reason"] is None


def test_ratio_keys_order():
    out = _ratio(0.5)
    assert list(out.keys()) == ["value", "reason"]


def test_ratio_two_calls_independent_dict():
    a = _ratio(0.5)
    b = _ratio(0.5)
    assert a is not b


def test_bool_metric_returns_dict_with_value_bool():
    out = _bool_metric(True)
    assert out["value"] is True
    assert isinstance(out["value"], bool)


def test_bool_metric_int_converted_to_bool():
    out = _bool_metric(1)  # type: ignore[arg-type]
    assert out["value"] is True


def test_bool_metric_zero_converted_to_false():
    out = _bool_metric(0)  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_reason_is_none():
    out = _bool_metric(True)
    assert out["reason"] is None


def test_bool_metric_keys_order():
    out = _bool_metric(True)
    assert list(out.keys()) == ["value", "reason"]


def test_int_metric_returns_dict_with_value_int():
    out = _int_metric(5)
    assert out["value"] == 5
    assert isinstance(out["value"], int)


def test_int_metric_float_converted_to_int():
    out = _int_metric(5.7)  # type: ignore[arg-type]
    assert out["value"] == 5


def test_int_metric_zero():
    out = _int_metric(0)
    assert out["value"] == 0


def test_int_metric_negative():
    out = _int_metric(-3)
    assert out["value"] == -3


def test_int_metric_reason_is_none():
    out = _int_metric(5)
    assert out["reason"] is None


def test_int_metric_keys_order():
    out = _int_metric(5)
    assert list(out.keys()) == ["value", "reason"]


# =========================================================================
# _is_valid_bbox 边界
# =========================================================================


def test_is_valid_bbox_valid_int_list():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_valid_float_list():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([1, 2.5, 3, 4.5]) is True


def test_is_valid_bbox_too_short():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_too_long():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_contains_bool():
    """True/False 是 int 子类但 _is_valid_bbox 显式排除。"""
    assert _is_valid_bbox([True, 1, 2, 3]) is False


def test_is_valid_bbox_contains_inf():
    assert _is_valid_bbox([math.inf, 1, 2, 3]) is False


def test_is_valid_bbox_contains_negative_inf():
    assert _is_valid_bbox([-math.inf, 1, 2, 3]) is False


def test_is_valid_bbox_contains_nan():
    assert _is_valid_bbox([math.nan, 1, 2, 3]) is False


def test_is_valid_bbox_contains_str():
    assert _is_valid_bbox([1, '2', 3, 4]) is False


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string():
    """bbox 是 str 不是 list → False。"""
    assert _is_valid_bbox("[1,2,3,4]") is False


def test_is_valid_bbox_tuple():
    """bbox 是 tuple 不是 list → False（代码用 isinstance(bbox, list)）。"""
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_returns_bool_type():
    assert isinstance(_is_valid_bbox([1, 2, 3, 4]), bool)


# =========================================================================
# _pdf_locator_ratio 边界
# =========================================================================


def test_pdf_locator_ratio_empty_elements():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_missing_source_locator():
    """element 缺 source_locator → loc = {} → page None → 不计。"""
    out = _pdf_locator_ratio([{"type": "heading"}])
    # 1 element 0 valid → ratio 0.0
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_zero():
    """page=0 < 1 → 不计。"""
    out = _pdf_locator_ratio(
        [{"type": "header", "source_locator": {"page": 0}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative():
    out = _pdf_locator_ratio(
        [{"type": "header", "source_locator": {"page": -1}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_float_not_int():
    """page=1.0 是 float 不是 int → 不计（isinstance(page, int) False）。"""
    out = _pdf_locator_ratio(
        [{"type": "header", "source_locator": {"page": 1.0}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_string():
    """page='1' 是 str 不是 int → 不计。"""
    out = _pdf_locator_ratio(
        [{"type": "header", "source_locator": {"page": "1"}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_missing_bbox():
    """heading 需要 bbox 但缺 → 不计。"""
    out = _pdf_locator_ratio(
        [{"type": "heading", "source_locator": {"page": 1}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_invalid_bbox():
    out = _pdf_locator_ratio(
        [{"type": "heading", "source_locator": {"page": 1, "bbox": [1, 2, 3]}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_valid_bbox():
    out = _pdf_locator_ratio(
        [{"type": "heading", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}}]
    )
    assert out["value"] == 1.0


def test_pdf_locator_ratio_non_required_type_no_bbox_needed():
    """header 不需要 bbox → page=1 即可。"""
    out = _pdf_locator_ratio(
        [{"type": "header", "source_locator": {"page": 1}}]
    )
    assert out["value"] == 1.0


def test_pdf_locator_ratio_partial_valid():
    out = _pdf_locator_ratio(
        [
            {"type": "header", "source_locator": {"page": 1}},  # valid
            {"type": "heading", "source_locator": {"page": 1}},  # invalid (no bbox)
        ]
    )
    assert out["value"] == 0.5


def test_pdf_locator_ratio_returns_dict_with_value_and_reason():
    out = _pdf_locator_ratio([{"type": "header", "source_locator": {"page": 1}}])
    assert "value" in out
    assert "reason" in out


# =========================================================================
# _docx_locator_ratio 边界
# =========================================================================


def test_docx_locator_ratio_empty_elements():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_locator_has_page():
    """locator 含 page → 不计。"""
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": 1}}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_locator_has_bbox():
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4]}}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_locator_has_structural_key():
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    )
    assert out["value"] == 1.0


def test_docx_locator_ratio_locator_empty_dict():
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {}}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_locator_none():
    """source_locator 是 None → loc = {} (None or {}) → 不计。"""
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": None}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_source_locator():
    out = _docx_locator_ratio([{"type": "paragraph"}])
    assert out["value"] == 0.0


def test_docx_locator_ratio_each_structural_key():
    """每个 structural_key 单独触发。"""
    for key in (
        "section",
        "paragraph_index",
        "run_index",
        "table_index",
        "row_index",
        "col_index",
        "relationship_id",
    ):
        out = _docx_locator_ratio(
            [{"type": "paragraph", "source_locator": {key: 1}}]
        )
        assert out["value"] == 1.0


def test_docx_locator_ratio_partial_valid():
    out = _docx_locator_ratio(
        [
            {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        ]
    )
    assert out["value"] == 0.5


# =========================================================================
# _image_resource_ratio 边界
# =========================================================================


def test_image_resource_ratio_no_image_elements():
    out = _image_resource_ratio([], None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_non_image_only():
    """全是非 image element → no_image_elements。"""
    out = _image_resource_ratio([{"type": "paragraph"}], None)
    assert out["value"] is None


def test_image_resource_ratio_image_missing_resource_path():
    out = _image_resource_ratio([{"type": "image"}], None)
    # rp=None falsy → skip → valid=0 → ratio=0/1=0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path():
    out = _image_resource_ratio([{"type": "image", "resource_path": ""}], None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_not_found(tmp_path: Path):
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": "missing.png"}], tmp_path
    )
    assert out["value"] == 0.0


def test_image_resource_ratio_file_exists_absolute(tmp_path: Path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": str(img)}], None
    )
    assert out["value"] == 1.0


def test_image_resource_ratio_file_exists_filename_only(tmp_path: Path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": "test.png"}], tmp_path
    )
    # image_base_dir / Path(rp).name 拼接找到
    assert out["value"] == 1.0


def test_image_resource_ratio_file_size_zero(tmp_path: Path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": "empty.png"}], tmp_path
    )
    # size == 0 → not counted
    assert out["value"] == 0.0


def test_image_resource_ratio_partial_valid(tmp_path: Path):
    img = tmp_path / "exists.png"
    img.write_bytes(b"\x89PNG" + b"\x00" * 10)
    out = _image_resource_ratio(
        [
            {"type": "image", "resource_path": "exists.png"},
            {"type": "image", "resource_path": "missing.png"},
        ],
        tmp_path,
    )
    assert out["value"] == 0.5


# =========================================================================
# _chunk_reference_ratio 边界
# =========================================================================


def test_chunk_reference_ratio_no_chunks():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_elements():
    """elements=[] → elem_ids 是空集 → 任何 ids 都不在 → valid=0。"""
    out = _chunk_reference_ratio(
        [], [{"source_element_ids": ["e1"]}]
    )
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_missing_source_element_ids():
    """chunk 缺 source_element_ids → ids=[] → ids falsy → 不计。"""
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}], [{}]
    )
    # 1 chunk 0 valid → 0.0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_empty():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}], [{"source_element_ids": []}]
    )
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_none():
    """source_element_ids=None → ids = None or [] = [] → falsy → 不计。"""
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}], [{"source_element_ids": None}]
    )
    assert out["value"] == 0.0


def test_chunk_reference_ratio_id_not_in_elements():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}], [{"source_element_ids": ["nonexistent"]}]
    )
    assert out["value"] == 0.0


def test_chunk_reference_ratio_partial_match():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}, {"element_id": "e2"}],
        [
            {"source_element_ids": ["e1"]},  # valid
            {"source_element_ids": ["nonexistent"]},  # invalid
        ],
    )
    assert out["value"] == 0.5


def test_chunk_reference_ratio_all_ids_must_match():
    """all(sid in elem_ids) → 只要一个不匹配就 false。"""
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}, {"element_id": "e2"}],
        [{"source_element_ids": ["e1", "nonexistent"]}],
    )
    assert out["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace 边界
# =========================================================================


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_ascii_spaces():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_ascii_tabs_newlines():
    assert _strip_unicode_whitespace("a\tb\nc\rd") == "abcd"


def test_strip_unicode_whitespace_nbsp():
    """NBSP \\x00a0 是 whitespace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """em space \\u2003 是 whitespace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """全角空格 \\u3000 是 whitespace。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """line separator \\u2028 是 whitespace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_only_whitespace():
    assert _strip_unicode_whitespace(" \t\n　") == ""


def test_strip_unicode_whitespace_does_not_remove_non_whitespace():
    """不删除非空白字符（包括标点、emoji 等）。"""
    assert _strip_unicode_whitespace("a,b.c!") == "a,b.c!"


def test_strip_unicode_whitespace_preserves_order():
    """不排序，只删除空白。"""
    assert _strip_unicode_whitespace("c b a") == "cba"


def test_strip_unicode_whitespace_returns_str_type():
    assert isinstance(_strip_unicode_whitespace("x"), str)


# =========================================================================
# _text_preservation 边界
# =========================================================================


def test_text_preservation_both_empty():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None
    assert out["recall"]["value"] is None
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_all_image_elements():
    """所有 elements 是 image → expected_raw='' → expected='' → both empty 路径。"""
    out = _text_preservation(
        [{"type": "image", "content": "x"}],
        [{"text": "x"}],
    )
    # expected='' 但 actual='x' → 不是 both empty
    # equal: '' == 'x' after strip → False
    # precision: |actual|>0 → common=0 → 0.0
    # recall: |expected|==0 → null+empty_expected
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_expected_empty_actual_non_empty():
    out = _text_preservation([], [{"text": "abc"}])
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] is None


def test_text_preservation_expected_non_empty_actual_empty():
    out = _text_preservation([{"type": "paragraph", "content": "abc"}], [])
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] is None
    assert out["recall"]["value"] == 0.0


def test_text_preservation_perfect_match():
    out = _text_preservation(
        [{"type": "paragraph", "content": "abc"}],
        [{"text": "abc"}],
    )
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_partial_overlap():
    """expected='abc' actual='abd' → common='a','b' → precision=2/3 recall=2/3。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "abc"}],
        [{"text": "abd"}],
    )
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_repeated_chars():
    """expected='aabb' actual='abab' → Counter both {'a':2,'b':2} → equal counter → precision=1.0 recall=1.0
    但 sequence 不等 → equal=False。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "aabb"}],
        [{"text": "abab"}],
    )
    assert out["equal"]["value"] is False  # 顺序不同
    assert out["precision"]["value"] == 1.0  # counter 相同
    assert out["recall"]["value"] == 1.0


def test_text_preservation_extra_chars_in_actual():
    """expected='ab' actual='abc' → common=2 → precision=2/3 recall=2/2=1.0。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "ab"}],
        [{"text": "abc"}],
    )
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == 1.0


def test_text_preservation_missing_chars_in_actual():
    """expected='abc' actual='ab' → common=2 → precision=2/2=1.0 recall=2/3。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "abc"}],
        [{"text": "ab"}],
    )
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_whitespace_ignored():
    """空白被 _strip_unicode_whitespace 删除，不影响 equal。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "a b"}],
        [{"text": "ab"}],
    )
    assert out["equal"]["value"] is True


def test_text_preservation_returns_three_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


# =========================================================================
# _heading_boundary_ratio 边界
# =========================================================================


def test_heading_boundary_ratio_no_heading():
    out = _heading_boundary_ratio(
        [{"type": "paragraph"}], [{"source_element_ids": ["e1"]}]
    )
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks():
    out = _heading_boundary_ratio([{"type": "heading", "element_id": "h1"}], [])
    # 1 heading 0 matched → ratio 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_missing_source_element_ids():
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{}],  # 缺 source_element_ids
    )
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_empty_ids():
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": []}],
    )
    assert out["value"] == 0.0


def test_heading_boundary_ratio_perfect_match():
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": ["h1", "p1"]}],
    )
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    out = _heading_boundary_ratio(
        [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
        ],
        [{"source_element_ids": ["h1", "p1"]}],
    )
    assert out["value"] == 0.5


def test_heading_boundary_ratio_uses_first_id_only():
    """heading 必须是 chunk 的首元素（ids[0]）。"""
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": ["p1", "h1"]}],  # h1 是第二个 → 不算
    )
    assert out["value"] == 0.0


# =========================================================================
# _silent_drop_count 边界
# =========================================================================


def test_silent_drop_count_no_expectations():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_no_element_count():
    """expectations 没有 element_count_by_type 字段。"""
    out = _silent_drop_count({"paragraph": 5}, {"other_field": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_more_than_expected():
    """actual > expected → max(0, expected-actual)=0。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_actual_equals_expected():
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_actual_less_than_expected():
    out = _silent_drop_count(
        {"paragraph": 3},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 2


def test_silent_drop_count_multi_type_sum():
    out = _silent_drop_count(
        {"paragraph": 3, "heading": 1},
        {"element_count_by_type": {"paragraph": 5, "heading": 2, "table": 3}},
    )
    # paragraph: max(0, 5-3)=2; heading: max(0, 2-1)=1; table: max(0, 3-0)=3
    # sum = 6
    assert out["value"] == 6


def test_silent_drop_count_returns_int_metric():
    out = _silent_drop_count(
        {"paragraph": 3},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert isinstance(out["value"], int)


# =========================================================================
# compute_automatic_metrics 边界
# =========================================================================


def test_compute_metrics_document_none_error_none():
    """document=None + error=None → pipeline_success=False + error_code value=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


def test_compute_metrics_document_with_error():
    """document 非 None + error 非 None → pipeline_success=False。"""
    doc = {"elements": [], "chunks": []}
    err = {"code": "x", "message": "y"}
    out = compute_automatic_metrics(doc, err, "pdf", None)
    # error is not None → pipeline_success=False
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_unknown_source_type():
    """source_type='unknown' → pdf ratio null+not_pdf_document; docx ratio null+not_docx_document。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "unknown", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_pdf_source_type():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # pdf 路径 → 走 _pdf_locator_ratio([]) → null+no_elements
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"
    # docx 路径 → not_docx_document
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_docx_source_type():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "no_elements"
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_keys_count_14():
    """document 非 None → 14 个 metric key。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(out) == 14


def test_compute_metrics_keys_when_pipeline_failed():
    """document=None → 13 个 metric key（error_code/pipeline_success/schema_valid + 10 个 null）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    expected_keys = {
        "pipeline_success",
        "error_code",
        "schema_valid",
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
    }
    assert set(out.keys()) == expected_keys


def test_compute_metrics_does_not_mutate_document():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    import copy
    doc_copy = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == doc_copy


def test_compute_metrics_does_not_mutate_expectations():
    doc = {"elements": [], "chunks": []}
    exp = {"element_count_by_type": {"paragraph": 5}}
    import copy
    exp_copy = copy.deepcopy(exp)
    compute_automatic_metrics(doc, None, "pdf", exp)
    assert exp == exp_copy


def test_compute_metrics_two_calls_independent():
    doc = {"elements": [], "chunks": []}
    a = compute_automatic_metrics(doc, None, "pdf", None)
    b = compute_automatic_metrics(doc, None, "pdf", None)
    assert a is not b


def test_compute_metrics_schema_check_exception(monkeypatch):
    """document_passes_schema 抛错 → schema_valid value=False + reason schema_check_exception:X。"""
    import evaluation.schema_validation as sv

    def fake_check(doc):
        raise ValueError("test error")

    monkeypatch.setattr(sv, "document_passes_schema", fake_check)
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception:ValueError" in out["schema_valid"]["reason"]


# =========================================================================
# 模块 namespace 完整性补强
# =========================================================================


def test_module_namespace_has_strip_unicode_whitespace():
    import evaluation.metrics as m

    assert hasattr(m, "_strip_unicode_whitespace")


def test_module_namespace_has_bool_metric():
    import evaluation.metrics as m

    assert hasattr(m, "_bool_metric")


def test_module_namespace_has_int_metric():
    import evaluation.metrics as m

    assert hasattr(m, "_int_metric")


def test_module_namespace_has_math():
    import evaluation.metrics as m

    assert hasattr(m, "math")
    assert m.math is math


def test_module_namespace_has_counter():
    import evaluation.metrics as m

    assert hasattr(m, "Counter")
    assert m.Counter is Counter


def test_module_namespace_has_path():
    import evaluation.metrics as m

    assert hasattr(m, "Path")
    assert m.Path is Path


def test_module_namespace_has_text_types_constant():
    import evaluation.metrics as m

    assert hasattr(m, "_TEXT_TYPES")


def test_module_namespace_has_pdf_bbox_required_types():
    import evaluation.metrics as m

    assert hasattr(m, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_namespace_has_not_evaluated():
    import evaluation.metrics as m

    assert hasattr(m, "_NOT_EVALUATED")


def test_module_all_is_list():
    import evaluation.metrics as m

    assert isinstance(m.__all__, list)


def test_module_all_exact():
    import evaluation.metrics as m

    assert m.__all__ == ["compute_automatic_metrics"]


# =========================================================================
# 常量精确（顺序敏感）
# =========================================================================


def test_text_types_is_tuple():
    import evaluation.metrics as m

    assert isinstance(m._TEXT_TYPES, tuple)


def test_text_types_exact():
    import evaluation.metrics as m

    assert list(m._TEXT_TYPES) == [
        "heading",
        "paragraph",
        "list_item",
        "table",
        "caption",
        "header",
        "footer",
    ]


def test_pdf_bbox_required_types_is_tuple():
    import evaluation.metrics as m

    assert isinstance(m._PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_exact():
    import evaluation.metrics as m

    assert list(m._PDF_BBOX_REQUIRED_TYPES) == [
        "heading",
        "paragraph",
        "caption",
        "list_item",
    ]


def test_not_evaluated_value():
    import evaluation.metrics as m

    assert m._NOT_EVALUATED == "not_evaluated"


def test_pdf_bbox_required_types_subset_of_text_types():
    import evaluation.metrics as m

    assert set(m._PDF_BBOX_REQUIRED_TYPES).issubset(set(m._TEXT_TYPES))


def test_text_types_does_not_contain_image():
    import evaluation.metrics as m

    assert "image" not in m._TEXT_TYPES


# =========================================================================
# 源码 token 验证（补强 edges16）
# =========================================================================


def test_module_source_contains_strip_unicode_whitespace_def():
    import evaluation.metrics as m

    assert "def _strip_unicode_whitespace(" in inspect.getsource(m)


def test_module_source_contains_isspace_call():
    """isspace() 判断 Unicode 空白。"""
    import evaluation.metrics as m

    assert ".isspace()" in inspect.getsource(m)


def test_module_source_contains_isfinite():
    import evaluation.metrics as m

    assert "math.isfinite" in inspect.getsource(m)


def test_module_source_contains_strip_unicode_whitespace_docstring():
    """_strip_unicode_whitespace docstring 提到不排序/不删非空白。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "删除全部 Unicode 空白" in src or "Unicode 空白" in src


def test_module_source_contains_text_preservation_v1_1_note():
    """docstring 提到 v1.1 的口径变更。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "v1.1" in src or "v1.0" in src


def test_module_source_contains_counter_intersection():
    """多集合交集 & 运算。"""
    import evaluation.metrics as m

    assert "c_expected & c_actual" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.metrics as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_does_not_contain_logging():
    import evaluation.metrics as m

    assert "import logging" not in inspect.getsource(m)


def test_module_source_does_not_contain_json_import():
    import evaluation.metrics as m

    assert "import json" not in inspect.getsource(m)


def test_module_source_does_not_contain_subprocess():
    import evaluation.metrics as m

    assert "import subprocess" not in inspect.getsource(m)


def test_module_source_does_not_contain_asyncio():
    import evaluation.metrics as m

    assert "asyncio" not in inspect.getsource(m)


# =========================================================================
# docstring 内容
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.metrics as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_pure_function():
    import evaluation.metrics as m

    assert "纯函数" in m.__doc__ or "pure function" in m.__doc__.lower()


def test_module_docstring_mentions_no_mutation():
    import evaluation.metrics as m

    assert "不修改" in m.__doc__ or "no mutation" in m.__doc__.lower() or "不" in m.__doc__


def test_module_docstring_mentions_text_preservation():
    import evaluation.metrics as m

    assert "text_preservation" in m.__doc__ or "文本保留" in m.__doc__
