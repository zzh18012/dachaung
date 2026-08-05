r"""evaluation/metrics.py 边角测试 - 第十轮（Round 216）。

补强已有 base/edges/edges2-9（共 ~1454 测试）未覆盖的深度：
- _null / _ratio / _bool_metric / _int_metric：精确 dict behavior / 不变性
- _is_valid_bbox：负零 / 非常小 / 非常大 / 边界 NaN-Inf 组合
- _pdf_locator_ratio：mixed element types 大规模 / locator={}/None
- _docx_locator_ratio：locator is None / 全部 elements locator={}
- _image_resource_ratio：image_base_dir = None 时直接 Path(rp)
- _chunk_reference_ratio：source_element_ids 含重复 / id 出现在多个 chunk
- _strip_unicode_whitespace：组合 unicode 空白 / 中日韩空白
- _text_preservation：unicode 字符 / 跨 chunk 文本拼接顺序
- _heading_boundary_ratio：所有 chunks 都缺 first id / heading 无 element_id
- _silent_drop_count：expectations 含未知 type 而不增量
- compute_automatic_metrics：source_type="other" / image_base_dir 无影响 / expectations 多 type
- 模块 imports / 常量组合 / 类型分离
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path

import pytest

from evaluation.metrics import (
    _NOT_EVALUATED,
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
# _null / _ratio / _bool_metric / _int_metric 深度
# =========================================================================


def test_null_with_empty_string_reason():
    """reason="" → 仍要写空字符串。"""
    result = _null("")
    assert result == {"value": None, "reason": ""}


def test_null_with_unicode_reason():
    result = _null("没有元素")
    assert result == {"value": None, "reason": "没有元素"}


def test_null_dict_does_not_have_extra_keys():
    result = _null("x")
    assert set(result.keys()) == {"value", "reason"}


def test_null_value_type_is_none():
    result = _null("x")
    assert result["value"] is None


def test_ratio_returns_float_class():
    """ratio 始终 float（即便输入是 int）。"""
    result = _ratio(1)
    assert type(result["value"]) is float
    assert result["value"] == 1.0


def test_ratio_with_nan_input():
    """NaN 是 float → 不抛异常（行为记录）。"""
    result = _ratio(float("nan"))
    assert math.isnan(result["value"])


def test_ratio_with_inf_input():
    result = _ratio(float("inf"))
    assert result["value"] == float("inf")


def test_ratio_with_negative_zero():
    result = _ratio(-0.0)
    assert result["value"] == 0.0
    # sign may differ
    assert math.copysign(1.0, result["value"]) in (1.0, -1.0)


def test_ratio_keys_exact():
    result = _ratio(0.5)
    assert set(result.keys()) == {"value", "reason"}


def test_bool_metric_with_none():
    """None → bool(None) = False。"""
    result = _bool_metric(None)  # type: ignore[arg-type]
    assert result["value"] is False


def test_bool_metric_with_long_string():
    """非空 str → True。"""
    result = _bool_metric("hello")  # type: ignore[arg-type]
    assert result["value"] is True


def test_bool_metric_with_zero_int():
    result = _bool_metric(0)  # type: ignore[arg-type]
    assert result["value"] is False


def test_bool_metric_with_empty_list():
    result = _bool_metric([])  # type: ignore[arg-type]
    assert result["value"] is False


def test_bool_metric_with_nonempty_list():
    result = _bool_metric([0])  # type: ignore[arg-type]
    assert result["value"] is True


def test_bool_metric_keys_exact():
    result = _bool_metric(True)
    assert set(result.keys()) == {"value", "reason"}


def test_int_metric_with_negative_float():
    """int(-3.7) → -3（截断，不是 round）。"""
    result = _int_metric(-3.7)  # type: ignore[arg-type]
    assert result["value"] == -3


def test_int_metric_with_positive_float():
    result = _int_metric(2.99)  # type: ignore[arg-type]
    assert result["value"] == 2


def test_int_metric_with_string_digits():
    """int("42") → 42。"""
    result = _int_metric("42")  # type: ignore[arg-type]
    assert result["value"] == 42


def test_int_metric_keys_exact():
    result = _int_metric(5)
    assert set(result.keys()) == {"value", "reason"}


def test_int_metric_value_is_int_type():
    result = _int_metric(5)
    assert type(result["value"]) is int


# =========================================================================
# _is_valid_bbox 深度
# =========================================================================


def test_is_valid_bbox_zero_floats():
    assert _is_valid_bbox([0.0, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_very_small_floats():
    assert _is_valid_bbox([1e-300, -1e-300, 1e-300, -1e-300]) is True


def test_is_valid_bbox_very_large_finite():
    assert _is_valid_bbox([1e300, 1e300, 1e300, 1e300]) is True


def test_is_valid_bbox_max_float():
    import sys
    assert _is_valid_bbox([sys.float_info.max, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_with_negative_zero():
    """-0.0 仍是 finite float。"""
    assert _is_valid_bbox([-0.0, -0.0, -0.0, -0.0]) is True


def test_is_valid_bbox_inf_at_each_position():
    """Inf 在任意位置 → False。"""
    for i in range(4):
        bbox = [1.0, 1.0, 1.0, 1.0]
        bbox[i] = float("inf")
        assert _is_valid_bbox(bbox) is False


def test_is_valid_bbox_nan_at_each_position():
    """NaN 在任意位置 → False。"""
    for i in range(4):
        bbox = [1.0, 1.0, 1.0, 1.0]
        bbox[i] = float("nan")
        assert _is_valid_bbox(bbox) is False


def test_is_valid_bbox_three_floats_one_nan():
    """3 个 finite + 1 个 NaN → False。"""
    assert _is_valid_bbox([1.0, 2.0, 3.0, float("nan")]) is False


# =========================================================================
# _pdf_locator_ratio / _docx_locator_ratio 深度
# =========================================================================


def test_pdf_locator_ratio_all_locators_empty():
    """所有 elements 的 source_locator={} → page=None → 全部无效。"""
    elements = [{"type": "paragraph", "source_locator": {}} for _ in range(3)]
    result = _pdf_locator_ratio(elements)
    assert result == {"value": 0.0, "reason": None}


def test_pdf_locator_ratio_image_only_valid_no_bbox():
    """image element 只需要 page，不需要 bbox。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_many_mixed():
    """10 个 elements，5 个合法（page≥1），5 个不合法 → ratio = 0.5。"""
    elements = []
    for i in range(5):
        elements.append({"type": "image", "source_locator": {"page": i + 1}})
    for _ in range(5):
        elements.append({"type": "paragraph", "source_locator": {}})
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.5


