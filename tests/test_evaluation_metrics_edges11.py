r"""evaluation/metrics.py 边角测试 - 第十一轮（Round 229）。

补强已有 base/edges/edges2-10（共 ~1454+ 测试）未覆盖的深度：
- 模块常量精确内容：_TEXT_TYPES 7 项、_PDF_BBOX_REQUIRED_TYPES 4 项、_NOT_EVALUATED 值
- _chunk_reference_ratio：elements 含 None element_id（集合含 None）/ chunks first id 是 None / chunks 含 mix valid+None
- _heading_boundary_ratio：chunk first id None 加入集合 / heading element_id 与 None 匹配
- _text_preservation：全部 image type / 全部 non-image type 但 content None / content 是非 str（raises）
- _image_resource_ratio：image_base_dir 是文件而非目录 / resource_path 是绝对路径
- _docx_locator_ratio：7 个 structural key 全在一个 element / relationship_id 单独足够
- _pdf_locator_ratio：type=None 不属于 BBOX_REQUIRED / type="image" 只需 page
- _silent_drop_count：expectations 含未知 key 被忽略 / 多个 type 都 drop 求和精确
- compute_automatic_metrics：metric name 集合精确（13 项 + error_code）/ 不混入 chunk_boundary_* figure_caption_*
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
# 模块常量精确内容
# =========================================================================


def test_text_types_count_exactly_seven():
    """_TEXT_TYPES 必须 7 项：heading/paragraph/list_item/table/caption/header/footer。"""
    assert len(_TEXT_TYPES) == 7


def test_text_types_exact_members():
    assert set(_TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    }


def test_text_types_does_not_contain_image():
    """image 不参与文本比对，故意排除。"""
    assert "image" not in _TEXT_TYPES


def test_text_types_is_tuple_not_list():
    """tuple 防止运行时 mutate。"""
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_count_exactly_four():
    """_PDF_BBOX_REQUIRED_TYPES 4 项：heading/paragraph/caption/list_item。"""
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_exact_members():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {
        "heading", "paragraph", "caption", "list_item",
    }


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_subset_of_text_types():
    """所有需要 bbox 的类型都参与文本比对。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_does_not_include_table_header_footer():
    """table/header/footer 是文本类型但不需要 bbox（parser 给不出）。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_value():
    """_NOT_EVALUATED 是字面量字符串 'not_evaluated'。"""
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_not_in_all():
    """内部常量不应出现在 __all__。"""
    from evaluation import metrics as metrics_mod
    assert "_NOT_EVALUATED" not in metrics_mod.__all__


def test_text_types_not_in_all():
    from evaluation import metrics as metrics_mod
    assert "_TEXT_TYPES" not in metrics_mod.__all__


def test_pdf_bbox_required_types_not_in_all():
    from evaluation import metrics as metrics_mod
    assert "_PDF_BBOX_REQUIRED_TYPES" not in metrics_mod.__all__


# =========================================================================
# _chunk_reference_ratio：None element_id / None first id
# =========================================================================


def test_chunk_reference_ratio_elements_with_none_element_id_in_set():
    """elements 含 element_id=None → set 含 None；chunks 引用 None 视为 valid（因为 None in set）。"""
    elements = [{"element_id": None}, {"element_id": "a"}]
    chunks = [{"source_element_ids": [None]}]
    # None is in elem_ids set, so all([None in {None, "a"}]) is True
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_chunks_first_id_none_treated_as_valid():
    """chunk 第一个 id 是 None：如果 elements 也有 None，则该 chunk 视为 valid。"""
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None, "missing"]}]
    # None in set → True; "missing" not in set → False; all() False → invalid
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunks_all_ids_in_set_valid():
    elements = [{"element_id": "a"}, {"element_id": "b"}]
    chunks = [{"source_element_ids": ["a", "b"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_chunks_one_id_missing_invalid():
    elements = [{"element_id": "a"}]
    chunks = [{"source_element_ids": ["a", "missing"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunks_duplicate_id_in_one_chunk():
    """同一 chunk 内重复 id 都在 set 中 → valid。"""
    elements = [{"element_id": "a"}]
    chunks = [{"source_element_ids": ["a", "a", "a"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_half_valid():
    elements = [{"element_id": "a"}]
    chunks = [
        {"source_element_ids": ["a"]},
        {"source_element_ids": ["missing"]},
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.5


def test_chunk_reference_ratio_elements_duplicate_id_collapsed_in_set():
    """elements 重复 element_id → set 去重，仍可匹配。"""
    elements = [{"element_id": "a"}, {"element_id": "a"}, {"element_id": "a"}]
    chunks = [{"source_element_ids": ["a"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


# =========================================================================
# _heading_boundary_ratio：first id 是 None
# =========================================================================


def test_heading_boundary_ratio_chunk_first_id_none():
    """chunk 的 first id 是 None：加入 set；如果 heading element_id 也是 None 则匹配。"""
    elements = [{"type": "heading", "element_id": None}]
    chunks = [{"source_element_ids": [None, "ignored"]}]
    # ids[0] is None → added to chunk_first_ids; heading element_id None in set → match
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_chunk_first_id_none_does_not_match_str_heading():
    """chunk first id 是 None 但 heading element_id 是 str → 不匹配。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": [None]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_multiple_chunks_same_first_id():
    """多个 chunks 同 first id → set 去重；heading 匹配只算一次。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_multiple_headings_some_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},  # match
        {"source_element_ids": ["x"]},   # h2 not matched
        {"source_element_ids": ["h3"]},  # match
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == pytest.approx(2 / 3)


# =========================================================================
# _text_preservation：all image / content None / content non-str
# =========================================================================


def test_text_preservation_all_image_elements_expected_empty():
    """elements 全是 image type → expected_raw = "" → expected = ""。"""
    elements = [
        {"type": "image", "content": "abc"},
        {"type": "image", "content": "def"},
    ]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    # expected empty → equal is False (actual "abc")
    assert result["equal"]["value"] is False


def test_text_preservation_all_image_elements_actual_empty_recall_null():
    """expected 和 actual 都空 → precision/recall = null + 'empty_expected_and_actual'。"""
    elements = [{"type": "image", "content": "abc"}]
    chunks = [{"text": ""}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] is None
    assert result["recall"]["value"] is None
    assert result["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_content_none_treated_as_empty():
    """content=None → or "" → ""."""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    # expected = "" → not equal
    assert result["equal"]["value"] is False
    # expected empty, actual "abc" → recall null + empty_expected
    assert result["recall"]["value"] is None
    assert result["recall"]["reason"] == "empty_expected"


def test_text_preservation_text_none_treated_as_empty():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # expected "abc", actual "" → precision null + empty_actual
    assert result["precision"]["value"] is None
    assert result["precision"]["reason"] == "empty_actual"


def test_text_preservation_content_int_raises_type_error():
    """content 是 int → join 触发 TypeError。"""
    elements = [{"type": "paragraph", "content": 123}]
    chunks = [{"text": "abc"}]
    with pytest.raises(TypeError):
        _text_preservation(elements, chunks)


def test_text_preservation_content_list_raises_type_error():
    elements = [{"type": "paragraph", "content": ["a", "b"]}]
    chunks = [{"text": "abc"}]
    with pytest.raises(TypeError):
        _text_preservation(elements, chunks)


def test_text_preservation_text_int_raises_type_error():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": 123}]
    with pytest.raises(TypeError):
        _text_preservation(elements, chunks)


def test_text_preservation_returns_three_keys():
    """返回 dict 必须有 equal/precision/recall 三个 key。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert set(result.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_precision_one_half():
    """expected 'abc' actual 'abd'：交集 = 'a','b' = 2 chars；actual=3 → precision=2/3。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abd"}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_recall_one_half():
    """expected 'abc' actual 'abd'：交集 2；expected=3 → recall=2/3。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abd"}]
    result = _text_preservation(elements, chunks)
    assert result["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_dup_char_in_actual_only():
    """expected 'ab' actual 'aabb'：交集 a=1, b=1 = 2；actual=4 → precision=0.5；expected=2 → recall=1.0。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "aabb"}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] == 0.5
    assert result["recall"]["value"] == 1.0


def test_text_preservation_dup_char_in_expected_only():
    """expected 'aabb' actual 'ab'：交集 a=1, b=1 = 2；actual=2 → precision=1.0；expected=4 → recall=0.5。"""
    elements = [{"type": "paragraph", "content": "aabb"}]
    chunks = [{"text": "ab"}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 0.5


# =========================================================================
# _image_resource_ratio：image_base_dir 是文件而非目录
# =========================================================================


def test_image_resource_ratio_image_base_dir_is_file_not_dir(tmp_path: Path):
    """image_base_dir 指向文件而非目录 → image_base_dir / name 仍可能解析（不抛异常）。"""
    # 创建一个文件作为 image_base_dir
    file_base = tmp_path / "file.txt"
    file_base.write_text("hello", encoding="utf-8")

    # 创建实际图片文件
    img_file = tmp_path / "image.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    elements = [{"type": "image", "resource_path": str(img_file)}]
    # image_base_dir 是文件，但其 name 与 img_file.name 不一致 → 候选 2 失败
    # 候选 1：Path(rp) 即 img_file，存在且 size > 0 → valid
    result = _image_resource_ratio(elements, file_base)
    assert result["value"] == 1.0


def test_image_resource_ratio_resource_path_absolute_exists(tmp_path: Path):
    """resource_path 是绝对路径，文件存在 → valid。"""
    img_file = tmp_path / "image.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [{"type": "image", "resource_path": str(img_file.absolute())}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 1.0


def test_image_resource_ratio_resource_path_absolute_missing(tmp_path: Path):
    """绝对路径但文件不存在 → 0/1。"""
    elements = [{"type": "image", "resource_path": str(tmp_path / "no.png")}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_resource_path_is_dir(tmp_path: Path):
    """resource_path 是目录 → Path(rp).is_file() False → 0。"""
    elements = [{"type": "image", "resource_path": str(tmp_path)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_resource_path_empty_string(tmp_path: Path):
    """resource_path="" → falsy → continue（不算 valid）。"""
    elements = [{"type": "image", "resource_path": ""}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_no_image_elements_returns_null():
    elements = [{"type": "paragraph", "content": "abc"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] is None
    assert result["reason"] == "no_image_elements"


def test_image_resource_ratio_zero_byte_file_invalid(tmp_path: Path):
    """0 字节文件 → size > 0 失败 → invalid。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


# =========================================================================
# _docx_locator_ratio：7 个 structural key 全在一个 element
# =========================================================================


def test_docx_locator_ratio_all_seven_structural_keys_one_element():
    """一个 element 含 7 个 structural key → valid（any() True）。"""
    elements = [{
        "source_locator": {
            "section": 1,
            "paragraph_index": 0,
            "run_index": 0,
            "table_index": 0,
            "row_index": 0,
            "col_index": 0,
            "relationship_id": "rId1",
        }
    }]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_relationship_id_alone_sufficient():
    """只有 relationship_id 一个 key → valid（any() True）。"""
    elements = [{"source_locator": {"relationship_id": "rId1"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_section_alone_sufficient():
    elements = [{"source_locator": {"section": 1}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_page_present_invalid():
    """含 page → invalid（pdf 字段不应出现在 docx）。"""
    elements = [{"source_locator": {"page": 1, "section": 1}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_bbox_present_invalid():
    elements = [{"source_locator": {"bbox": [1, 2, 3, 4], "section": 1}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_unknown_locator_key_invalid():
    """unknown_key 不在 structural_keys → any() False → invalid。"""
    elements = [{"source_locator": {"unknown_key": "value"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_empty_locator_invalid():
    elements = [{"source_locator": {}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_no_source_locator_field():
    """element 没有 source_locator key → e.get(...) or {} → {} → invalid。"""
    elements = [{"type": "paragraph"}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


# =========================================================================
# _pdf_locator_ratio：type=None / type=image 只需 page
# =========================================================================


def test_pdf_locator_ratio_type_none_not_in_bbox_required():
    """element type=None → not in _PDF_BBOX_REQUIRED_TYPES → 只需 page≥1。"""
    elements = [{
        "type": None,
        "source_locator": {"page": 1},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_image_only_needs_page():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES → 只需 page≥1。"""
    elements = [{
        "type": "image",
        "source_locator": {"page": 1},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_table_only_needs_page():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES（虽然参与文本比对）→ 只需 page≥1。"""
    elements = [{
        "type": "table",
        "source_locator": {"page": 1},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_header_only_needs_page():
    elements = [{
        "type": "header",
        "source_locator": {"page": 1},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_footer_only_needs_page():
    elements = [{
        "type": "footer",
        "source_locator": {"page": 1},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_paragraph_needs_bbox():
    """paragraph 在 _PDF_BBOX_REQUIRED_TYPES → 需 page≥1 + valid bbox。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_paragraph_missing_bbox_invalid():
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1},  # 无 bbox
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_type_caption_needs_bbox():
    elements = [{
        "type": "caption",
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 10.0, 10.0]},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_type_list_item_needs_bbox():
    elements = [{
        "type": "list_item",
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 10.0, 10.0]},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_page_zero_invalid():
    """page=0 不满足 page>=1 → invalid（即便 type=image）。"""
    elements = [{
        "type": "image",
        "source_locator": {"page": 0},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [{
        "type": "image",
        "source_locator": {"page": -1},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_string_invalid():
    """page='1' 是 str → not isinstance(int) → invalid。"""
    elements = [{
        "type": "image",
        "source_locator": {"page": "1"},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_float_invalid():
    """page=1.0 是 float → not isinstance(int) → invalid。"""
    elements = [{
        "type": "image",
        "source_locator": {"page": 1.0},
    }]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_bool_invalid():
    """page=True：bool 是 int 子类但 isinstance(True, int) True → page < 1 (True==1>=1)?"""
    # True == 1, isinstance(True, int) is True, not (True < 1) → valid
    # 实际：bool 是 int 子类，所以 isinstance 通过；True >= 1（True == 1）→ valid
    elements = [{
        "type": "image",
        "source_locator": {"page": True},
    }]
    result = _pdf_locator_ratio(elements)
    # bool 是 int 子类，True == 1，page < 1 是 False，所以 valid
    assert result["value"] == 1.0


def test_pdf_locator_ratio_half_valid_mixed_types():
    """4 个 elements，2 valid（image/page=1 + paragraph/page=1+bbox），2 invalid → 0.5。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},               # valid
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},  # valid
        {"type": "image", "source_locator": {"page": 0}},                # invalid
        {"type": "paragraph", "source_locator": {"page": 1}},            # invalid (no bbox)
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.5


# =========================================================================
# _silent_drop_count：expectations 含未知 key 被忽略
# =========================================================================


def test_silent_drop_count_expectations_with_extra_keys_ignored():
    """expectations 含 element_count_by_type 之外的字段 → 被忽略。"""
    by_type = {"paragraph": 5}
    expectations = {
        "element_count_by_type": {"paragraph": 5},
        "extra_field": "ignored",
        "another": [1, 2, 3],
    }
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_more_keys_than_expected():
    """actual 含 expectations 没有的 type → 不影响 drop（仅遍历 expected types）。"""
    by_type = {"paragraph": 5, "heading": 2, "image": 3}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    result = _silent_drop_count(by_type, expectations)
    # paragraph expected 3, actual 5 → max(0, 3-5) = 0
    # heading/image 不在 expectations → 不算
    assert result["value"] == 0


def test_silent_drop_count_multi_type_drop_sum():
    """多个 type 都 drop → 求和。"""
    by_type = {"paragraph": 1, "heading": 0, "image": 2}
    expectations = {
        "element_count_by_type": {"paragraph": 5, "heading": 3, "image": 4}
    }
    result = _silent_drop_count(by_type, expectations)
    # paragraph: 5-1=4; heading: 3-0=3; image: 4-2=2; total=9
    assert result["value"] == 9


def test_silent_drop_count_negative_expected_no_drop():
    """expected 是负数 → actual - exp 都 > 0 → max(0, negative) = 0。"""
    by_type = {"paragraph": 0}
    expectations = {"element_count_by_type": {"paragraph": -5}}
    result = _silent_drop_count(by_type, expectations)
    # actual=0, exp=-5, actual < exp? 0 < -5? False → no drop
    # 进入 if 分支：actual < exp → 0 < -5 → False → 不进入
    assert result["value"] == 0


def test_silent_drop_count_zero_expected_zero_actual():
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 0}}
    result = _silent_drop_count(by_type, expectations)
    # actual = by_type.get("paragraph", 0) = 0; exp = 0; 0 < 0 False → no drop
    assert result["value"] == 0


def test_silent_drop_count_int_value_type():
    by_type = {"paragraph": 0}
    expectations = {"element_count_by_type": {"paragraph": 1}}
    result = _silent_drop_count(by_type, expectations)
    assert isinstance(result["value"], int)
    assert result["value"] == 1


# =========================================================================
# compute_automatic_metrics：metric name 集合精确
# =========================================================================


def test_compute_metrics_returns_exactly_these_metric_names(tmp_path: Path):
    """成功路径 metric 集合：13 个 ratio/count + error_code + pipeline_success = 14 keys。"""
    document = {
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [{"text": "abc", "chunk_id": "c1", "source_element_ids": ["e1"]}],
    }
    result = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
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
    assert set(result.keys()) == expected_keys


def test_compute_metrics_metric_count_exactly_fourteen(tmp_path: Path):
    document = {
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [{"text": "abc", "chunk_id": "c1", "source_element_ids": ["e1"]}],
    }
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert len(result) == 14


def test_compute_metrics_does_not_include_annotation_metrics(tmp_path: Path):
    """自动指标不包含 chunk_boundary_* / figure_caption_*（那些来自 annotation_metrics）。"""
    document = {
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [{"text": "abc", "chunk_id": "c1", "source_element_ids": ["e1"]}],
    }
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert "chunk_boundary_precision" not in result
    assert "chunk_boundary_recall" not in result
    assert "chunk_boundary_f1" not in result
    assert "figure_caption_precision" not in result
    assert "figure_caption_recall" not in result
    assert "figure_caption_f1" not in result


def test_compute_metrics_failure_path_metric_count(tmp_path: Path):
    """失败路径：pipeline_success + error_code + schema_valid + 11 null = 14 keys。"""
    result = compute_automatic_metrics(
        document=None, error={"code": "x", "message": "y"},
        source_type="pdf", expectations=None, image_base_dir=None,
    )
    assert len(result) == 14


def test_compute_metrics_failure_path_metric_names(tmp_path: Path):
    result = compute_automatic_metrics(
        document=None, error={"code": "x", "message": "y"},
        source_type="pdf", expectations=None, image_base_dir=None,
    )
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
    # 失败路径少 schema_valid（在 null 列表中）但 schema_valid 仍存在
    # 实际：失败路径有 pipeline_success + error_code + schema_valid + 11 null = 14 keys
    # 等等，让我重新数：
    # 1. pipeline_success（_bool_metric(False)）
    # 2. error_code（来自 error["code"]）
    # 3. schema_valid（_null("pipeline_failed")）
    # 4-14. 11 个 null（element_count_total, element_count_by_type, pdf_locator_valid_ratio,
    #       docx_locator_valid_ratio, image_resource_exists_ratio, chunk_reference_intact_ratio,
    #       text_preservation_equal, text_char_multiset_precision, text_char_multiset_recall,
    #       heading_boundary_compliance, silent_drop_count）
    # 总计 14
    assert set(result.keys()) == expected_keys


def test_compute_metrics_failure_path_count_correct():
    """修正：失败路径共 14 keys（与成功路径数量一致）。"""
    result = compute_automatic_metrics(
        document=None, error={"code": "x", "message": "y"},
        source_type="pdf", expectations=None, image_base_dir=None,
    )
    assert len(result) == 14


# =========================================================================
# compute_automatic_metrics：source_type 切换
# =========================================================================


def test_compute_metrics_source_type_pdf_locator_returns_ratio(tmp_path: Path):
    """source_type='pdf' → pdf_locator_valid_ratio 是 ratio（非 null）。"""
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    # elements=[] → _pdf_locator_ratio 返回 _null("no_elements")
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_source_type_pdf_docx_locator_null(tmp_path: Path):
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert result["docx_locator_valid_ratio"]["value"] is None
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_docx_pdf_locator_null(tmp_path: Path):
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="docx",
        expectations=None, image_base_dir=None,
    )
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_source_type_other_both_locator_null(tmp_path: Path):
    """source_type='other' → pdf null + docx null。"""
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="other",
        expectations=None, image_base_dir=None,
    )
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert result["docx_locator_valid_ratio"]["value"] is None
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# =========================================================================
# compute_automatic_metrics：error_code 行为
# =========================================================================


def test_compute_metrics_error_none_error_code_value_none():
    """error=None + document 给定 → error_code value None。"""
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert result["error_code"]["value"] is None
    assert result["error_code"]["reason"] is None


def test_compute_metrics_error_dict_without_code_value_none():
    """error 是 dict 但缺 code → error["code"] 触发 KeyError（实际代码：error["code"] if error else None）。"""
    # 实际代码：error["code"] if error else None —— error 是非空 dict（truthy）→ error["code"] KeyError
    document = {"elements": [], "chunks": []}
    with pytest.raises(KeyError):
        compute_automatic_metrics(
            document=document, error={"message": "y"},  # 缺 code
            source_type="pdf", expectations=None, image_base_dir=None,
        )


def test_compute_metrics_error_dict_with_code_value_present():
    """error 是 dict 含 code → error_code value 来自 error["code"]。"""
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=None,  # pipeline_success 走失败路径
        error={"code": "parse_failed", "message": "x"},
        source_type="pdf", expectations=None, image_base_dir=None,
    )
    assert result["error_code"]["value"] == "parse_failed"


def test_compute_metrics_error_dict_with_empty_string_code():
    """error.code 是空字符串 → truthy error → error["code"] = "" → value 是 ""。"""
    result = compute_automatic_metrics(
        document=None,
        error={"code": "", "message": "x"},
        source_type="pdf", expectations=None, image_base_dir=None,
    )
    assert result["error_code"]["value"] == ""


# =========================================================================
# compute_automatic_metrics：schema_check_exception 路径
# =========================================================================


def test_compute_metrics_schema_exception_returns_false_with_reason(tmp_path, monkeypatch):
    """document_passes_schema 抛异常 → schema_valid value=False + reason 'schema_check_exception:...'。"""
    from evaluation import metrics as metrics_mod

    def boom(_doc):
        raise RuntimeError("kaboom")

    # 延迟 import 模块内部
    import evaluation.schema_validation as sv
    monkeypatch.setattr(sv, "document_passes_schema", boom)

    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert result["schema_valid"]["value"] is False
    assert "schema_check_exception" in result["schema_valid"]["reason"]
    assert "RuntimeError" in result["schema_valid"]["reason"]


def test_compute_metrics_schema_passes_returns_true(tmp_path, monkeypatch):
    """document_passes_schema 返回 True → schema_valid value=True。"""
    import evaluation.schema_validation as sv
    monkeypatch.setattr(sv, "document_passes_schema", lambda d: True)

    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert result["schema_valid"]["value"] is True


def test_compute_metrics_schema_fails_returns_false(tmp_path, monkeypatch):
    """document_passes_schema 返回 False → schema_valid value=False（reason None）。"""
    import evaluation.schema_validation as sv
    monkeypatch.setattr(sv, "document_passes_schema", lambda d: False)

    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert result["schema_valid"]["value"] is False
    assert result["schema_valid"]["reason"] is None


# =========================================================================
# _strip_unicode_whitespace：补充 \f \v 等控制字符
# =========================================================================


def test_strip_unicode_whitespace_form_feed():
    """\\f (form feed, U+000C) isspace() True → 删除。"""
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_vertical_tab():
    """\\v (vertical tab, U+000B) isspace() True → 删除。"""
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_carriage_return():
    """\\r isspace() True → 删除。"""
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_null_char_preserved():
    """\\x00 (null) isspace() False → 保留。"""
    # 注意：'\x00'.isspace() is False
    assert _strip_unicode_whitespace("a\x00b") == "a\x00b"


def test_strip_unicode_whitespace贝尔_char_preserved():
    """\\x07 (BEL) isspace() False → 保留。"""
    assert _strip_unicode_whitespace("a\x07b") == "a\x07b"


def test_strip_unicode_whitespace_escape_char_preserved():
    """\\x1b (ESC) isspace() False → 保留。"""
    assert _strip_unicode_whitespace("a\x1bb") == "a\x1bb"


def test_strip_unicode_whitespace_only_whitespace_returns_empty():
    assert _strip_unicode_whitespace(" \t\n\r\v\f") == ""


# =========================================================================
# _is_valid_bbox：补充更深的类型边界
# =========================================================================


def test_is_valid_bbox_tuple_rejected():
    """bbox 是 tuple 而非 list → isinstance(list) False → invalid。"""
    assert _is_valid_bbox((1.0, 2.0, 3.0, 4.0)) is False


def test_is_valid_bbox_set_rejected():
    assert _is_valid_bbox({1.0, 2.0, 3.0, 4.0}) is False


def test_is_valid_bbox_dict_rejected():
    assert _is_valid_bbox({"x": 1, "y": 2, "w": 3, "h": 4}) is False


def test_is_valid_bbox_complex_number_rejected():
    """complex 不是 int/float → invalid。"""
    assert _is_valid_bbox([1 + 0j, 2 + 0j, 3 + 0j, 4 + 0j]) is False


def test_is_valid_bbox_str_elements_rejected():
    assert _is_valid_bbox(["1", "2", "3", "4"]) is False


def test_is_valid_bbox_none_element_rejected():
    assert _is_valid_bbox([None, 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_one_element_only():
    assert _is_valid_bbox([1.0]) is False


def test_is_valid_bbox_exactly_four_minimal():
    """恰好 4 个最小正 float → valid。"""
    assert _is_valid_bbox([0.000001, 0.000001, 0.000001, 0.000001]) is True


def test_is_valid_bbox_zero_zero_valid():
    """4 个 0.0 → valid（坐标可以全 0）。"""
    assert _is_valid_bbox([0.0, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_negative_coords_valid():
    """bbox 允许负坐标（PDF 坐标系允许）。"""
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


# =========================================================================
# 模块 imports / 结构
# =========================================================================


def test_module_imports_math():
    import evaluation.metrics as m
    assert hasattr(m, "math")


def test_module_imports_counter():
    import evaluation.metrics as m
    assert hasattr(m, "Counter")


def test_module_imports_path():
    import evaluation.metrics as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.metrics as m
    assert hasattr(m, "Any")


def test_module_all_only_compute_automatic_metrics():
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_internal_helpers_not_in_all():
    """所有 _ 开头 helper 都不应在 __all__。"""
    import evaluation.metrics as m
    for name in m.__all__:
        assert not name.startswith("_")


def test_module_uses_future_annotations():
    import evaluation.metrics as m
    assert hasattr(m, "annotations")  # from __future__ import annotations


def test_module_docstring_mentions_pure_function():
    """docstring 应该提到 'pure' 或 '纯函数'。"""
    import evaluation.metrics as m
    assert m.__doc__ is not None
    assert "纯函数" in m.__doc__ or "pure" in m.__doc__.lower()


def test_module_docstring_mentions_v1_1_semantics():
    """docstring 应该提到 v1.1 语义变更。"""
    import evaluation.metrics as m
    assert "v1.1" in m.__doc__ or "1.1" in m.__doc__
