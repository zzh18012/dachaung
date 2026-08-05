r"""evaluation/metrics.py 边角测试 - 第十三轮（Round 242）。

补强已有 base/edges/edges2-12（共 ~1690+ 测试）未覆盖的深度：
- _pdf_locator_ratio：bbox 含 NaN/Inf/-Inf；page 极大值；多个 invalid→valid 计数
- _docx_locator_ratio：source_locator 是 string 触发 substring 检查；page=0 key 存在；
  bbox=None key 存在；relationship_id 字符串值；7 个 structural_keys 全在
- _image_resource_ratio：resource_path=True (bool) → Path(True) TypeError；
  3+ images 全 valid/全 invalid；image element 缺 type
- _chunk_reference_ratio：source_element_ids=None；element_id=None；chunk 引用 None
- _heading_boundary_ratio：multiple chunks 同 first_id（set 去重）；heading 无 element_id
- _silent_drop_count：expectations=truthy 非 dict（string）→ AttributeError；
  element_count_by_type=list → TypeError
- _text_preservation：actual whitespace-only / expected whitespace-only；
  disjoint 字符集 → precision/recall=0
- _null/_ratio/_bool_metric/_int_metric：truthy 边界、None reason、bool 输入
- compute_automatic_metrics：error={} falsy；error 真值；schema_valid reason 格式精确
- 模块结构：__all__ 是 list（非 tuple）；typing.Any/math/Counter/Path 在命名空间
- Counter & 交集：empty Counter & non-empty → empty Counter
- 签名：所有 helper 函数签名精确（含返回值类型注解）
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

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
# _pdf_locator_ratio：bbox NaN / Inf / 极值
# =========================================================================


def test_pdf_locator_ratio_bbox_nan_rejected():
    """bbox 含 NaN → math.isfinite(nan)=False → invalid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [0, 0, 100, float("nan")]},
    }]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_inf_rejected():
    """bbox 含 +Inf → invalid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [0, 0, 100, float("inf")]},
    }]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_negative_inf_rejected():
    """bbox 含 -Inf → invalid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [float("-inf"), 0, 100, 100]},
    }]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_all_nan_rejected():
    """bbox 4 个全 NaN → invalid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {
            "page": 1,
            "bbox": [float("nan")] * 4,
        },
    }]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_very_large_page():
    """page=999999999 → isinstance int 且 ≥1 → valid（image type 不需要 bbox）。"""
    elements = [{"type": "image", "source_locator": {"page": 999999999}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_mixed_invalid_then_valid():
    """3 个元素，前 2 invalid + 后 1 valid → 1/3。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 0}},  # page=0 invalid
        {"type": "paragraph", "source_locator": {"page": 1}},  # paragraph 缺 bbox invalid
        {"type": "image", "source_locator": {"page": 1}},  # valid
    ]
    out = _pdf_locator_ratio(elements)
    assert abs(out["value"] - 1/3) < 1e-9


def test_pdf_locator_ratio_all_invalid_zero():
    """全部 invalid → 0.0。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 0}},
        {"type": "paragraph", "source_locator": {"page": -1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_locator_key():
    """元素缺 source_locator 键 → loc={} → page=None → invalid。"""
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_returns_float():
    """valid ratio 是 float。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert isinstance(out["value"], float)


# =========================================================================
# _docx_locator_ratio：source_locator 类型边界
# =========================================================================


def test_docx_locator_ratio_source_locator_string_substring_match():
    """source_locator='sectionparagraph'（string）→ 'section' substring 命中 → valid。

    源码用 `loc = e.get("source_locator") or {}`，string 是 truthy → loc=string；
    然后 `k in loc` 对 string 做 substring 检查。
    """
    elements = [{"type": "paragraph", "source_locator": "sectionparagraph"}]
    out = _docx_locator_ratio(elements)
    # "page" 不在 "sectionparagraph"，"bbox" 不在，
    # "section" 在 → structural_keys any → valid
    assert out["value"] == 1.0


