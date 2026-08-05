r"""evaluation/metrics.py 边角测试 - 第十二轮（Round 235）。

补强已有 base/edges/edges2-11（共 ~1570+ 测试）未覆盖的深度：
- compute_automatic_metrics 输出 dict 插入顺序精确（success/failure 两路）
- _text_preservation 返回 dict 插入顺序：equal, precision, recall
- _chunk_reference_ratio：source_element_ids 是非 list（str/int）触发 TypeError 或 char-iterate
- _heading_boundary_ratio：source_element_ids 是 str 触发 char-iterate
- _pdf_locator_ratio / _docx_locator_ratio：elements=[{}]（无 source_locator 键）
- _image_resource_ratio：image element 缺 resource_path / resource_path=None
- _silent_drop_count：expectations 含 string 类型 expected 触发 TypeError
- _is_valid_bbox：list 内嵌 list / 5 元素 / 3 元素 / complex / 巨大值
- _strip_unicode_whitespace：NBSP / line separator / paragraph separator / ideographic space
- compute_automatic_metrics：document={} 空字典 / source_type 未知
"""

from __future__ import annotations

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
# compute_automatic_metrics 输出 dict 插入顺序
# =========================================================================


def test_compute_metrics_failure_path_dict_insertion_order(tmp_path: Path):
    """failure path 输出 dict 插入顺序：14 个 key 精确。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    keys = list(out.keys())
    expected = [
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
    ]
    assert keys == expected


def test_compute_metrics_success_path_dict_insertion_order(tmp_path: Path):
    """success path 输出 dict 插入顺序：14 个 key 精确。"""
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hi"}],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    keys = list(out.keys())
    expected = [
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
    ]
    assert keys == expected


def test_compute_metrics_pipeline_success_first_key():
    """第 1 个 key 是 pipeline_success。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert list(out.keys())[0] == "pipeline_success"


def test_compute_metrics_silent_drop_count_last_key():
    """最后 1 个 key 是 silent_drop_count。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert list(out.keys())[-1] == "silent_drop_count"


def test_compute_metrics_error_code_before_schema_valid():
    """error_code 在 schema_valid 之前。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    keys = list(out.keys())
    assert keys.index("error_code") < keys.index("schema_valid")


def test_compute_metrics_schema_valid_before_element_count_total():
    """schema_valid 在 element_count_total 之前。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    keys = list(out.keys())
    assert keys.index("schema_valid") < keys.index("element_count_total")


# =========================================================================
# _text_preservation 返回 dict 插入顺序
# =========================================================================


def test_text_preservation_return_dict_insertion_order():
    """_text_preservation 返回 dict 顺序：equal, precision, recall。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    keys = list(out.keys())
    assert keys == ["equal", "precision", "recall"]


def test_text_preservation_equal_first_key():
    """equal 是第 1 个 key。"""
    out = _text_preservation([], [])
    assert list(out.keys())[0] == "equal"


def test_text_preservation_recall_last_key():
    """recall 是最后 1 个 key。"""
    out = _text_preservation([], [])
    assert list(out.keys())[-1] == "recall"


# =========================================================================
# _chunk_reference_ratio：source_element_ids 是非 list
# =========================================================================