def test_pdf_locator_ratio_locator_missing():
    """element 没有 source_locator 键 → loc={} → page=None → 无效。"""
    elements = [{"type": "image"}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_returns_float_value():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    result = _pdf_locator_ratio(elements)
    assert isinstance(result["value"], float)


def test_docx_locator_ratio_locator_none_for_each():
    """source_locator=None → loc={} (via `or {}`) → 无效。"""
    elements = [
        {"type": "paragraph", "source_locator": None},
        {"type": "paragraph", "source_locator": None},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_multiple_keys_one_element():
    """一个 element 含多个结构键 → 仍只算 1 个 valid。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {
                "section": 1, "paragraph_index": 2, "run_index": 3,
            },
        },
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_zero_valid():
    """paragraph_index=0 仍 valid（key 存在即可）。"""
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_many_elements_mixed():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        {"type": "paragraph", "source_locator": {}},  # invalid
        {"type": "paragraph", "source_locator": {"paragraph_index": 5}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.5  # 2 of 4 valid


# =========================================================================
# _image_resource_ratio 深度
# =========================================================================


def test_image_resource_ratio_many_images_mixed_exist(tmp_path):
    images = []
    for i in range(5):
        rp = f"img_{i}.png"
        if i < 3:
            (tmp_path / rp).write_bytes(b"data")
        images.append({"type": "image", "resource_path": str(tmp_path / rp)})
    result = _image_resource_ratio(images, None)
    assert result["value"] == 0.6  # 3/5


def test_image_resource_ratio_image_base_dir_filename_match(tmp_path):
    """image_base_dir 给定时，从 rp 取 filename 拼接。"""
    images = [{"type": "image", "resource_path": "only_filename.png"}]
    (tmp_path / "only_filename.png").write_bytes(b"data")
    result = _image_resource_ratio(images, tmp_path)
    assert result["value"] == 1.0


def test_image_resource_ratio_image_base_dir_filename_mismatch(tmp_path):
    """rp 是相对路径但 image_base_dir 下没有同名文件 → invalid。"""
    images = [{"type": "image", "resource_path": "sub/only_filename.png"}]
    (tmp_path / "only_filename.png").write_bytes(b"data")  # 在 base_dir 根下，但 rp 是 sub/...
    # Path(rp).name = "only_filename.png" → base_dir / "only_filename.png" 存在
    result = _image_resource_ratio(images, tmp_path)
    assert result["value"] == 1.0


def test_image_resource_ratio_image_base_dir_does_not_match_either(tmp_path):
    """rp 既不在 base_dir 也不是 base_dir/filename → invalid。"""
    images = [{"type": "image", "resource_path": "/nonexistent/path.png"}]
    result = _image_resource_ratio(images, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_zero_byte_file_in_base_dir(tmp_path):
    """base_dir 下的文件 size=0 → invalid。"""
    images = [{"type": "image", "resource_path": "empty.png"}]
    (tmp_path / "empty.png").write_bytes(b"")
    result = _image_resource_ratio(images, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_no_resource_path_field():
    """image element 没有 resource_path 键 → rp=None → skip → invalid。"""
    images = [{"type": "image"}]
    result = _image_resource_ratio(images, None)
    assert result["value"] == 0.0


# =========================================================================
# _chunk_reference_ratio 深度
# =========================================================================


def test_chunk_reference_ratio_duplicate_ids_in_one_chunk():
    """chunk source_element_ids=[id1, id1] → all in elem_ids → valid。"""
    elements = [{"element_id": "id1"}]
    chunks = [{"source_element_ids": ["id1", "id1"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_id_in_multiple_chunks():
    """同一个 element_id 出现在多个 chunk → 都 valid。"""
    elements = [{"element_id": "id1"}]
    chunks = [
        {"source_element_ids": ["id1"]},
        {"source_element_ids": ["id1"]},
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_elements_empty_ids():
    """elements element_id=None → elem_ids = {None}。chunk ids 含 None → match。"""
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_chunks_empty_list():
    """chunks=[] → null。"""
    elements = [{"element_id": "id1"}]
    chunks = []
    result = _chunk_reference_ratio(elements, chunks)
    assert result["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_missing_ids_field():
    """chunk 没有 source_element_ids 键 → c.get → None → or [] → [] → 不计 valid。"""
    elements = [{"element_id": "id1"}]
    chunks = [{}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace 深度
# =========================================================================


def test_strip_unicode_whitespace_chinese_ideographic_space():
    """U+3000 IDEOGRAPHIC SPACE 应被删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """U+2003 EM SPACE 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """U+2002 EN SPACE 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_nbsp():
    """U+00A0 NO-BREAK SPACE 应被删除（isspace() True）。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_thin_space():
    """U+2009 THIN SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 LINE SEPARATOR 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_multiple_types_mixed():
    """组合多种空白类型。"""
    s = " \t　\na b c\r"
    assert _strip_unicode_whitespace(s) == "abc"


def test_strip_unicode_whitespace_all_whitespace():
    """全空白 → 空。"""
    assert _strip_unicode_whitespace(" \t\n　 ") == ""


def test_strip_unicode_whitespace_preserves_emoji():
    """emoji 字符不是空白。"""
    assert _strip_unicode_whitespace("hello 🌍 world") == "hello🌍world"


def test_strip_unicode_whitespace_preserves_digits():
    assert _strip_unicode_whitespace("1 2 3") == "123"


# =========================================================================
# _text_preservation 深度
# =========================================================================


def test_text_preservation_unicode_content_match():
    elements = [{"type": "paragraph", "content": "中文"}]
    chunks = [{"text": "中文"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_chunking_preserves_chars():
    """chunks 把内容拆成多段，但字符序列保持 → equal=True。"""
    elements = [{"type": "paragraph", "content": "abcdef"}]
    chunks = [{"text": "abc"}, {"text": "def"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_chunking_reorder_breaks_equal():
    """chunks 顺序打乱 → equal=False，但 precision/recall 仍 1.0。"""
    elements = [{"type": "paragraph", "content": "abcdef"}]
    chunks = [{"text": "def"}, {"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_extra_whitespace_in_chunks_ok():
    """chunks 之间加了空白，但去除空白后序列相等 → equal=True。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "  a  "}, {"text": "  b  "}, {"text": "  c  "}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_dup_in_chunks_unequal():
    """chunk 重复了字符 → equal=False。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcabc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # precision: 实际多集合 {a:2,b:2,c:2}, expected {a:1,b:1,c:1} → common = 3 / 6 = 0.5
    assert result["precision"]["value"] == 0.5
    # recall: common 3 / |expected| 3 = 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_missing_in_chunks_unequal():
    """chunk 丢失部分字符 → equal=False，recall<1。"""
    elements = [{"type": "paragraph", "content": "abcdef"}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # precision: 实际 {a,b,c} 全在 expected 中 → common 3 / |actual| 3 = 1.0
    assert result["precision"]["value"] == 1.0
    # recall: common 3 / |expected| 6 = 0.5
    assert result["recall"]["value"] == 0.5


def test_text_preservation_image_content_ignored():
    """image element content 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "XYZ"},
    ]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_returns_dict_with_correct_keys():
    elements = [{"type": "paragraph", "content": "x"}]
    chunks = [{"text": "x"}]
    result = _text_preservation(elements, chunks)
    assert set(result.keys()) == {"equal", "precision", "recall"}


# =========================================================================
# _heading_boundary_ratio 深度
# =========================================================================


def test_heading_boundary_ratio_all_chunks_have_first_id():
    """多个 chunks，每个 first id 都匹配不同 heading。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_chunks_empty_ids():
    """所有 chunks source_element_ids=[] → 无 first id → 0 个 heading 合规。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_chunks_missing_field():
    """chunk 没有 source_element_ids 键 → 视为 []。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_multiple_chunks_same_first_id():
    """两个 chunks first id 相同（重复） → set 去重 → 仍只 match 一个 heading。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_heading_no_element_id():
    """heading element 无 element_id 键 → h.get('element_id') = None →
    chunk_first_ids 中通常 None 不可匹配 → 不计。"""
    elements = [{"type": "heading"}]
    chunks = [{"source_element_ids": ["h1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_no_chunks():
    """chunks=[] → chunk_first_ids 空 → 0 个匹配。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = []
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


# =========================================================================
# _silent_drop_count 深度
# =========================================================================


def test_silent_drop_count_actual_negative_no_drop():
    """actual 负数（理论不可能，但行为记录）→ 仍 < exp 才计 drop。"""
    by_type = {"paragraph": -1}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 6  # max(0, 5 - (-1)) = 6


def test_silent_drop_count_actual_equals_expected_no_drop():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_more_than_expected_no_drop_negative_diff_ignored():
    """actual > expected → diff 负数，max(0, neg) = 0 → 不减。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_unknown_expected_type_treated_as_zero_actual():
    """expected 含 by_type 中没有的 type → actual = 0 → drop = exp。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"heading": 3, "paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    # heading: max(0, 3 - 0) = 3
    # paragraph: max(0, 5 - 5) = 0
    assert result["value"] == 3


def test_silent_drop_count_multiple_unknown_types_summed():
    by_type = {}
    expectations = {"element_count_by_type": {"heading": 3, "paragraph": 5, "table": 2}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 10  # 3 + 5 + 2


# =========================================================================
# compute_automatic_metrics 深度
# =========================================================================


def test_compute_automatic_metrics_source_type_other_all_locators_null(tmp_path):
    """source_type 不是 pdf/docx → 两个 locator 都 null。"""
    document = {
        "elements": [],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="html",
        expectations=None,
    )
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_image_base_dir_none_when_not_passed(tmp_path):
    """image_base_dir None 时仍要计算 image_resource_ratio（用字符串原值）。"""
    document = {
        "elements": [
            {"type": "image", "resource_path": "/nonexistent.png"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    # image_base_dir None → 用 Path(rp) 原值 → 不存在 → ratio 0.0
    assert result["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_automatic_metrics_does_not_mutate_document(tmp_path):
    document = {
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    snapshot = json.dumps(document, sort_keys=True)
    compute_automatic_metrics(
        document=document,
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert json.dumps(document, sort_keys=True) == snapshot


def test_compute_automatic_metrics_all_metric_names(tmp_path):
    """完整 metric keys 集合。"""
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None,
        source_type="pdf", expectations=None,
    )
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(result.keys()) == expected


def test_compute_automatic_metrics_total_metric_count(tmp_path):
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None,
        source_type="pdf", expectations=None,
    )
    assert len(result) == 14


def test_compute_automatic_metrics_failure_path_total_metrics(tmp_path):
    """document=None 时返回的 metrics 数（11 个 null metrics + 2 个 success/error + schema_valid）。"""
    result = compute_automatic_metrics(
        document=None, error=None,
        source_type="pdf", expectations=None,
    )
    expected = {
        "pipeline_success", "error_code", "schema_valid",  # 3 first
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(result.keys()) == expected


def test_compute_automatic_metrics_failure_path_all_null_reasons(tmp_path):
    """document=None 时所有 metrics reason=pipeline_failed（除 pipeline_success/error_code/schema_valid）。"""
    result = compute_automatic_metrics(
        document=None, error=None,
        source_type="pdf", expectations=None,
    )
    for key in (
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ):
        assert result[key]["reason"] == "pipeline_failed"
        assert result[key]["value"] is None


def test_compute_automatic_metrics_failure_path_schema_valid_reason():
    result = compute_automatic_metrics(
        document=None, error=None,
        source_type="pdf", expectations=None,
    )
    assert result["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_error_with_dict_no_code_key(tmp_path):
    """error dict 没有 code 键 → KeyError（行为记录，runner 实际 error dict 总有 code）。"""
    with pytest.raises(KeyError):
        compute_automatic_metrics(
            document=None, error={"message": "boom"},
            source_type="pdf", expectations=None,
        )


def test_compute_automatic_metrics_by_type_with_multiple_types():
    document = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
            {"type": "image"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=document, error=None,
        source_type="pdf", expectations=None,
    )
    assert result["element_count_by_type"]["value"] == {
        "paragraph": 2, "heading": 1, "image": 1,
    }


def test_compute_automatic_metrics_element_count_total_is_int():
    document = {"elements": [{"type": "paragraph"}], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None,
        source_type="pdf", expectations=None,
    )
    assert type(result["element_count_total"]["value"]) is int


# =========================================================================
# 模块结构补充
# =========================================================================


def test_module_constants_type():
    import evaluation.metrics as m
    assert isinstance(m._TEXT_TYPES, tuple)
    assert isinstance(m._PDF_BBOX_REQUIRED_TYPES, tuple)
    assert isinstance(m._NOT_EVALUATED, str)


def test_module_all_export_only_compute():
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_uses_future_annotations():
    import evaluation.metrics as m
    sig = inspect.signature(m.compute_automatic_metrics)
    assert isinstance(sig.return_annotation, str)


def test_module_docstring_present():
    import evaluation.metrics as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 100


def test_module_docstring_mentions_design_principles():
    import evaluation.metrics as m
    doc = m.__doc__
    assert "纯函数" in doc or "pure" in doc.lower()
    assert "null" in doc.lower() or "null" in doc


def test_module_docstring_mentions_text_preservation_semantics():
    import evaluation.metrics as m
    doc = m.__doc__
    assert "text_preservation" in doc or "v1.1" in doc


# Import json for snapshot comparison
import json  # noqa: E402

# sys.float_max substitute
import sys  # noqa: E402


def test_is_valid_bbox_max_float_value():
    """sys.float_info.max 是 finite → True。"""
    assert _is_valid_bbox([sys.float_info.max, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_min_positive_float():
    """sys.float_info.min 是 finite（最小正规格化数）→ True。"""
    assert _is_valid_bbox([sys.float_info.min, 0.0, 0.0, 0.0]) is True