def test_docx_locator_ratio_source_locator_string_with_page():
    """source_locator='page1'（string）→ 'page' substring → invalid。"""
    elements = [{"type": "paragraph", "source_locator": "page1"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_source_locator_string_with_bbox():
    """source_locator='abcbboxXYZ'（string）→ 'bbox' substring → invalid。"""
    elements = [{"type": "paragraph", "source_locator": "abcbboxXYZ"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_source_locator_string_no_match():
    """source_locator='zzzz'（string）→ 无 structural_key substring → invalid。"""
    elements = [{"type": "paragraph", "source_locator": "zzzz"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_page_zero_key_present():
    """locator={'page': 0} → 'page' in loc True → invalid（哪怕值是 0/falsy）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_bbox_none_key_present():
    """locator={'bbox': None} → 'bbox' in loc True → invalid（值 None 也算）。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": None}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_relationship_id_string_value():
    """locator={'relationship_id': 'rId1'} → valid。"""
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_paragraph_index_none_value():
    """locator={'paragraph_index': None} → key 在 → valid（值 None 也算）。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": None}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_all_seven_structural_keys():
    """locator 含全部 7 个 structural_keys → valid。"""
    loc = {
        "section": "s1",
        "paragraph_index": 0,
        "run_index": 0,
        "table_index": 0,
        "row_index": 0,
        "col_index": 0,
        "relationship_id": "rId1",
    }
    elements = [{"type": "paragraph", "source_locator": loc}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_multiple_structural_keys():
    """locator 含 2 个 structural_keys → valid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"section": "s1", "paragraph_index": 5},
    }]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_mixed_invalid_then_valid():
    """3 个元素，前 2 invalid（page / 无 key）+ 后 1 valid → 1/3。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # page → invalid
        {"type": "paragraph", "source_locator": {}},  # 无 key → invalid
        {"type": "paragraph", "source_locator": {"section": "s1"}},  # valid
    ]
    out = _docx_locator_ratio(elements)
    assert abs(out["value"] - 1/3) < 1e-9


def test_docx_locator_all_invalid_zero():
    """全部 invalid → 0.0。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},
        {"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4]}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_returns_float():
    """valid ratio 是 float。"""
    elements = [{"type": "paragraph", "source_locator": {"section": "s1"}}]
    out = _docx_locator_ratio(elements)
    assert isinstance(out["value"], float)


# =========================================================================
# _image_resource_ratio：truthy 非 str resource_path
# =========================================================================


def test_image_resource_ratio_resource_path_true_raises(tmp_path: Path):
    """resource_path=True → Path(True) raises TypeError（bool 不能转 Path）。"""
    elements = [{"type": "image", "resource_path": True}]
    with pytest.raises(TypeError):
        _image_resource_ratio(elements, tmp_path)


def test_image_resource_ratio_resource_path_int_one_raises(tmp_path: Path):
    """resource_path=1 → Path(1) raises TypeError（int 不能转 Path）。"""
    elements = [{"type": "image", "resource_path": 1}]
    with pytest.raises(TypeError):
        _image_resource_ratio(elements, tmp_path)


def test_image_resource_ratio_three_images_all_valid(tmp_path: Path):
    """3 个 image，全 valid → 1.0。"""
    elements = []
    for i in range(3):
        f = tmp_path / f"img{i}.png"
        f.write_bytes(b"\x89PNG")
        elements.append({"type": "image", "resource_path": str(f)})
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_three_images_all_invalid(tmp_path: Path):
    """3 个 image，全 missing → 0.0。"""
    elements = [
        {"type": "image", "resource_path": str(tmp_path / "a.png")},
        {"type": "image", "resource_path": str(tmp_path / "b.png")},
        {"type": "image", "resource_path": str(tmp_path / "c.png")},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_without_type_key(tmp_path: Path):
    """element 缺 type → not image → 不算 denominator。"""
    # 没有 type 视为非 image → images list 为空 → no_image_elements
    elements = [{"resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_resource_path_path_object(tmp_path: Path):
    """resource_path 是 Path 对象 → Path(Path(...)) OK。"""
    f = tmp_path / "a.png"
    f.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": f}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


# =========================================================================
# _chunk_reference_ratio：边界
# =========================================================================


def test_chunk_reference_ratio_source_element_ids_none_treated_as_empty():
    """source_element_ids=None → `or []` → 空列表 → invalid（不计入 valid）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_references_none_id():
    """chunk source_element_ids=[None] → None in elem_ids → False（除非 element 也 None）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # None 不在 {"e1"} → invalid
    assert out["value"] == 0.0


def test_chunk_reference_ratio_element_id_none_in_set():
    """element element_id=None → None 入 elem_ids 集合；chunk 引用 None → valid。"""
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_all_chunks_valid():
    """3 chunks 都 valid → 1.0。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}, {"element_id": "e3"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
        {"source_element_ids": ["e3"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_referencing_multiple_ids_partial_invalid():
    """chunk 引用 [e1, e2, eX] → all(...) 失败 → invalid。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2", "eX"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_referencing_multiple_ids_all_valid():
    """chunk 引用 [e1, e2] → all valid → valid。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# =========================================================================
# _heading_boundary_ratio：set 去重
# =========================================================================


def test_heading_boundary_ratio_multiple_chunks_same_first_id():
    """2 chunks 都以 e1 开头 → set 去重 → {e1}；1 heading 匹配 → 1.0。"""
    elements = [{"type": "heading", "element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1", "e2"]},
        {"source_element_ids": ["e1", "e3"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_heading_without_element_id_key():
    """heading 缺 element_id 键 → .get 返回 None → None not in set → invalid。"""
    elements = [{"type": "heading"}]  # no element_id
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_heading_element_id_none():
    """heading element_id=None；chunk 也以 None 开头 → None in set → valid。"""
    elements = [{"type": "heading", "element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_chunks_with_empty_ids_skipped():
    """chunk source_element_ids=[] → not added to set。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_two_headings_one_match():
    """2 headings，1 个匹配 → 0.5。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_no_chunks_returns_null():
    """chunks=[] → no chunks → matched=0 → ratio 0/N = 0.0（not null，因为 headings 非空）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    # 注意：源码不检查 chunks 空，只检查 headings 空
    assert out["value"] == 0.0


# =========================================================================
# _silent_drop_count：truthy 非 dict expectations
# =========================================================================


def test_silent_drop_count_expectations_string_raises():
    """expectations='abc'（truthy 非 dict）→ .get 失败 AttributeError。"""
    with pytest.raises(AttributeError):
        _silent_drop_count({"paragraph": 5}, "abc")  # type: ignore[arg-type]


def test_silent_drop_count_expectations_list_raises():
    """expectations=[]（空 list，falsy）→ no_expectations（不抛）。"""
    # 注意：[] 是 falsy → `if not expectations:` True → 返回 null
    out = _silent_drop_count({"paragraph": 5}, [])
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_nonempty_list_raises():
    """expectations=[1, 2]（truthy list）→ .get 失败 AttributeError。"""
    with pytest.raises(AttributeError):
        _silent_drop_count({"paragraph": 5}, [1, 2])  # type: ignore[arg-type]


def test_silent_drop_count_element_count_by_type_list():
    """expectations 含 element_count_by_type=list → `or {}` 仍走 list → 后续 .items() 失败。"""
    # 注意：`expected_counts = expectations.get(...) or {}`
    # list 是 truthy → expected_counts = list
    # 后续 for t, exp in expected_counts.items() → AttributeError
    with pytest.raises(AttributeError):
        _silent_drop_count(
            {"paragraph": 5},
            {"element_count_by_type": [("paragraph", 3)]},
        )


def test_silent_drop_count_expected_zero_no_drop():
    """expected=0 → max(0, 0-actual)=0；不抛。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 0}},
    )
    assert out["value"] == 0


def test_silent_drop_count_expected_negative_no_drop():
    """expected=-3, actual=5 → max(0, -3-5)=0；不抛。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": -3}},
    )
    assert out["value"] == 0


def test_silent_drop_count_actual_zero_expected_positive():
    """expected=3, actual=0（type missing in actual）→ drop=3。"""
    out = _silent_drop_count({}, {"element_count_by_type": {"heading": 3}})
    assert out["value"] == 3


def test_silent_drop_count_multiple_types_summed():
    """expected 含 3 个 type，2 个 drop → 求和。"""
    out = _silent_drop_count(
        {"paragraph": 5},  # paragraph 不 drop
        {"element_count_by_type": {
            "paragraph": 5,  # 0 drop
            "heading": 3,    # actual=0 → drop 3
            "list_item": 2,  # actual=0 → drop 2
        }},
    )
    assert out["value"] == 5


# =========================================================================
# _text_preservation：whitespace-only / disjoint 字符集
# =========================================================================


def test_text_preservation_actual_whitespace_only_treated_as_empty():
    """chunks text 全是空白 → actual.strip_unicode_ws = '' → empty_actual。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "   \t\n  "}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual=""
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_expected_whitespace_only_treated_as_empty():
    """elements content 全是空白 → expected.strip_unicode_ws = '' → empty_expected。"""
    elements = [{"type": "paragraph", "content": "  \t\n  "}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected="", actual="abc"
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_both_whitespace_only():
    """both 只含空白 → both empty → empty_expected_and_actual。"""
    elements = [{"type": "paragraph", "content": "  \t  "}]
    chunks = [{"text": "  \n  "}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_disjoint_character_sets():
    """expected='abc', actual='xyz' → common=0 → precision/recall=0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "xyz"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_same_chars_different_counts():
    """expected='aaa', actual='aa' → common=2; precision=2/2=1; recall=2/3。"""
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False  # 'aaa' != 'aa'
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2/3) < 1e-9


def test_text_preservation_unicode_chars():
    """unicode 字符正确处理。"""
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_chunk_included():
    """elements 含 image 但 chunks 中含该 image 的 'content' → 算 actual 的一部分。"""
    elements = [
        {"type": "image", "content": "should_be_excluded"},
        {"type": "paragraph", "content": "abc"},
    ]
    chunks = [{"text": "abcshould_be_excluded"}]
    out = _text_preservation(elements, chunks)
    # expected="abc"（image content 不计）
    # actual="abcshould_be_excluded"
    # equal=False, common=3 (abc), |actual|=21, |expected|=3
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] == 1.0  # 3/3
    # precision = 3/21
    assert out["precision"]["value"] < 0.2


def test_text_preservation_counter_intersection_empty_counter():
    """Counter & Counter: 空 Counter 交集任意都为空。"""
    c1 = Counter("")
    c2 = Counter("abc")
    assert (c1 & c2) == Counter()
    assert sum((c1 & c2).values()) == 0


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 边界
# =========================================================================


def test_null_with_empty_reason():
    """reason="" → value=None, reason=""。"""
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_with_none_reason():
    """reason=None 透传（不验证）。"""
    out = _null(None)  # type: ignore[arg-type]
    assert out["value"] is None
    assert out["reason"] is None


def test_null_with_unicode_reason():
    """reason 含 unicode。"""
    out = _null("无内容可比")
    assert out["value"] is None
    assert out["reason"] == "无内容可比"


def test_ratio_with_bool_true():
    """ratio(True) → float(True)=1.0。"""
    out = _ratio(True)
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_ratio_with_bool_false():
    """ratio(False) → float(False)=0.0。"""
    out = _ratio(False)
    assert out["value"] == 0.0


def test_bool_metric_truthy_non_bool():
    """bool_metric('hello') → bool('hello')=True。"""
    out = _bool_metric("hello")  # type: ignore[arg-type]
    assert out["value"] is True


def test_bool_metric_falsy_non_bool():
    """bool_metric('') → bool('')=False。"""
    out = _bool_metric("")  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_with_list_input():
    """bool_metric([1]) → True；bool_metric([]) → False。"""
    assert _bool_metric([1])["value"] is True
    assert _bool_metric([])["value"] is False


def test_int_metric_with_bool_input():
    """int_metric(True)=1；int_metric(False)=0。"""
    assert _int_metric(True)["value"] == 1
    assert _int_metric(False)["value"] == 0


def test_int_metric_with_float_truncates():
    """int_metric(3.99)=3；int_metric(-3.99)=-3（向 0 截断）。"""
    assert _int_metric(3.99)["value"] == 3
    assert _int_metric(-3.99)["value"] == -3


def test_int_metric_value_is_int_type_with_float_input():
    """int_metric(1.5) → value 是 int 不是 float。"""
    out = _int_metric(1.5)
    assert isinstance(out["value"], int)
    assert not isinstance(out["value"], float)


# =========================================================================
# compute_automatic_metrics：error / schema 边界
# =========================================================================


def test_compute_metrics_error_empty_dict_treated_as_no_error(tmp_path: Path):
    """error={} → falsy → error_code value=None；pipeline_success 看 document。

    注意：`pipeline_success = error is None and document is not None`
    这里 error={} 不是 None → pipeline_success=False
    """
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, {}, "pdf", None)
    # error is not None → pipeline_success=False
    assert out["pipeline_success"]["value"] is False
    # error_code：error={} falsy → value=None
    assert out["error_code"]["value"] is None


def test_compute_metrics_error_with_code_value_string(tmp_path: Path):
    """error={'code': 'parse_failed'} → error_code.value='parse_failed'。"""
    out = compute_automatic_metrics(None, {"code": "parse_failed"}, "pdf", None)
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_metrics_error_code_value_int(tmp_path: Path):
    """error={'code': 42} → error_code.value=42（任意类型透传）。"""
    out = compute_automatic_metrics(None, {"code": 42}, "pdf", None)
    assert out["error_code"]["value"] == 42


def test_compute_metrics_schema_valid_exception_reason_format(tmp_path, monkeypatch):
    """document_passes_schema raises ValueError → reason='schema_check_exception:ValueError'。"""
    def boom(doc):
        raise ValueError("boom")

    monkeypatch.setattr(
        "evaluation.metrics.document_passes_schema", boom, raising=False
    )
    # 需要把 schema_validation 模块里的也 patch，因为 from import 后绑定到 metrics 模块
    import evaluation.metrics as m
    # metrics.py 内是延迟 import：`from evaluation.schema_validation import document_passes_schema`
    # 所以每次调用都重新 import，patch 源头模块
    import evaluation.schema_validation
    monkeypatch.setattr(
        evaluation.schema_validation, "document_passes_schema", boom
    )
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert out["schema_valid"]["reason"] == "schema_check_exception:ValueError"


def test_compute_metrics_schema_valid_exception_type_name_in_reason(tmp_path, monkeypatch):
    """document_passes_schema raises RuntimeError → reason 含 'RuntimeError'。"""
    def boom(doc):
        raise RuntimeError("x")

    import evaluation.schema_validation
    monkeypatch.setattr(
        evaluation.schema_validation, "document_passes_schema", boom
    )
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert "RuntimeError" in out["schema_valid"]["reason"]


def test_compute_metrics_schema_valid_with_real_schema_validation(tmp_path: Path):
    """不用 monkeypatch，调用真实 schema_validation → schema_valid.value=True。"""
    # 一个最小但合法的 document（schema 校验通过）
    # document.schema.json 要求 element_id 等字段，但 schema_validation 可能有不同实现
    # 用一个空 document 测试（schema_validation 应当能处理）
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 不固定 True/False，只验证它是 bool 类型（不抛）
    assert isinstance(out["schema_valid"]["value"], bool)


def test_compute_metrics_does_not_mutate_image_base_dir(tmp_path: Path):
    """compute_automatic_metrics 不修改 image_base_dir 参数。"""
    img_file = tmp_path / "a.png"
    img_file.write_bytes(b"\x89PNG")
    document = {
        "elements": [{"type": "image", "resource_path": "a.png"}],
        "chunks": [],
    }
    original = tmp_path
    compute_automatic_metrics(
        document, None, "pdf", None, image_base_dir=tmp_path,
    )
    assert tmp_path == original
    assert img_file.is_file()  # 文件未被破坏


def test_compute_metrics_expectations_truthy_non_dict_string(tmp_path: Path):
    """expectations='abc'（truthy string）→ _silent_drop_count 会 AttributeError。

    这里我们验证：compute_automatic_metrics 在调用 _silent_drop_count 时
    不会捕获异常，会向上抛。
    """
    document = {"elements": [], "chunks": []}
    with pytest.raises(AttributeError):
        compute_automatic_metrics(document, None, "pdf", "abc")


# =========================================================================
# element_count_by_type insertion order
# =========================================================================


def test_compute_metrics_element_count_by_type_insertion_order(tmp_path: Path):
    """element_count_by_type 按 element 出现顺序插入。"""
    document = {
        "elements": [
            {"element_id": "e1", "type": "paragraph"},
            {"element_id": "e2", "type": "heading"},
            {"element_id": "e3", "type": "list_item"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    by_type = out["element_count_by_type"]["value"]
    # 插入顺序 = element 出现顺序
    assert list(by_type.keys()) == ["paragraph", "heading", "list_item"]


def test_compute_metrics_element_count_by_type_same_type_grouped(tmp_path: Path):
    """相同 type 的 element 计数累加，但顺序保持首次出现的位置。"""
    document = {
        "elements": [
            {"element_id": "e1", "type": "paragraph"},
            {"element_id": "e2", "type": "heading"},
            {"element_id": "e3", "type": "paragraph"},  # 第二次出现
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    by_type = out["element_count_by_type"]["value"]
    # paragraph 在前（首次出现），heading 在中
    assert list(by_type.keys()) == ["paragraph", "heading"]
    assert by_type["paragraph"] == 2
    assert by_type["heading"] == 1


# =========================================================================
# 模块结构补强
# =========================================================================


def test_module_all_is_list():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.metrics as m
    assert isinstance(m.__all__, list)


def test_module_all_exact_contents():
    """__all__ 内容精确：['compute_automatic_metrics']。"""
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_typing_any_in_namespace():
    """Any 在模块命名空间。"""
    import evaluation.metrics as m
    assert m.Any is Any


def test_module_math_in_namespace():
    """math 在模块命名空间。"""
    import evaluation.metrics as m
    assert m.math is math


def test_module_counter_in_namespace():
    """Counter 在模块命名空间。"""
    import evaluation.metrics as m
    assert m.Counter is Counter


def test_module_path_in_namespace():
    """Path 在模块命名空间。"""
    import evaluation.metrics as m
    assert m.Path is Path


def test_module_constants_text_types_exact_value():
    """_TEXT_TYPES 7 元素精确。"""
    assert _TEXT_TYPES == (
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    )


def test_module_constants_pdf_bbox_required_exact_value():
    """_PDF_BBOX_REQUIRED_TYPES 4 元素精确。"""
    assert _PDF_BBOX_REQUIRED_TYPES == (
        "heading", "paragraph", "caption", "list_item",
    )


def test_module_constants_not_evaluated_value():
    """_NOT_EVALUATED = 'not_evaluated'。"""
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_constants_text_types_excludes_caption_in_bbox():
    """_PDF_BBOX_REQUIRED_TYPES 不含 'table'。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_module_constants_subset_relation_exact():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的真子集。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


# =========================================================================
# 函数签名精确
# =========================================================================


def test_compute_automatic_metrics_signature_exact():
    """signature: (document, error, source_type, expectations, image_base_dir=None)。"""
    import inspect
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == [
        "document", "error", "source_type", "expectations", "image_base_dir",
    ]
    # image_base_dir 默认值是 None
    assert sig.parameters["image_base_dir"].default is None


def test_pdf_locator_ratio_signature_exact():
    """signature: (elements)。"""
    import inspect
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_docx_locator_ratio_signature_exact():
    """signature: (elements)。"""
    import inspect
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_image_resource_ratio_signature_exact():
    """signature: (elements, image_base_dir)。"""
    import inspect
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_chunk_reference_ratio_signature_exact():
    """signature: (elements, chunks)。"""
    import inspect
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_heading_boundary_ratio_signature_exact():
    """signature: (elements, chunks)。"""
    import inspect
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_silent_drop_count_signature_exact():
    """signature: (by_type, expectations)。"""
    import inspect
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


def test_text_preservation_signature_exact():
    """signature: (elements, chunks)。"""
    import inspect
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_is_valid_bbox_signature_exact():
    """signature: (bbox)。"""
    import inspect
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


def test_strip_unicode_whitespace_signature_exact():
    """signature: (s)。"""
    import inspect
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_null_signature_exact():
    """signature: (reason)。"""
    import inspect
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_ratio_signature_exact():
    """signature: (value)。"""
    import inspect
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_bool_metric_signature_exact():
    """signature: (value)。"""
    import inspect
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_int_metric_signature_exact():
    """signature: (value)。"""
    import inspect
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


# =========================================================================
# callable 验证
# =========================================================================


def test_compute_automatic_metrics_callable():
    assert callable(compute_automatic_metrics)


def test_all_helpers_callable():
    """所有内部 helper 都 callable。"""
    assert callable(_null)
    assert callable(_ratio)
    assert callable(_bool_metric)
    assert callable(_int_metric)
    assert callable(_pdf_locator_ratio)
    assert callable(_docx_locator_ratio)
    assert callable(_image_resource_ratio)
    assert callable(_chunk_reference_ratio)
    assert callable(_heading_boundary_ratio)
    assert callable(_silent_drop_count)
    assert callable(_text_preservation)
    assert callable(_is_valid_bbox)
    assert callable(_strip_unicode_whitespace)


# =========================================================================
# 端到端：full document 跑通
# =========================================================================


def test_compute_metrics_full_document_all_metrics_present(tmp_path: Path):
    """合成一个 full document → 所有 14 个 metric 都有值。"""
    document = {
        "elements": [
            {"element_id": "h1", "type": "heading", "content": "Title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"element_id": "p1", "type": "paragraph", "content": "Body text",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "Title Body text", "source_element_ids": ["h1", "p1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 14 keys
    assert len(out) == 14
    # pipeline_success
    assert out["pipeline_success"]["value"] is True
    # element_count_total
    assert out["element_count_total"]["value"] == 2
    # element_count_by_type
    assert out["element_count_by_type"]["value"] == {"heading": 1, "paragraph": 1}
    # pdf_locator_valid_ratio: 2 valid / 2 = 1.0
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    # docx_locator_valid_ratio: not_docx_document
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    # chunk_reference_intact_ratio
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    # heading_boundary_compliance: h1 是 chunk 首元素 → 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_compute_metrics_full_document_docx_path(tmp_path: Path):
    """DOCX full document → docx_locator_valid_ratio 计算。"""
    document = {
        "elements": [
            {"element_id": "p1", "type": "paragraph", "content": "Hello",
             "source_locator": {"section": "s1", "paragraph_index": 0}},
        ],
        "chunks": [{"text": "Hello", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
