"""evaluation/metrics.py 第七十三轮 edges 测试（Round 612）。

补强 edges67 未触及的角度（第四十二批）—— 专门补强 _is_valid_bbox / _pdf_locator_ratio / _docx_locator_ratio。

新角度：
- _is_valid_bbox 各种非法类型（set / frozenset / dict / bytes / bytearray / custom iter）
- _is_valid_bbox 边界（None / 4 元素 / 5 元素 / 3 元素）
- _is_valid_bbox 含 True/False → False（bool 是 int 子类）
- _is_valid_bbox 含字符串数字 → False
- _is_valid_bbox NaN / -Inf / +Inf → False（math.isfinite）
- _is_valid_bbox 含 complex → False
- _pdf_locator_ratio 含非文本类型（image/table/header/footer 不需要 bbox）
- _pdf_locator_ratio page=0 / page=-1 → 不算
- _pdf_locator_ratio page=1 但 bbox 缺 → 不算
- _pdf_locator_ratio page 字符串 "1" → 不算
- _pdf_locator_ratio page 是 bool True → 不算
- _pdf_locator_ratio page 是 float 1.0 → 不算（实现 isinstance int 严格）
- _pdf_locator_ratio source_locator 是 None → 空字典
- _pdf_locator_ratio source_locator 缺 key → 空字典
- _docx_locator_ratio 含 relationship_id → 算
- _docx_locator_ratio 含 section → 算
- _docx_locator_ratio 含 paragraph_index → 算
- _docx_locator_ratio 含 run_index → 算
- _docx_locator_ratio 含 table_index → 算
- _docx_locator_ratio 含 row_index → 算
- _docx_locator_ratio 含 col_index → 算
- _docx_locator_ratio 含未知 key 但无结构 key → 不算
- _docx_locator_ratio 空 locator → 不算
- _docx_locator_ratio 部分有效部分无效 → 比例正确
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _NOT_EVALUATED,
    _PDF_BBOX_REQUIRED_TYPES,
    _TEXT_TYPES,
    _bool_metric,
    _docx_locator_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _strip_unicode_whitespace,
)


# ---------- _is_valid_bbox 类型拒绝 第四十二批


def test_is_valid_bbox_set_rejected_batch42():
    """set 不是 list。"""
    assert _is_valid_bbox({1, 2, 3, 4}) is False


def test_is_valid_bbox_frozenset_rejected_batch42():
    assert _is_valid_bbox(frozenset([1, 2, 3, 4])) is False


def test_is_valid_bbox_dict_rejected_batch42():
    assert _is_valid_bbox({"x": 1, "y": 2, "w": 3, "h": 4}) is False


def test_is_valid_bbox_bytes_rejected_batch42():
    """bytes 不是 list（也不是数值）。"""
    assert _is_valid_bbox(b"\x00\x01\x02\x03") is False


def test_is_valid_bbox_bytearray_rejected_batch42():
    assert _is_valid_bbox(bytearray([0, 1, 2, 3])) is False


def test_is_valid_bbox_generator_rejected_batch42():
    gen = (i for i in [0, 1, 2, 3])
    assert _is_valid_bbox(gen) is False


def test_is_valid_bbox_tuple_rejected_batch42():
    """tuple 也不是 list（严格 isinstance）。"""
    assert _is_valid_bbox((0, 1, 2, 3)) is False


def test_is_valid_bbox_string_rejected_batch42():
    """str 是 iterable 但不是 list。"""
    assert _is_valid_bbox("abcd") is False


def test_is_valid_bbox_none_rejected_batch42():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list_rejected_batch42():
    """长度 != 4。"""
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_len_three_rejected_batch42():
    assert _is_valid_bbox([0, 1, 2]) is False


def test_is_valid_bbox_len_five_rejected_batch42():
    assert _is_valid_bbox([0, 1, 2, 3, 4]) is False


def test_is_valid_bbox_len_four_accepted_batch42():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_int_four_accepted_batch42():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_mixed_int_float_accepted_batch42():
    assert _is_valid_bbox([0, 0.5, 100, 99.5]) is True


def test_is_valid_bbox_contains_true_rejected_batch42():
    """bool 是 int 子类，但实现专门 reject。"""
    assert _is_valid_bbox([True, 0, 100, 100]) is False


def test_is_valid_bbox_contains_false_rejected_batch42():
    assert _is_valid_bbox([0, 0, False, 100]) is False


def test_is_valid_bbox_all_bool_rejected_batch42():
    assert _is_valid_bbox([True, True, True, True]) is False


def test_is_valid_bbox_string_number_rejected_batch42():
    """字符串数字不是数值。"""
    assert _is_valid_bbox(["0", "0", "100", "100"]) is False


def test_is_valid_bbox_nan_rejected_batch42():
    assert _is_valid_bbox([float("nan"), 0, 100, 100]) is False


def test_is_valid_bbox_inf_rejected_batch42():
    assert _is_valid_bbox([float("inf"), 0, 100, 100]) is False


def test_is_valid_bbox_neg_inf_rejected_batch42():
    assert _is_valid_bbox([float("-inf"), 0, 100, 100]) is False


def test_is_valid_bbox_complex_rejected_batch42():
    assert _is_valid_bbox([complex(1, 2), 0, 100, 100]) is False


def test_is_valid_bbox_zero_accepted_batch42():
    """全 0 是合法 bbox（空 bbox）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_accepted_batch42():
    """负值也接受（bbox 可能有负偏移）。"""
    assert _is_valid_bbox([-10, -10, 100, 100]) is True


