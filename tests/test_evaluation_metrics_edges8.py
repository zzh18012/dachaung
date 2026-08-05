r"""evaluation/metrics.py 边角测试 - 第八轮（Round 193）。

补强已有 base/edges/edges2-7（共 1103 测试）未覆盖的深度：
- 构造器（_null/_ratio/_bool_metric/_int_metric）类型边界
- _is_valid_bbox NaN/Inf/bool/列表长度/非 list 全面拒绝
- _pdf_locator_ratio 多元素混合 + 非 BBOX 类型 page-only 路径
- _docx_locator_ratio 结构键矩阵（section/paragraph_index/run_index 等）+ page/bbox 拒绝
- _image_resource_ratio OSError 路径 + image_base_dir .name 兼容
- _chunk_reference_ratio 多 chunk 混合（含空 ids/None）
- _strip_unicode_whitespace Unicode 空白集合（NBSP/em/en/ideographic/LS/PS）
- _text_preservation Counter 多集合语义 + 单边空 + 全 image 元素
- _heading_boundary_ratio 多 heading 多 chunk 顺序敏感性
- _silent_drop_count 完整 expectations 边界
- compute_automatic_metrics 顶层各 source_type / error / schema 异常路径
- 模块结构与签名深度
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
# 构造器深度
# =========================================================================


def test_null_returns_value_none():
    m = _null("any_reason")
    assert m["value"] is None


def test_null_returns_reason_unchanged():
    m = _null("some_specific_reason_text")
    assert m["reason"] == "some_specific_reason_text"


def test_null_empty_string_reason():
    m = _null("")
    assert m["reason"] == ""
    assert m["value"] is None


def test_null_unicode_reason():
    m = _null("原因")
    assert m["reason"] == "原因"


def test_ratio_zero_returns_float_zero():
    m = _ratio(0.0)
    assert m["value"] == 0.0
    assert isinstance(m["value"], float)


def test_ratio_one_returns_float_one():
    m = _ratio(1.0)
    assert m["value"] == 1.0
    assert isinstance(m["value"], float)


def test_ratio_int_input_coerced_to_float():
    m = _ratio(0)
    assert isinstance(m["value"], float)


def test_ratio_half_value():
    m = _ratio(0.5)
    assert m["value"] == 0.5


def test_ratio_reason_always_none():
    m = _ratio(0.7)
    assert m["reason"] is None


def test_ratio_negative_input_returns_negative():
    """构造器不验证值域；调用方负责传 [0,1]。"""
    m = _ratio(-0.5)
    assert m["value"] == -0.5


def test_ratio_gt_one_input_unchanged():
    m = _ratio(1.5)
    assert m["value"] == 1.5


def test_bool_metric_true():
    m = _bool_metric(True)
    assert m["value"] is True
    assert m["reason"] is None


def test_bool_metric_false():
    m = _bool_metric(False)
    assert m["value"] is False
    assert m["reason"] is None


def test_bool_metric_int_zero_coerced():
    m = _bool_metric(0)
    assert m["value"] is False


def test_bool_metric_int_one_coerced():
    m = _bool_metric(1)
    assert m["value"] is True


def test_bool_metric_empty_string_coerced():
    m = _bool_metric("")
    assert m["value"] is False


def test_bool_metric_nonempty_string_coerced():
    m = _bool_metric("yes")
    assert m["value"] is True


def test_bool_metric_none_coerced():
    m = _bool_metric(None)
    assert m["value"] is False


def test_int_metric_zero():
    m = _int_metric(0)
    assert m["value"] == 0
    assert isinstance(m["value"], int)


def test_int_metric_positive():
    m = _int_metric(42)
    assert m["value"] == 42


def test_int_metric_negative():
    m = _int_metric(-7)
    assert m["value"] == -7


def test_int_metric_float_input_coerced():
    """int(2.9) → 2，不抛异常。"""
    m = _int_metric(2.9)
    assert m["value"] == 2


def test_int_metric_bool_input():
    """int(True) == 1。"""
    m = _int_metric(True)
    assert m["value"] == 1


def test_int_metric_reason_always_none():
    m = _int_metric(5)
    assert m["reason"] is None


# =========================================================================
# _is_valid_bbox 深度
# =========================================================================


def test_is_valid_bbox_four_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_four_floats():
    assert _is_valid_bbox([0.0, 0.5, 100.5, 200.0]) is True


def test_is_valid_bbox_negative_numbers():
    """负值也算合法（caller 决定语义）。"""
    assert _is_valid_bbox([-1, -1, 0, 0]) is True


def test_is_valid_bbox_three_elements():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_five_elements():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_tuple_not_list():
    """类型必须是 list，不是 tuple。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_string_elements():
    assert _is_valid_bbox(["0", "0", "100", "100"]) is False