def test_chunk_reference_ratio_source_element_ids_string_iterates_chars():
    """source_element_ids='abc' → 迭代字符 'a'/'b'/'c'，每个查集合。"""
    elements = [{"element_id": "a"}, {"element_id": "b"}, {"element_id": "c"}]
    chunks = [{"source_element_ids": "abc"}]
    # 'a', 'b', 'c' 都在集合中 → valid → 1/1 = 1.0
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_source_element_ids_string_partial():
    """source_element_ids='abd'，d 不在集合 → not all → 0。"""
    elements = [{"element_id": "a"}, {"element_id": "b"}, {"element_id": "c"}]
    chunks = [{"source_element_ids": "abd"}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_source_element_ids_int_raises():
    """source_element_ids=42（非零 int）→ 迭代 int 抛 TypeError。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": 42}]
    with pytest.raises(TypeError):
        _chunk_reference_ratio(elements, chunks)


def test_chunk_reference_ratio_source_element_ids_zero_treated_as_empty():
    """source_element_ids=0 → falsy → `or []` → 空列表 → chunk 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": 0}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_source_element_ids_empty_string_treated_as_empty():
    """source_element_ids='' → falsy → 空列表 → chunk 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ""}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_source_element_ids_none_treated_as_empty():
    """source_element_ids=None → falsy → 空列表 → chunk 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_source_element_ids_missing_key():
    """chunk 缺 source_element_ids 键 → .get 返回 None → falsy → 空列表。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_elements_empty_chunks_present():
    """elements=[] + chunks 有 → elem_ids=∅ → 所有 chunk invalid。"""
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


# =========================================================================
# _heading_boundary_ratio：source_element_ids 非 list
# =========================================================================


def test_heading_boundary_ratio_source_element_ids_string_iterates_chars():
    """source_element_ids='hid' → 第 1 个 char 'h' 加入集合。"""
    elements = [{"type": "heading", "element_id": "h"}]
    chunks = [{"source_element_ids": "h"}]
    # 'h' 是字符串的第 1 个 char，加入 chunk_first_ids
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_source_element_ids_int_raises():
    """source_element_ids=42 → ids[0] 抛 TypeError（int 不支持索引）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": 42}]
    with pytest.raises(TypeError):
        _heading_boundary_ratio(elements, chunks)


def test_heading_boundary_ratio_source_element_ids_zero_treated_as_empty():
    """source_element_ids=0 → falsy → 跳过这个 chunk。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": 0}]
    out = _heading_boundary_ratio(elements, chunks)
    # headings 存在但 chunk_first_ids 空 → matched=0 / 1 = 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_source_element_ids_empty_list():
    """source_element_ids=[] → falsy → 跳过。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunks_is_empty_list():
    """chunks=[] + headings present → matched=0 / len(headings)。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


# =========================================================================
# _pdf_locator_ratio / _docx_locator_ratio：elements=[{}] 缺 source_locator
# =========================================================================


def test_pdf_locator_ratio_elements_empty_dict_no_locator():
    """elements=[{}]（无 source_locator 键）→ loc={} → page=None → invalid。"""
    out = _pdf_locator_ratio([{}])
    assert out["value"] == 0.0


def test_pdf_locator_ratio_elements_source_locator_none():
    """elements source_locator=None → `or {}` → page=None → invalid。"""
    out = _pdf_locator_ratio([{"source_locator": None}])
    assert out["value"] == 0.0


def test_pdf_locator_ratio_elements_source_locator_empty_dict():
    """elements source_locator={} → page=None → invalid。"""
    out = _pdf_locator_ratio([{"source_locator": {}}])
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_missing_bbox():
    """paragraph 类型 + 有 page + 无 bbox → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_invalid_bbox():
    """paragraph + page + bbox=[1,2,3]（3 元素）→ invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_image_type_only_needs_page():
    """image 类型只需 page≥1，无 bbox 也 OK。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_table_type_only_needs_page():
    """table 类型不在 _PDF_BBOX_REQUIRED_TYPES → 只需 page≥1。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_header_footer_only_needs_page():
    """header/footer 不在 BBOX_REQUIRED → 只需 page≥1。"""
    elements = [
        {"type": "header", "source_locator": {"page": 1}},
        {"type": "footer", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_elements_empty_dict_no_locator():
    """DOCX：elements=[{}]（无 source_locator 键）→ loc={} → 无结构键 → invalid。"""
    out = _docx_locator_ratio([{}])
    assert out["value"] == 0.0


def test_docx_locator_ratio_source_locator_none():
    """DOCX：source_locator=None → `or {}` → 无结构键 → invalid。"""
    out = _docx_locator_ratio([{"source_locator": None}])
    assert out["value"] == 0.0


def test_docx_locator_ratio_source_locator_with_page_invalid():
    """DOCX：source_locator 含 page → invalid（DOCX 不允许 page）。"""
    elements = [{"source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_source_locator_with_bbox_invalid():
    """DOCX：source_locator 含 bbox → invalid。"""
    elements = [{"source_locator": {"bbox": [1, 2, 3, 4], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_paragraph_index_alone_sufficient():
    """DOCX：只有 paragraph_index → valid。"""
    elements = [{"source_locator": {"paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_index_alone_sufficient():
    """DOCX：只有 section → valid。"""
    elements = [{"source_locator": {"section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_table_row_col():
    """DOCX：table_index + row_index + col_index → valid。"""
    elements = [{"source_locator": {"table_index": 0, "row_index": 1, "col_index": 2}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


# =========================================================================
# _image_resource_ratio：image element 缺 resource_path
# =========================================================================


def test_image_resource_ratio_missing_resource_path_key(tmp_path: Path):
    """image element 缺 resource_path 键 → .get 返回 None → falsy → not counted。"""
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 1 image, valid=0 → 0/1 = 0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_resource_path_none(tmp_path: Path):
    """image element resource_path=None → falsy → not counted。"""
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_resource_path_empty_string(tmp_path: Path):
    """resource_path='' → falsy → not counted。"""
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_resource_path_zero(tmp_path: Path):
    """resource_path=0（int）→ falsy → not counted。"""
    elements = [{"type": "image", "resource_path": 0}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_present_missing(tmp_path: Path):
    """2 images，1 个有 valid resource_path、1 个缺 → 0.5。"""
    img_file = tmp_path / "a.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
        {"type": "image"},  # 缺 resource_path
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


def test_image_resource_ratio_resource_path_absolute_no_basedir(tmp_path: Path):
    """image_base_dir=None + resource_path 绝对路径 → 直接 Path(rp) 校验。"""
    img_file = tmp_path / "a.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_resource_path_absolute_missing_no_basedir(tmp_path: Path):
    """image_base_dir=None + resource_path 不存在 → 0.0。"""
    elements = [{"type": "image", "resource_path": str(tmp_path / "missing.png")}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# =========================================================================
# _silent_drop_count：expectations 类型边界
# =========================================================================


def test_silent_drop_count_expectations_empty_dict():
    """expectations={} → falsy → no_expectations。"""
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_none():
    """expectations=None → falsy → no_expectations。"""
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_no_element_count_key():
    """expectations 不含 element_count_by_type → no_expectations_element_count。"""
    out = _silent_drop_count({"paragraph": 5}, {"required_markers": ["x"]})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expectations_element_count_none():
    """expectations['element_count_by_type']=None → `or {}` → no_expectations_element_count。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": None})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expectations_string_value_raises():
    """expected 是 string → actual(str) < exp(int) 或 actual(int) < exp(str) 抛 TypeError。"""
    with pytest.raises(TypeError):
        _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": "5"}})


def test_silent_drop_count_zero_when_actual_equals_expected():
    """actual=expected → drops=0。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_no_drop_when_actual_exceeds():
    """actual>expected → max(0, neg) = 0 → 不计 drop。"""
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_unknown_type_ignored():
    """expectations 含未知 type（actual=0）→ drop=expected。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"heading": 3}})
    # by_type 不含 heading → actual=0 → drop=3-0=3
    assert out["value"] == 3