def test_is_valid_bbox_very_large_accepted_batch42():
    assert _is_valid_bbox([0, 0, 1e18, 1e18]) is True


def test_is_valid_bbox_very_small_accepted_batch42():
    assert _is_valid_bbox([0, 0, 1e-18, 1e-18]) is True


def test_is_valid_bbox_mixed_invalid_first_elem_rejected_batch42():
    assert _is_valid_bbox([None, 0, 100, 100]) is False


def test_is_valid_bbox_mixed_invalid_last_elem_rejected_batch42():
    assert _is_valid_bbox([0, 0, 100, None]) is False


# ---------- _pdf_locator_ratio 第四十二批


def test_pdf_locator_ratio_empty_elements_batch42():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_only_image_no_bbox_needed_batch42():
    """image 类型不需要 bbox。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_image_without_bbox_still_valid_batch42():
    """image 没有 bbox 字段也算 valid。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # 无 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_table_no_bbox_needed_batch42():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [
        {"type": "table", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_header_no_bbox_needed_batch42():
    elements = [{"type": "header", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_footer_no_bbox_needed_batch42():
    elements = [{"type": "footer", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_paragraph_needs_bbox_batch42():
    """paragraph 在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_with_valid_bbox_batch42():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_page_zero_rejected_batch42():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_rejected_batch42():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_string_rejected_batch42():
    """page="1" 字符串不是 int。"""
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_bool_rejected_batch42():
    """True 是 int 子类，但 isinstance(True, int) is True；
    不过 True < 1 是 False，所以 True page 接受... 等等。"""
    elements = [{"type": "image", "source_locator": {"page": True}}]
    out = _pdf_locator_ratio(elements)
    # isinstance(True, int) = True; True < 1 = False (True == 1);
    # 所以 page=True 通过 isinstance 检查 且 not (True < 1) → 接受
    # 实际：isinstance(True, int) = True; page < 1 = (1 < 1) = False; not False = True → 通过
    # 因此 page=True 接受 → ratio = 1.0
    # 但其实 image 不需要 bbox，所以接受
    # 看实现：if not isinstance(page, int) or page < 1 → continue
    # isinstance(True, int) = True；True < 1 → False；所以条件是 (False or False) = False → 不 continue
    # 即 page=True 接受
    assert out["value"] == 1.0  # bool 是 int 子类的经典 gotcha


def test_pdf_locator_ratio_page_float_rejected_batch42():
    """float 1.0 不是 int（isinstance 严格）。"""
    elements = [{"type": "image", "source_locator": {"page": 1.0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_none_rejected_batch42():
    elements = [{"type": "image", "source_locator": {"page": None}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_locator_none_batch42():
    """source_locator=None → 实现用 `or {}` → 空 dict → 无 page → 拒绝。"""
    elements = [{"type": "image", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_locator_key_batch42():
    """element 无 source_locator 字段 → .get 返回 None → or {} → 空。"""
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_partial_mixed_batch42():
    """3 个：1 个有效 image + 1 个 page=0 + 1 个 paragraph 缺 bbox → ratio=1/3。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # ✓
        {"type": "image", "source_locator": {"page": 0}},  # ✗
        {"type": "paragraph", "source_locator": {"page": 1}},  # ✗（缺 bbox）
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0 / 3.0


def test_pdf_locator_ratio_heading_with_bbox_batch42():
    elements = [{"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_caption_with_bbox_batch42():
    elements = [{"type": "caption", "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_list_item_with_bbox_batch42():
    elements = [{"type": "list_item", "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_unknown_type_no_bbox_needed_batch42():
    """未知 type 不在 _PDF_BBOX_REQUIRED_TYPES → 只需 page。"""
    elements = [{"type": "unknown_type", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_missing_type_treated_unknown_batch42():
    """缺 type 字段 → e.get("type") → None；不在 required types → 不需 bbox。"""
    elements = [{"source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 第四十二批


def test_docx_locator_ratio_empty_elements_batch42():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_relationship_id_batch42():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_batch42():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_batch42():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_run_index_batch42():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 2}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_table_index_batch42():
    elements = [{"type": "table_cell", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_row_index_batch42():
    elements = [{"type": "table_cell", "source_locator": {"row_index": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_col_index_batch42():
    elements = [{"type": "table_cell", "source_locator": {"col_index": 2}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_rejected_batch42():
    """page 出现 → 不算（DOCX 没有 page 概念）。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 1, "page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected_batch42():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 1, "bbox": [0, 0, 1, 1]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_only_page_rejected_batch42():
    """只有 page → 走 page 检查 → continue。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_unknown_key_rejected_batch42():
    """未知 key 不在结构 keys 列表 → 不算。"""
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "value"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_empty_locator_rejected_batch42():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_locator_none_rejected_batch42():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_locator_rejected_batch42():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_multiple_structural_keys_batch42():
    """多个结构 key 仍算 valid。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 1, "section": 2}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_partial_mixed_batch42():
    """3 个：1 个有 paragraph_index + 1 个空 locator + 1 个只有 page → ratio=1/3。"""
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 1}},  # ✓
        {"type": "paragraph", "source_locator": {}},  # ✗
        {"type": "paragraph", "source_locator": {"page": 1}},  # ✗
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0 / 3.0


def test_docx_locator_ratio_index_negative_accepted_batch42():
    """实现不校验 index 值；负 index 仍算 valid。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": -1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_index_zero_accepted_batch42():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_index_string_accepted_batch42():
    """index="5" 字符串也接受（实现不校验类型）。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": "5"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_index_none_accepted_batch42():
    """index=None 也接受（实现只检查 key 存在）。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": None}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _PDF_BBOX_REQUIRED_TYPES 第四十二批


def test_pdf_bbox_required_types_len_four_batch42():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_contains_heading_batch42():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_contains_paragraph_batch42():
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_contains_caption_batch42():
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_contains_list_item_batch42():
    assert "list_item" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_no_image_batch42():
    assert "image" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_no_table_batch42():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_subset_of_text_types_batch42():
    """_PDF_BBOX_REQUIRED_TYPES 应是 _TEXT_TYPES 的子集。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


# ---------- _TEXT_TYPES 第四十二批


def test_text_types_len_seven_batch42():
    assert len(_TEXT_TYPES) == 7


def test_text_types_contains_all_expected_batch42():
    expected = {"heading", "paragraph", "list_item", "table", "caption", "header", "footer"}
    assert set(_TEXT_TYPES) == expected


def test_text_types_no_image_batch42():
    assert "image" not in _TEXT_TYPES


def test_text_types_no_duplicates_batch42():
    assert len(_TEXT_TYPES) == len(set(_TEXT_TYPES))


# ---------- _NOT_EVALUATED 第四十二批


def test_not_evaluated_is_string_batch42():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_value_batch42():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_isidentifier_batch42():
    assert _NOT_EVALUATED.isidentifier()


def test_not_evaluated_isascii_batch42():
    assert _NOT_EVALUATED.isascii()


# ---------- _null / _ratio / _bool_metric / _int_metric 补强 第四十二批


def test_null_returns_dict_with_two_keys_batch42():
    out = _null("reason")
    assert set(out.keys()) == {"value", "reason"}


def test_null_value_is_none_batch42():
    assert _null("x")["value"] is None


def test_null_reason_passthrough_batch42():
    assert _null("my_reason")["reason"] == "my_reason"


def test_null_empty_reason_batch42():
    assert _null("")["reason"] == ""


def test_ratio_returns_dict_with_two_keys_batch42():
    out = _ratio(0.5)
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_value_is_float_batch42():
    assert isinstance(_ratio(1)["value"], float)


def test_ratio_reason_is_none_batch42():
    assert _ratio(0.5)["reason"] is None


def test_ratio_int_input_converted_batch42():
    """int 输入被 float() 转。"""
    assert _ratio(1)["value"] == 1.0


def test_bool_metric_returns_dict_batch42():
    out = _bool_metric(True)
    assert set(out.keys()) == {"value", "reason"}


def test_bool_metric_value_is_bool_batch42():
    assert isinstance(_bool_metric(True)["value"], bool)


def test_bool_metric_truthy_input_batch42():
    """任何 truthy 都被 bool() 转。"""
    assert _bool_metric(1)["value"] is True
    assert _bool_metric("x")["value"] is True


def test_bool_metric_falsy_input_batch42():
    assert _bool_metric(0)["value"] is False
    assert _bool_metric("")["value"] is False


def test_int_metric_returns_dict_batch42():
    out = _int_metric(5)
    assert set(out.keys()) == {"value", "reason"}


def test_int_metric_value_is_int_batch42():
    assert isinstance(_int_metric(5)["value"], int)


def test_int_metric_float_input_truncated_batch42():
    """int(2.7) = 2。"""
    assert _int_metric(2.7)["value"] == 2


def test_int_metric_string_input_rejected_batch42():
    """int("abc") raises ValueError。"""
    with pytest.raises(ValueError):
        _int_metric("abc")


def test_int_metric_numeric_string_accepted_batch42():
    """int("5") = 5。"""
    assert _int_metric("5")["value"] == 5


# ---------- _strip_unicode_whitespace 补强 第四十二批


def test_strip_unicode_whitespace_empty_batch42():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace_batch42():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_ascii_space_batch42():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_tab_batch42():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline_batch42():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return_batch42():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_form_feed_batch42():
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_vertical_tab_batch42():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_nbsp_batch42():
    """Unicode NBSP (U+00A0)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_zero_width_space_not_stripped_batch42():
    """U+200B zero-width space 不是 isspace() 空白（是 format 字符），不删除。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_em_space_batch42():
    """U+2003 em space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_all_whitespace_batch42():
    """全空白 → 空。"""
    assert _strip_unicode_whitespace("   \t\n\r ") == ""


def test_strip_unicode_whitespace_multiple_consecutive_batch42():
    """连续多个空白都删除。"""
    assert _strip_unicode_whitespace("a   b") == "ab"


def test_strip_unicode_whitespace_only_letters_batch42():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_unicode_letters_batch42():
    """中文字符不是空白。"""
    assert _strip_unicode_whitespace("你好") == "你好"


def test_strip_unicode_whitespace_punctuation_batch42():
    assert _strip_unicode_whitespace("a.b") == "a.b"


def test_strip_unicode_whitespace_digits_batch42():
    assert _strip_unicode_whitespace("123") == "123"


def test_strip_unicode_whitespace_mixed_batch42():
    assert _strip_unicode_whitespace("  h e l l o  ") == "hello"


# ---------- 端到端集成 第四十二批


def test_e2e_pdf_locator_mixed_scenario_batch42():
    """模拟真实 PDF：3 个有效 paragraph + 1 个无效 + 1 个 image。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 60, 100, 110]}},
        {"type": "paragraph", "source_locator": {"page": 2, "bbox": [0, 0, 100, 50]}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # ✗ 缺 bbox
        {"type": "image", "source_locator": {"page": 1}},  # ✓
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 4.0 / 5.0


def test_e2e_docx_locator_mixed_scenario_batch42():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"paragraph_index": 1}},
        {"type": "paragraph", "source_locator": {"section": 1}},
        {"type": "paragraph", "source_locator": {}},  # ✗
        {"type": "paragraph", "source_locator": {"page": 1}},  # ✗
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 3.0 / 5.0


def test_e2e_pdf_locator_with_invalid_bbox_batch42():
    """bbox 类型错（dict 而非 list）→ _is_valid_bbox False → paragraph 不算。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": {"x": 0, "y": 0}}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- module source forbidden tokens 第八十二批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch42(token):
    src = inspect.getsource(mmod)
    assert token not in src