def test_is_valid_bbox_mixed_types():
    assert _is_valid_bbox([0, "0", 100, 100]) is False


def test_is_valid_bbox_bool_true_rejected():
    """bool 是 int 子类但显式拒绝。"""
    assert _is_valid_bbox([True, 0, 100, 100]) is False


def test_is_valid_bbox_all_bools():
    assert _is_valid_bbox([True, False, True, False]) is False


def test_is_valid_bbox_nan_rejected():
    assert _is_valid_bbox([float("nan"), 0, 100, 100]) is False


def test_is_valid_bbox_inf_rejected():
    assert _is_valid_bbox([float("inf"), 0, 100, 100]) is False


def test_is_valid_bbox_neg_inf_rejected():
    assert _is_valid_bbox([float("-inf"), 0, 100, 100]) is False


def test_is_valid_bbox_none_rejected():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_none_element():
    assert _is_valid_bbox([None, 0, 100, 100]) is False


def test_is_valid_bbox_dict_rejected():
    assert _is_valid_bbox({"x": 0, "y": 0, "w": 100, "h": 100}) is False


# =========================================================================
# _pdf_locator_ratio 深度
# =========================================================================


def test_pdf_locator_ratio_empty_returns_no_elements_null():
    result = _pdf_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_pdf_locator_ratio_single_image_with_page_only():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES，只需 page。"""
    elements = [
        {"type": "image", "element_id": "i1", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_single_paragraph_with_page_no_bbox():
    """paragraph 在 BBOX_REQUIRED，缺 bbox → 无效。"""
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_single_paragraph_with_page_and_bbox():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_page_zero_invalid():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": 0, "bbox": [0, 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": -1, "bbox": [0, 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_none_invalid():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": None, "bbox": [0, 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_string_invalid():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": "1", "bbox": [0, 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_float_invalid():
    """page=1.0 是 float 不是 int → 无效。"""
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": 1.0, "bbox": [0, 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_missing_source_locator():
    """source_locator 缺失 → loc 默认为 {} → page 缺失 → 无效。"""
    elements = [{"type": "paragraph", "element_id": "p1"}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_source_locator_none():
    """source_locator 显式 None → loc 默认 {}。"""
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": None},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
        },
        {
            "type": "paragraph",
            "element_id": "p2",
            "source_locator": {"page": 0},
        },
        {"type": "image", "element_id": "i1", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == pytest.approx(2 / 3)


def test_pdf_locator_ratio_caption_requires_bbox():
    """caption 在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [
        {
            "type": "caption",
            "element_id": "c1",
            "source_locator": {"page": 1},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_header_only_needs_page():
    """header 不在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [
        {"type": "header", "element_id": "h1", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_table_only_needs_page():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [
        {"type": "table", "element_id": "t1", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_footer_only_needs_page():
    elements = [
        {"type": "footer", "element_id": "f1", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_list_item_requires_bbox():
    """list_item 在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [
        {
            "type": "list_item",
            "element_id": "l1",
            "source_locator": {"page": 1},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_invalid_bbox_rejected():
    """bbox 有 NaN → 无效。"""
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"page": 1, "bbox": [float("nan"), 0, 100, 100]},
        },
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_all_invalid_returns_zero():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {}},
        {"type": "paragraph", "element_id": "p2", "source_locator": {}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


# =========================================================================
# _docx_locator_ratio 深度
# =========================================================================


def test_docx_locator_ratio_empty_returns_no_elements_null():
    result = _docx_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_docx_locator_ratio_section_valid():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"section": "intro"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_valid():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"paragraph_index": 0}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_run_index_valid():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"run_index": 5}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_table_index_valid():
    elements = [
        {"type": "table", "element_id": "t1", "source_locator": {"table_index": 2}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_row_index_valid():
    elements = [
        {"type": "table", "element_id": "t1", "source_locator": {"row_index": 1}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_col_index_valid():
    elements = [
        {"type": "table", "element_id": "t1", "source_locator": {"col_index": 3}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_relationship_id_valid():
    elements = [
        {"type": "image", "element_id": "i1", "source_locator": {"relationship_id": "rId1"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_page_key_rejects():
    """DOCX 不允许 page 键（PDF 才有）。"""
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"page": 1, "section": "x"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_bbox_key_rejects():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"bbox": [0, 0, 100, 100], "section": "x"},
        },
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_rejects():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"foo": "bar"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_empty_locator_rejects():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_missing_locator_rejects():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"section": "x"}},
        {"type": "paragraph", "element_id": "p2", "source_locator": {}},
        {"type": "paragraph", "element_id": "p3", "source_locator": {"page": 1}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == pytest.approx(1 / 3)


def test_docx_locator_ratio_multiple_structural_keys_one_sufficient():
    elements = [
        {
            "type": "paragraph",
            "element_id": "p1",
            "source_locator": {"section": "x", "paragraph_index": 0, "run_index": 0},
        },
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


# =========================================================================
# _image_resource_ratio 深度
# =========================================================================


def test_image_resource_ratio_no_images_returns_null(tmp_path: Path):
    """no image elements → null + no_image_elements。"""
    elements = [{"type": "paragraph", "element_id": "p1"}]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] is None
    assert result["reason"] == "no_image_elements"


def test_image_resource_ratio_no_image_base_dir_relative_path(tmp_path: Path):
    """image_base_dir=None 且 resource_path 是相对路径 → 找不到 → valid=0。"""
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": "missing.png"},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_filename_with_image_base_dir(tmp_path: Path):
    """resource_path 只是文件名，image_base_dir 提供目录。"""
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    p = img_dir / "x.png"
    p.write_bytes(b"data")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": "x.png"},
    ]
    result = _image_resource_ratio(elements, img_dir)
    assert result["value"] == 1.0


def test_image_resource_ratio_filename_in_subdir_with_image_base_dir(tmp_path: Path):
    """resource_path = 'sub/x.png'，image_base_dir 拼接只取 .name。"""
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    p = img_dir / "x.png"
    p.write_bytes(b"data")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": "sub/x.png"},
    ]
    result = _image_resource_ratio(elements, img_dir)
    assert result["value"] == 1.0


def test_image_resource_ratio_absolute_path_ignores_image_base_dir(tmp_path: Path):
    """绝对路径直接用，image_base_dir 也试 .name 但绝对路径已生效。"""
    p = tmp_path / "abs.png"
    p.write_bytes(b"data")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(p)},
    ]
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    result = _image_resource_ratio(elements, other_dir)
    assert result["value"] == 1.0


def test_image_resource_ratio_three_images_mixed(tmp_path: Path):
    """3 张 image，2 张存在 1 张不存在 → ratio=2/3。"""
    p1 = tmp_path / "ok1.png"
    p1.write_bytes(b"data1")
    p2 = tmp_path / "ok2.png"
    p2.write_bytes(b"data2")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(p1)},
        {"type": "image", "element_id": "i2", "resource_path": str(p2)},
        {"type": "image", "element_id": "i3", "resource_path": "missing.png"},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == pytest.approx(2 / 3)


def test_image_resource_ratio_resource_path_zero_size(tmp_path: Path):
    """size=0 跳过 → valid=0。"""
    p = tmp_path / "empty.png"
    p.write_bytes(b"")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(p)},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_resource_path_is_dir(tmp_path: Path):
    """resource_path 是目录 → is_file()=False → valid=0。"""
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(tmp_path)},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_oserror_caught(tmp_path: Path, monkeypatch):
    """Path.is_file() 抛 OSError → 跳过 candidate，继续。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"data")

    def fake_is_file(self):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "is_file", fake_is_file)
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(p)},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_resource_path_with_special_chars(tmp_path: Path):
    """文件名包含中文/特殊字符。"""
    p = tmp_path / "图片.png"
    p.write_bytes(b"data")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": str(p)},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 1.0


def test_image_resource_ratio_image_base_dir_with_two_candidates_second_ok(
    tmp_path: Path,
):
    """rp 直接找不到，image_base_dir / .name 能找到 → valid。"""
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    p = img_dir / "img.png"
    p.write_bytes(b"data")
    # rp 指向不存在的子路径，但 .name == "img.png" 能在 img_dir 找到
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": "subdir/img.png"},
    ]
    result = _image_resource_ratio(elements, img_dir)
    assert result["value"] == 1.0


# =========================================================================
# _chunk_reference_ratio 深度
# =========================================================================


def test_chunk_reference_ratio_empty_chunks_returns_null():
    elements = [{"element_id": "e1"}]
    result = _chunk_reference_ratio(elements, [])
    assert result["value"] is None
    assert result["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_with_no_source_ids_skipped():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    result = _chunk_reference_ratio(elements, chunks)
    # 空 ids 视为 "not valid" → 0/1 = 0.0
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunk_with_missing_key():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x"}]  # 无 source_element_ids
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunk_with_none_source_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": None}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_valid_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_unknown_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e_unknown"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_multiple_ids_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"text": "x", "source_element_ids": ["e1", "e2"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_multiple_ids_partial_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1", "unknown"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_mixed_chunks():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},  # valid
        {"text": "y", "source_element_ids": ["unknown"]},  # invalid
        {"text": "z", "source_element_ids": ["e2"]},  # valid
        {"text": "w", "source_element_ids": []},  # skipped (not valid)
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.5  # 2/4


def test_chunk_reference_ratio_empty_elements_no_chunks():
    """no_chunks 优先 → null。"""
    result = _chunk_reference_ratio([], [])
    assert result["value"] is None


def test_chunk_reference_ratio_empty_elements_with_chunks():
    """elements=[] 但 chunks 非空 → 所有 id 都不在 elem_ids → 全 0。"""
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    result = _chunk_reference_ratio([], chunks)
    assert result["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace 深度
# =========================================================================


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ascii_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_ascii_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_ascii_carriage_return():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_ascii_form_feed():
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_ascii_vertical_tab():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_nbsp():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_thin_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_hair_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_narrow_nbsp():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """非空白字符全部保留，包括标点。"""
    assert _strip_unicode_whitespace("a, b. c!") == "a,b.c!"


def test_strip_unicode_whitespace_preserves_emoji():
    """emoji 是非空白。"""
    assert _strip_unicode_whitespace("a 🎉 b") == "a🎉b"


def test_strip_unicode_whitespace_preserves_cjk():
    assert _strip_unicode_whitespace("你 好 世 界") == "你好世界"


def test_strip_unicode_whitespace_preserves_digits():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_mixed_kinds_at_once():
    """多种空白混合一次性删除。"""
    assert _strip_unicode_whitespace("a b\tc\nd　e") == "abcde"


# =========================================================================
# _text_preservation 深度
# =========================================================================


def test_text_preservation_equal_simple():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_with_whitespace_in_content_ignored():
    """空白被删除，所以 "a b" == "ab" 等同。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "a b c"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_extra_chars_in_actual():
    """expected='abc', actual='abcd' → equal=False, precision=3/4, recall=3/3。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "abcd", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 0.75
    assert result["recall"]["value"] == 1.0


def test_text_preservation_missing_chars_in_actual():
    """expected='abcd', actual='abc' → precision=1, recall=3/4。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abcd"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 0.75