def test_silent_drop_count_returns_int_value():
    """silent_drop_count value 是 int（不是 float）。"""
    out = _silent_drop_count({"paragraph": 0}, {"element_count_by_type": {"paragraph": 3}})
    assert isinstance(out["value"], int)


def test_silent_drop_count_reason_none_when_value_present():
    """有 expectations 且计算成功 → reason=None。"""
    out = _silent_drop_count({"paragraph": 0}, {"element_count_by_type": {"paragraph": 3}})
    assert out["reason"] is None


# =========================================================================
# _is_valid_bbox 边界
# =========================================================================


def test_is_valid_bbox_nested_list_element():
    """bbox=[1, 2, 3, [4]] → 第 4 元素是 list → not int/float → False。"""
    assert _is_valid_bbox([1, 2, 3, [4]]) is False


def test_is_valid_bbox_nested_dict_element():
    """bbox=[1, 2, 3, {}] → 第 4 元素是 dict → False。"""
    assert _is_valid_bbox([1, 2, 3, {}]) is False


def test_is_valid_bbox_complex_number():
    """bbox 含 complex → not int/float → False。"""
    assert _is_valid_bbox([1, 2, 3, 1j]) is False


def test_is_valid_bbox_3_elements():
    """bbox=[1, 2, 3] → len != 4 → False。"""
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_5_elements():
    """bbox=[1, 2, 3, 4, 5] → len != 4 → False。"""
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_zero_elements():
    """bbox=[] → len=0 != 4 → False。"""
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_only_int_zero():
    """bbox=[0, 0, 0, 0] → True。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_float_zero():
    """bbox=[0.0, 0.0, 0.0, 0.0] → True（float OK）。"""
    assert _is_valid_bbox([0.0, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_very_large_finite():
    """bbox 含 1e308（仍 finite）→ True。"""
    assert _is_valid_bbox([0, 0, 0, 1e308]) is True


def test_is_valid_bbox_very_small_negative():
    """bbox=[-1e308, 0, 0, 0] → True。"""
    assert _is_valid_bbox([-1e308, 0, 0, 0]) is True


def test_is_valid_bbox_first_element_bool_rejected():
    """bbox=[True, 2, 3, 4] → 第 1 个是 bool → False。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_last_element_bool_rejected():
    """bbox=[1, 2, 3, True] → 最后是 bool → False。"""
    assert _is_valid_bbox([1, 2, 3, True]) is False


def test_is_valid_bbox_mixed_int_and_float_accepted():
    """bbox=[1, 2.5, 3, 4.0] → mixed int/float → True。"""
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_is_valid_bbox_negative_and_positive():
    """bbox=[-1.5, 2.5, -3.0, 4.0] → True。"""
    assert _is_valid_bbox([-1.5, 2.5, -3.0, 4.0]) is True


# =========================================================================
# _strip_unicode_whitespace 特殊字符
# =========================================================================


def test_strip_unicode_whitespace_nbsp():
    """NBSP \\u00A0 是 whitespace → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """EM SPACE \\u2003 是 whitespace → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """EN SPACE \\u2002 是 whitespace → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """IDEOGRAPHIC SPACE \\u3000 是 whitespace → 删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """LINE SEPARATOR \\u2028 是 whitespace → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """PARAGRAPH SEPARATOR \\u2029 是 whitespace → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_digits():
    """数字不删除。"""
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_preserves_punctuation():
    """标点不删除。"""
    assert _strip_unicode_whitespace("a, b. c!") == "a,b.c!"


def test_strip_unicode_whitespace_preserves_emoji():
    """emoji 不删除（isspace=False）。"""
    assert _strip_unicode_whitespace("a 😀 b") == "a😀b"


def test_strip_unicode_whitespace_zero_width_joiner_preserved():
    """ZWJ \\u200D 不是 whitespace → 保留。"""
    # ZWJ 的 isspace() 返回 False
    assert _strip_unicode_whitespace("a‍b") == "a‍b"


def test_strip_unicode_whitespace_only_whitespace_returns_empty_string():
    """全 whitespace → 空字符串。"""
    assert _strip_unicode_whitespace("   \t\n 　") == ""


def test_strip_unicode_whitespace_empty_string_returns_empty():
    """空字符串输入 → 空字符串输出。"""
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace_unchanged():
    """无 whitespace → 原样返回。"""
    assert _strip_unicode_whitespace("abc") == "abc"


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 结构补强
# =========================================================================


def test_null_returns_independent_dict():
    """_null 每次返回新 dict（不缓存）。"""
    a = _null("r1")
    b = _null("r1")
    assert a is not b
    assert a == b


def test_ratio_returns_independent_dict():
    """_ratio 每次返回新 dict。"""
    a = _ratio(0.5)
    b = _ratio(0.5)
    assert a is not b
    assert a == b


def test_bool_metric_returns_independent_dict():
    """_bool_metric 每次返回新 dict。"""
    a = _bool_metric(True)
    b = _bool_metric(True)
    assert a is not b
    assert a == b


def test_int_metric_returns_independent_dict():
    """_int_metric 每次返回新 dict。"""
    a = _int_metric(5)
    b = _int_metric(5)
    assert a is not b
    assert a == b