def test_text_preservation_reorder_not_equal():
    """顺序不同 → equal=False，但 Counter 仍然交集 100%。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "cba", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_counter_duplicate_chars():
    """expected='aabb', actual='abab' → equal=False（顺序字符不同），
    但 Counter 相同 → precision=recall=1.0（不区分顺序）。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "aabb"}]
    chunks = [{"text": "abab", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_counter_duplicate_mismatch():
    """expected='aabb', actual='ab' → equal=False，
    common = min(2,1)+min(2,1) = 2,
    precision = 2/2 = 1.0,
    recall = 2/4 = 0.5。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "aabb"}]
    chunks = [{"text": "ab", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 0.5


def test_text_preservation_completely_disjoint():
    """expected='abc', actual='xyz' → equal=False, common=0。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "xyz", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 0.0
    assert result["recall"]["value"] == 0.0


def test_text_preservation_both_empty_returns_null_precision_recall():
    """expected='' actual='' → equal=True, precision/recall=null。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": ""}]
    chunks = [{"text": "", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] is None
    assert result["precision"]["reason"] == "empty_expected_and_actual"
    assert result["recall"]["value"] is None
    assert result["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_both_whitespace_only_returns_null():
    """expected=' ' actual='\t' → 删除空白后都为空 → null。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": " "}]
    chunks = [{"text": "\t", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] is None


def test_text_preservation_empty_actual_with_content_expected():
    """expected='abc' actual='' → precision=null empty_actual, recall=0。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] is None
    assert result["precision"]["reason"] == "empty_actual"
    assert result["recall"]["value"] == 0.0


def test_text_preservation_empty_expected_with_actual():
    """expected='' actual='abc' → recall=null empty_expected, precision=0。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": ""}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["recall"]["value"] is None
    assert result["recall"]["reason"] == "empty_expected"
    assert result["precision"]["value"] == 0.0


def test_text_preservation_skips_image_elements():
    """image element 的 content 不参与计算。"""
    elements = [
        {"type": "paragraph", "element_id": "p1", "content": "abc"},
        {"type": "image", "element_id": "i1", "content": "XYZ"},
    ]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_only_image_elements():
    """全部 image → expected='' → 与 empty actual 相同。"""
    elements = [
        {"type": "image", "element_id": "i1", "content": "XYZ"},
    ]
    chunks = [{"text": "", "source_element_ids": ["i1"]}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] is None


def test_text_preservation_content_none_treated_as_empty():
    elements = [{"type": "paragraph", "element_id": "p1", "content": None}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["recall"]["value"] is None


def test_text_preservation_content_missing_treated_as_empty():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False


def test_text_preservation_chunk_text_none_treated_as_empty():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abc"}]
    chunks = [{"text": None, "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] is None


def test_text_preservation_multiple_chunks_concat():
    """多 chunk 文本拼接后比对。"""
    elements = [{"type": "paragraph", "element_id": "p1", "content": "abcdef"}]
    chunks = [
        {"text": "abc", "source_element_ids": ["p1"]},
        {"text": "def", "source_element_ids": ["p1"]},
    ]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_multiple_elements_concat():
    """多 element 拼接。"""
    elements = [
        {"type": "heading", "element_id": "h1", "content": "Hello"},
        {"type": "paragraph", "element_id": "p1", "content": "World"},
    ]
    chunks = [{"text": "HelloWorld", "source_element_ids": ["h1", "p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_type_none_treated_as_text():
    """type=None 不等于 'image' → 参与文本比对。"""
    elements = [{"type": None, "element_id": "p1", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_returns_dict_with_three_keys():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "x"}]
    chunks = [{"text": "x", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    assert set(result.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_metric_has_value_and_reason():
    elements = [{"type": "paragraph", "element_id": "p1", "content": "x"}]
    chunks = [{"text": "x", "source_element_ids": ["p1"]}]
    result = _text_preservation(elements, chunks)
    for m in result.values():
        assert "value" in m
        assert "reason" in m


# =========================================================================
# _heading_boundary_ratio 深度
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"text": "x", "source_element_ids": ["p1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] is None
    assert result["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_single_heading_first_in_chunk():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_heading_not_first():
    """heading 是 chunk 第二个元素 → 不匹配。"""
    elements = [
        {"type": "paragraph", "element_id": "p1"},
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"text": "x", "source_element_ids": ["p1", "h1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_heading_id_not_in_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["other_id"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_chunks_empty_list():
    """no chunks → matched=0 → 0.0（不是 null，因为 headings 非空）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    result = _heading_boundary_ratio(elements, [])
    assert result["value"] == 0.0


def test_heading_boundary_ratio_chunks_with_empty_ids():
    """chunks 存在但 source_element_ids 为空 → no chunk_first_ids → matched=0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_multiple_headings_some_matched():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},
        {"text": "y", "source_element_ids": ["p1", "h2"]},  # h2 not first
        {"text": "z", "source_element_ids": ["h3"]},
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == pytest.approx(2 / 3)


def test_heading_boundary_ratio_duplicate_heading_first_ids():
    """两个 chunk 都以 h1 开头 → chunk_first_ids 去重 → 仍只算 h1 一次（matched=1）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},
        {"text": "y", "source_element_ids": ["h1"]},
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_only_paragraphs():
    """elements 全是 paragraph → null + no_heading_elements。"""
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"text": "x", "source_element_ids": ["p1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] is None


# =========================================================================
# _silent_drop_count 深度
# =========================================================================


def test_silent_drop_count_no_expectations():
    result = _silent_drop_count({"paragraph": 5}, None)
    assert result["value"] is None
    assert result["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations():
    result = _silent_drop_count({"paragraph": 5}, {})
    assert result["value"] is None
    assert result["reason"] == "no_expectations"


def test_silent_drop_count_empty_expected_counts():
    expectations = {"some_other_key": "value"}
    result = _silent_drop_count({"paragraph": 5}, expectations)
    assert result["value"] is None
    assert result["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expected_counts_empty_dict():
    expectations = {"element_count_by_type": {}}
    result = _silent_drop_count({"paragraph": 5}, expectations)
    assert result["value"] is None


def test_silent_drop_count_no_drop():
    """actual >= expected → 0 drops。"""
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count({"paragraph": 5}, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_greater_than_expected():
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count({"paragraph": 10}, expectations)
    assert result["value"] == 0


def test_silent_drop_count_one_drop():
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count({"paragraph": 3}, expectations)
    assert result["value"] == 2


def test_silent_drop_count_multiple_types():
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 3}}
    result = _silent_drop_count({"paragraph": 4, "heading": 1}, expectations)
    assert result["value"] == 3  # (5-4) + (3-1)


def test_silent_drop_count_unknown_type_in_expected():
    """expected 含未知 type → 视为完全丢失。"""
    expectations = {"element_count_by_type": {"unknown_type": 5}}
    result = _silent_drop_count({}, expectations)
    assert result["value"] == 5


def test_silent_drop_count_actual_zero():
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count({}, expectations)
    assert result["value"] == 5


def test_silent_drop_count_mixed_drop_no_drop():
    expectations = {"element_count_by_type": {"a": 5, "b": 3, "c": 2}}
    result = _silent_drop_count({"a": 3, "b": 3, "c": 4}, expectations)
    # a: max(0, 5-3) = 2; b: max(0, 3-3) = 0; c: max(0, 2-4) = 0
    assert result["value"] == 2


def test_silent_drop_count_returns_int_metric():
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count({"paragraph": 0}, expectations)
    assert result["reason"] is None
    assert isinstance(result["value"], int)


# =========================================================================
# compute_automatic_metrics 顶层
# =========================================================================


def test_compute_automatic_metrics_document_none_error_none():
    result = compute_automatic_metrics(None, None, "pdf", None)
    assert result["pipeline_success"]["value"] is False
    assert result["error_code"]["value"] is None
    assert result["schema_valid"]["value"] is None
    assert result["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_document_none_with_error():
    error = {"code": "PARSE_FAILED", "message": "boom"}
    result = compute_automatic_metrics(None, error, "pdf", None)
    assert result["pipeline_success"]["value"] is False
    assert result["error_code"]["value"] == "PARSE_FAILED"


def test_compute_automatic_metrics_error_with_code_only():
    """error 只要有 code key 即可。"""
    error = {"code": "X"}
    result = compute_automatic_metrics(None, error, "pdf", None)
    assert result["error_code"]["value"] == "X"


def test_compute_automatic_metrics_all_metrics_present_on_failure():
    """document=None 时所有 14 个 metric 都在。"""
    result = compute_automatic_metrics(None, None, "pdf", None)
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
    assert expected_keys.issubset(result.keys())


def test_compute_automatic_metrics_minimal_valid_document():
    doc = {
        "elements": [],
        "chunks": [],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["pipeline_success"]["value"] is True
    assert result["element_count_total"]["value"] == 0


def test_compute_automatic_metrics_minimal_docx_locator_null_for_pdf():
    """source_type='pdf' → docx_locator_valid_ratio=null。"""
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["docx_locator_valid_ratio"]["value"] is None
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_minimal_pdf_locator_null_for_docx():
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "docx", None)
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_automatic_metrics_other_source_type_both_null():
    """source_type 非 pdf/docx → 两个 locator ratio 都 null。"""
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "other", None)
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["docx_locator_valid_ratio"]["value"] is None


def test_compute_automatic_metrics_no_image_returns_null():
    doc = {"elements": [{"type": "paragraph", "element_id": "p1"}], "chunks": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["image_resource_exists_ratio"]["value"] is None
    assert result["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_automatic_metrics_no_chunks_returns_null_chunk_ratio():
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["chunk_reference_intact_ratio"]["value"] is None
    assert result["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_automatic_metrics_no_headings_returns_null_boundary():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1"}],
        "chunks": [],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["heading_boundary_compliance"]["value"] is None


def test_compute_automatic_metrics_no_expectations_returns_null_drop():
    doc = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["silent_drop_count"]["value"] is None
    assert result["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_automatic_metrics_with_expectations():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert result["silent_drop_count"]["value"] == 4  # 5 - 1


def test_compute_automatic_metrics_elements_missing_key_defaults_empty():
    """document 没有 elements 键 → 默认 []。"""
    doc = {}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["element_count_total"]["value"] == 0


def test_compute_automatic_metrics_chunks_missing_key_defaults_empty():
    doc = {"elements": []}
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["chunk_reference_intact_ratio"]["value"] is None


def test_compute_automatic_metrics_schema_invalid_for_bad_doc():
    """不合法 document（缺 source_hash 等）→ schema_valid=False。"""
    doc = {"elements": [], "chunks": []}  # 缺 source_hash/source_type
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["schema_valid"]["value"] is False


def test_compute_automatic_metrics_schema_exception_caught(monkeypatch):
    """document_passes_schema 抛异常 → schema_valid=False with exception reason。"""
    doc = {"elements": [], "chunks": []}

    def boom(_doc):
        raise ValueError("test")

    import evaluation.schema_validation as sv
    monkeypatch.setattr(sv, "document_passes_schema", boom)
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["schema_valid"]["value"] is False
    assert "ValueError" in result["schema_valid"]["reason"]


def test_compute_automatic_metrics_error_provided_with_document():
    """罕见路径：document 与 error 同时给 → pipeline_success=False，
    但因为 document 不为 None，仍计算后续 metric。"""
    doc = {"elements": [], "chunks": []}
    error = {"code": "X"}
    result = compute_automatic_metrics(doc, error, "pdf", None)
    assert result["pipeline_success"]["value"] is False
    assert result["error_code"]["value"] == "X"
    # 但 element_count_total 仍计算
    assert result["element_count_total"]["value"] == 0


def test_compute_automatic_metrics_by_type_includes_unknown():
    """缺 type 的 element → 归入 "unknown" 桶。"""
    doc = {
        "elements": [{"element_id": "p1"}],  # 无 type
        "chunks": [],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = result["element_count_by_type"]["value"]
    assert by_type.get("unknown") == 1


def test_compute_automatic_metrics_by_type_groups():
    doc = {
        "elements": [
            {"element_id": "p1", "type": "paragraph"},
            {"element_id": "p2", "type": "paragraph"},
            {"element_id": "h1", "type": "heading"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = result["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1}


def test_compute_automatic_metrics_by_type_none_value():
    """type=None → dict key 是 None（.get 返回 None 值，不用 default "unknown"）。"""
    doc = {
        "elements": [{"element_id": "p1", "type": None}],
        "chunks": [],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = result["element_count_by_type"]["value"]
    assert by_type.get(None) == 1
    assert None in by_type


def test_compute_automatic_metrics_image_base_dir_used(tmp_path: Path):
    """image_base_dir 关键字传入 → 用于 image_resource_exists_ratio。"""
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    p = img_dir / "x.png"
    p.write_bytes(b"data")
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1", "resource_path": "x.png"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        doc, None, "pdf", None, image_base_dir=img_dir
    )
    assert result["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_text_preservation_full_pipeline():
    """全流程：element content → chunk text 保留。"""
    doc = {
        "elements": [
            {"element_id": "h1", "type": "heading", "content": "Title"},
            {"element_id": "p1", "type": "paragraph", "content": "Body"},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Body", "source_element_ids": ["p1"]},
        ],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["text_preservation_equal"]["value"] is True
    assert result["text_char_multiset_precision"]["value"] == 1.0
    assert result["text_char_multiset_recall"]["value"] == 1.0


# =========================================================================
# 模块结构与常量
# =========================================================================


def test_text_types_tuple_contains_expected():
    expected = {"heading", "paragraph", "list_item", "table", "caption", "header", "footer"}
    assert set(_TEXT_TYPES) == expected


def test_text_types_does_not_include_image():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_subset_of_text_types():
    """BBOX_REQUIRED 是 TEXT_TYPES 的子集。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_types_exact_set():
    expected = {"heading", "paragraph", "caption", "list_item"}
    assert set(_PDF_BBOX_REQUIRED_TYPES) == expected


def test_pdf_bbox_required_types_excludes_table_header_footer():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_all_exports_only_public():
    """__all__ 只导出公开 API。"""
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_has_math_import():
    import evaluation.metrics as m
    assert hasattr(m, "math")


def test_module_has_counter_import():
    import evaluation.metrics as m
    assert hasattr(m, "Counter")


def test_module_has_path_import():
    import evaluation.metrics as m
    assert hasattr(m, "Path")


def test_module_has_any_import():
    import evaluation.metrics as m
    assert hasattr(m, "Any")


def test_metrics_constants_are_tuples_not_lists():
    """作为常量约定，使用不可变 tuple。"""
    assert isinstance(_TEXT_TYPES, tuple)
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_compute_automatic_metrics_signature():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]
    # image_base_dir 默认值
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_return_annotation():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation)


def test_internal_function_signatures():
    """子函数都是 module-level 私有函数。"""
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]

    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]

    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]

    sig = inspect.signature(_image_resource_ratio)
    params = list(sig.parameters.keys())
    assert params == ["elements", "image_base_dir"]

    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]

    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]

    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]

    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]

    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]

    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]

    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]

    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]

    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_internal_functions_are_callable():
    """所有内部 helper 都可调用。"""
    assert callable(_pdf_locator_ratio)
    assert callable(_docx_locator_ratio)
    assert callable(_is_valid_bbox)
    assert callable(_image_resource_ratio)
    assert callable(_chunk_reference_ratio)
    assert callable(_text_preservation)
    assert callable(_heading_boundary_ratio)
    assert callable(_silent_drop_count)
    assert callable(_strip_unicode_whitespace)
    assert callable(_null)
    assert callable(_ratio)
    assert callable(_bool_metric)
    assert callable(_int_metric)
    assert callable(compute_automatic_metrics)


# =========================================================================
# idempotency / 不变性
# =========================================================================


def test_is_valid_bbox_idempotent():
    bbox = [0, 0, 100, 100]
    a = _is_valid_bbox(bbox)
    b = _is_valid_bbox(bbox)
    assert a == b


def test_strip_unicode_whitespace_idempotent():
    s = "a b c"
    a = _strip_unicode_whitespace(s)
    b = _strip_unicode_whitespace(s)
    assert a == b


def test_pdf_locator_ratio_idempotent():
    elements = [
        {"type": "paragraph", "element_id": "p1", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
    ]
    a = _pdf_locator_ratio(elements)
    b = _pdf_locator_ratio(elements)
    assert a == b


def test_docx_locator_ratio_idempotent():
    elements = [{"type": "paragraph", "element_id": "p1", "source_locator": {"section": "x"}}]
    a = _docx_locator_ratio(elements)
    b = _docx_locator_ratio(elements)
    assert a == b


def test_chunk_reference_ratio_idempotent():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    a = _chunk_reference_ratio(elements, chunks)
    b = _chunk_reference_ratio(elements, chunks)
    assert a == b


def test_compute_automatic_metrics_does_not_mutate_input():
    doc = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    import copy
    before = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == before


def test_image_resource_ratio_does_not_mutate_input(tmp_path: Path):
    elements = [{"type": "image", "element_id": "i1", "resource_path": "x.png"}]
    import copy
    before = copy.deepcopy(elements)
    _image_resource_ratio(elements, tmp_path)
    assert elements == before


# =========================================================================
# 综合行为
# =========================================================================


def test_full_pipeline_with_all_metric_types(tmp_path: Path):
    """完整文档包含：heading/paragraph/image、chunks、locator、expectations。"""
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    p = img_dir / "img.png"
    p.write_bytes(b"data")
    doc = {
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "doc-x",
        "elements": [
            {
                "element_id": "h1",
                "type": "heading",
                "content": "Title",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
            },
            {
                "element_id": "p1",
                "type": "paragraph",
                "content": "Body",
                "source_locator": {"page": 1, "bbox": [0, 60, 100, 200]},
            },
            {
                "element_id": "i1",
                "type": "image",
                "content": None,
                "resource_path": "img.png",
                "source_locator": {"page": 1},
            },
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Body", "source_element_ids": ["p1"]},
        ],
    }
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1, "image": 1}}
    result = compute_automatic_metrics(
        doc, None, "pdf", expectations, image_base_dir=img_dir
    )
    assert result["pipeline_success"]["value"] is True
    assert result["element_count_total"]["value"] == 3
    assert result["pdf_locator_valid_ratio"]["value"] == 1.0
    assert result["image_resource_exists_ratio"]["value"] == 1.0
    assert result["chunk_reference_intact_ratio"]["value"] == 1.0
    assert result["text_preservation_equal"]["value"] is True
    assert result["heading_boundary_compliance"]["value"] == 1.0
    assert result["silent_drop_count"]["value"] == 0


def test_pipeline_with_text_drop_detected():
    """chunk 漏掉一段文本 → recall<1，silent_drop_count 不变（不同语义）。"""
    doc = {
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "doc-x",
        "elements": [
            {"element_id": "p1", "type": "paragraph", "content": "ABC"},
            {"element_id": "p2", "type": "paragraph", "content": "XYZ"},
        ],
        "chunks": [
            {"text": "ABC", "source_element_ids": ["p1"]},  # 漏了 p2
        ],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["text_preservation_equal"]["value"] is False
    assert result["text_char_multiset_recall"]["value"] == 0.5


def test_pipeline_with_chunk_boundary_split():
    """单个 element 被拆到两个 chunk → precision/recall=1，equal=1（顺序字符相同）。"""
    doc = {
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "doc-x",
        "elements": [
            {"element_id": "p1", "type": "paragraph", "content": "ABCDEF"},
        ],
        "chunks": [
            {"text": "ABC", "source_element_ids": ["p1"]},
            {"text": "DEF", "source_element_ids": ["p1"]},
        ],
    }
    result = compute_automatic_metrics(doc, None, "pdf", None)
    assert result["text_preservation_equal"]["value"] is True
    assert result["text_char_multiset_precision"]["value"] == 1.0