def test_null_dict_keys_exact():
    """_null 返回 dict 只有 value/reason 两个 key。"""
    out = _null("r")
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_dict_keys_exact():
    """_ratio 返回 dict 只有 value/reason 两个 key。"""
    out = _ratio(0.5)
    assert set(out.keys()) == {"value", "reason"}


def test_int_metric_value_is_int_type():
    """_int_metric 返回 value 是 int 类型。"""
    out = _int_metric(5)
    assert isinstance(out["value"], int)


def test_ratio_value_is_float_type():
    """_ratio 返回 value 是 float 类型（即使输入是 int）。"""
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_bool_metric_value_is_bool_type():
    """_bool_metric 返回 value 是 bool 类型。"""
    out = _bool_metric(1)
    assert isinstance(out["value"], bool)


# =========================================================================
# compute_automatic_metrics：document={} 空字典
# =========================================================================


def test_compute_metrics_empty_dict_document(tmp_path: Path):
    """document={} → pipeline_success=True，schema 校验通过/不通过路径走通。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["error_code"]["value"] is None


def test_compute_metrics_empty_dict_element_count_zero(tmp_path: Path):
    """document={} → element_count_total = 0。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["element_count_total"]["value"] == 0


def test_compute_metrics_empty_dict_element_count_by_type_empty(tmp_path: Path):
    """document={} → element_count_by_type value={}。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {}


def test_compute_metrics_empty_dict_pdf_locator_no_elements(tmp_path: Path):
    """document={} + source_type=pdf → pdf_locator ratio = no_elements。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_empty_dict_image_no_image_elements(tmp_path: Path):
    """document={} → image_resource_exists_ratio = no_image_elements。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_metrics_empty_dict_chunk_reference_no_chunks(tmp_path: Path):
    """document={} → chunk_reference_intact_ratio = no_chunks。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_metrics_empty_dict_text_preservation_both_empty(tmp_path: Path):
    """document={} → text_preservation_equal=True；precision/recall=null(empty_expected_and_actual)。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["reason"] == "empty_expected_and_actual"
    assert out["text_char_multiset_recall"]["reason"] == "empty_expected_and_actual"


def test_compute_metrics_empty_dict_heading_boundary_no_heading(tmp_path: Path):
    """document={} → heading_boundary_compliance = no_heading_elements。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["heading_boundary_compliance"]["reason"] == "no_heading_elements"


def test_compute_metrics_empty_dict_silent_drop_no_expectations(tmp_path: Path):
    """document={} + expectations=None → silent_drop_count = no_expectations。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["silent_drop_count"]["reason"] == "no_expectations"


# =========================================================================
# compute_automatic_metrics：source_type 未知
# =========================================================================


def test_compute_metrics_unknown_source_type_pdf_locator_not_pdf(tmp_path: Path):
    """source_type='unknown' → pdf_locator ratio = not_pdf_document。"""
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hi",
                       "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}}],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "unknown", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_unknown_source_type_docx_locator_not_docx(tmp_path: Path):
    """source_type='unknown' → docx_locator ratio = not_docx_document。"""
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "unknown", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_docx_pdf_locator_not_pdf(tmp_path: Path):
    """source_type='docx' → pdf_locator ratio = not_pdf_document。"""
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_source_type_pdf_docx_locator_not_docx(tmp_path: Path):
    """source_type='pdf' → docx_locator ratio = not_docx_document。"""
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# =========================================================================
# _text_preservation 类型补强
# =========================================================================


def test_text_preservation_image_type_excluded_from_expected():
    """elements 含 image → image 的 content 不计入 expected_sequence。"""
    elements = [
        {"type": "image", "content": "img_data"},
        {"type": "paragraph", "content": "abc"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual="abc" → equal=True
    assert out["equal"]["value"] is True


def test_text_preservation_chunk_text_none_treated_as_empty():
    """chunk text=None → `or ""` → 空字符串。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual="" → equal=False
    assert out["equal"]["value"] is False
    # precision: common=0, |actual|=0 → empty_actual → null
    assert out["precision"]["reason"] == "empty_actual"
    # recall: common=0, |expected|=3 → 0/3 = 0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_chunk_missing_text_key():
    """chunk 缺 text 键 → .get 返回 None → `or ""` → 空字符串。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_element_content_none_treated_as_empty():
    """element content=None → `or ""` → 空字符串。"""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected="", actual="abc" → equal=False
    assert out["equal"]["value"] is False
    # precision: common=0, |actual|=3 → 0/3 = 0.0
    assert out["precision"]["value"] == 0.0
    # recall: common=0, |expected|=0 → empty_expected → null
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_element_missing_content_key():
    """element 缺 content 键 → .get 返回 None → `or ""` → 空字符串。"""
    elements = [{"type": "paragraph"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_counter_intersection_takes_min():
    """Counter 交集取 min：a 出现 3 次（expected）、2 次（actual）→ common 中 a=2。"""
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    # common = 2 (min of 3, 2)
    # precision = 2/2 = 1.0
    # recall = 2/3
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2/3) < 1e-9


def test_text_preservation_actual_superset_precision_less_than_one():
    """actual 是 expected 超集 → precision<1, recall=1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    # common = 3 (a, b, c), |actual|=4, |expected|=3
    # precision = 3/4
    # recall = 3/3 = 1.0
    assert abs(out["precision"]["value"] - 0.75) < 1e-9
    assert out["recall"]["value"] == 1.0


# =========================================================================
# _chunk_reference_ratio / _heading_boundary_ratio：element_id 类型
# =========================================================================


def test_chunk_reference_ratio_element_id_int_in_set():
    """element_id 是 int 也可以加入集合，chunk 引用 int 时能匹配。"""
    elements = [{"element_id": 42}]
    chunks = [{"source_element_ids": [42]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_element_id_tuple_in_set():
    """element_id 是 tuple 也可以（hashable）。"""
    elements = [{"element_id": (1, 2)}]
    chunks = [{"source_element_ids": [(1, 2)]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_element_id_int_in_set():
    """heading element_id 是 int。"""
    elements = [{"type": "heading", "element_id": 99}]
    chunks = [{"source_element_ids": [99]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_multiple_chunks_mixed_validity():
    """3 chunks，1 valid + 2 invalid → 1/3。"""
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["e2"]},  # invalid
        {"source_element_ids": []},  # invalid (empty)
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert abs(out["value"] - 1/3) < 1e-9


# =========================================================================
# 模块结构补强
# =========================================================================


def test_module_all_only_one_element():
    """__all__ 只有 1 个元素：compute_automatic_metrics。"""
    import evaluation.metrics as m
    assert len(m.__all__) == 1


def test_module_internal_helpers_not_exported():
    """内部 helper（_null/_ratio/_bool_metric/_int_metric）不在 __all__。"""
    import evaluation.metrics as m
    assert "_null" not in m.__all__
    assert "_ratio" not in m.__all__
    assert "_bool_metric" not in m.__all__
    assert "_int_metric" not in m.__all__


def test_module_text_types_not_exported():
    """_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 不在 __all__。"""
    import evaluation.metrics as m
    assert "_TEXT_TYPES" not in m.__all__
    assert "_PDF_BBOX_REQUIRED_TYPES" not in m.__all__
    assert "_NOT_EVALUATED" not in m.__all__


def test_module_internal_helpers_accessible():
    """内部 helper 仍可在模块命名空间访问。"""
    import evaluation.metrics as m
    assert callable(m._null)
    assert callable(m._ratio)
    assert callable(m._bool_metric)
    assert callable(m._int_metric)


def test_module_private_funcs_in_namespace():
    """私有函数（_pdf_locator_ratio 等）在模块命名空间。"""
    import evaluation.metrics as m
    assert callable(m._pdf_locator_ratio)
    assert callable(m._docx_locator_ratio)
    assert callable(m._image_resource_ratio)
    assert callable(m._chunk_reference_ratio)
    assert callable(m._heading_boundary_ratio)
    assert callable(m._silent_drop_count)
    assert callable(m._text_preservation)
    assert callable(m._is_valid_bbox)
    assert callable(m._strip_unicode_whitespace)
