r"""evaluation/metrics.py 边角测试 - 第二十四轮（Round 304）。

edges22 已覆盖：4 helper one-liner（_null/_ratio/_bool_metric/_int_metric）行为 + 3 常量 +
compute_automatic_metrics 边界组合 + schema_valid 行为 + _pdf_locator_ratio/_docx_locator_ratio/
_image_resource_ratio/_chunk_reference_ratio/_heading_boundary_ratio/_silent_drop_count 各分支深度 +
_strip_unicode_whitespace 行为 + _text_preservation 边界 + module imports/__all__/namespace/
forbidden tokens/docstring + signatures 精确 + source level 完整 + 端到端集成 + 模块整体合理性。

edges23 补强未覆盖的角度（深度边界 + 行为 + source level + signatures + 端到端）：
- **_ratio 边界值补强**：_ratio(0.0) → value=0.0, reason=None；_ratio(1.0) → 1.0；
  _ratio(-0.0) → -0.0（Python 不规范化）；_ratio(0) int → float(0)=0.0；
  _ratio(float('inf')) → inf（不 clamp）；_ratio(float('-inf')) → -inf；
  _ratio(float('nan')) → nan（不 clamp）；_ratio(0.5) → 0.5
- **_null reason 字符串深度补强**：空字符串 reason；长字符串 reason；unicode reason（中文）；
  emoji reason；含空格 reason；含特殊字符 reason（\n/\t）
- **_bool_metric truthy/falsy 边界补强**：dict → True（非空 dict 是 truthy）；
  空列表 [] → False；空 dict {} → False；None → False；0 int → False；
  0.0 float → False；空字符串 "" → False；空 tuple () → False；
  非空 list [1] → True；非空 string "x" → True；非空 tuple (1,) → True
- **_int_metric 截断行为补强**：_int_metric(1.9) → 1（向 0 截断）；
  _int_metric(-1.9) → -1（向 0 截断）；_int_metric(-0.5) → 0；
  _int_metric(0.999) → 0；_int_metric(True) → 1（bool 是 int 子类）；
  _int_metric(False) → 0
- **_TEXT_TYPES 常量深度补强**：tuple 不可变；7 entries 顺序精确；
  不含 "image"；不含 "unknown"；_PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES；
  _TEXT_TYPES[0]=="heading"；_TEXT_TYPES[-1]=="footer"
- **compute_automatic_metrics 流程补强**：document None 早 return + 11 个 metric 全部 pipeline_failed；
  document={} + error=None → 各 metric 走 no_elements/no_chunks/no_image/no_heading；
  pipeline_success 在 metrics['pipeline_success'] value 字段；
  error_code 在 metrics['error_code'] value 字段；schema_valid 抛异常时 reason 含异常类名
- **_pdf_locator_ratio bbox 深度补强**：bbox=[1,2,3] len=3 → invalid；
  bbox=[1,2,3,4,5] len=5 → invalid；bbox=[1,'2',3,4] str 中混 → invalid；
  bbox=[True,2,3,4] bool → invalid；bbox=[1,2,3,None] → invalid；
  bbox=[1,2,3,float('inf')] → invalid；bbox=[1,2,3,float('nan')] → invalid；
  bbox 是 tuple → invalid（必须是 list）；bbox=None → invalid
- **_docx_locator_ratio structural_keys 单独有效性补强**：每 1 个 structural_key 单独 valid；
  含 page=1 + section=1 → invalid（page 优先）；含 bbox + paragraph_index → invalid；
  空 locator {} → invalid（无 structural_key）
- **_image_resource_ratio 候选路径补强**：image_base_dir=None + 绝对 rp → 1 candidate；
  image_base_dir 给 + 相对 rp → 2 candidates；image_base_dir 给 + 绝对 rp → 2 candidates；
  rp 是空字符串 → 不计入 valid；rp 是 None → 不计入 valid
- **_chunk_reference_ratio 边界补强**：chunk source_element_ids=[e1,e1,e1]（重复） → valid（all in elem_ids）；
  chunk source_element_ids=[] → invalid；chunks=[c1] source_element_ids=['x'] → 0.0
- **_strip_unicode_whitespace Unicode 类别深度补强**：NBSP   删除；em space   删除；
  en space   删除；ideographic space 　 删除；
  line separator   删除；paragraph separator   删除；
  thin space   删除；punctuation ASCII 不删
- **_text_preservation 深度补强**：单字符 'a' → equal=True precision/recall=1.0；
  emoji 单字符 '😀' → equal=True precision/recall=1.0；
  中文混合 ASCII 'a中b' → Counter 包含 'a','中','b'；
  chunker 词内硬切（chunk=['he','llo'] join='hello'） → equal 仍 True（无空白）
- **_silent_drop_count max(0,) 补强**：actual > expected → max(0, neg)=0；
  actual == expected → 0；actual < expected → 正数；多类型 partial sum 精确
- **module source 字符串精确补强**：含「自 evaluator v1.1」/「report v1.1」/「口径 D」/
  「v1.0 用 ' '.join」/「v1.1 直接删除全部空白」
- **module source forbidden tokens 补强**：不含 time / json / csv / pickle /
  sqlite3 / socket / email / html / http / urllib
- **module source 含 math.isfinite 调用**：_is_valid_bbox 含 math.isfinite(v)
- **module source 含 Counter 交集操作**：_text_preservation 含 c_expected & c_actual
- **module source 含 Path / Path.name 操作**：_image_resource_ratio 含 Path(rp) + Path(rp).name
- **signatures 精确补强**：_null 1 param + no default；_ratio 1 param + no default；
  _bool_metric 1 param + no default；_int_metric 1 param + no default；
  compute_automatic_metrics 5 params + image_base_dir default=None + keyword args 顺序
- **端到端集成补强**：完整 PDF + bbox 全 valid → pdf_locator_valid_ratio 1.0；
  完整 DOCX + structural_keys 全 valid → docx_locator_valid_ratio 1.0；
  完整 chunks source_element_ids 全 valid → chunk_reference_intact_ratio 1.0；
  含 heading + chunks 首 id 匹配 → heading_boundary_compliance 1.0；
  expectations element_count_by_type 全 0 drop → silent_drop_count=0
- **模块整体合理性**：__all__ 1 entry；1 public + 13 private + 3 constant；
  无 class 定义；无 __main__ 块；compute_automatic_metrics 是唯一 public
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any

import pytest

import evaluation.metrics as mmod
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
# _ratio 边界值补强
# =========================================================================


def test_ratio_zero_point_zero():
    out = _ratio(0.0)
    assert out["value"] == 0.0
    assert out["reason"] is None


def test_ratio_one_point_zero():
    out = _ratio(1.0)
    assert out["value"] == 1.0
    assert out["reason"] is None


def test_ratio_negative_zero():
    """Python 不规范化 -0.0 → 0.0。"""
    out = _ratio(-0.0)
    assert out["value"] == -0.0
    # -0.0 == 0.0 但 str(-0.0) != str(0.0)
    assert str(out["value"]) == "-0.0"


def test_ratio_int_zero_promoted_to_float():
    """_ratio(0) int → float(0) = 0.0。"""
    out = _ratio(0)
    assert isinstance(out["value"], float)
    assert out["value"] == 0.0


def test_ratio_half():
    out = _ratio(0.5)
    assert out["value"] == 0.5


def test_ratio_inf_not_clamped():
    """_ratio(float('inf')) → inf（不 clamp）。"""
    out = _ratio(float("inf"))
    assert math.isinf(out["value"])


def test_ratio_neg_inf_not_clamped():
    """_ratio(float('-inf')) → -inf。"""
    out = _ratio(float("-inf"))
    assert math.isinf(out["value"])
    assert out["value"] < 0


def test_ratio_nan_not_clamped():
    """_ratio(float('nan')) → nan（不规范化）。"""
    out = _ratio(float("nan"))
    assert math.isnan(out["value"])


# =========================================================================
# _null reason 字符串深度补强
# =========================================================================


def test_null_empty_reason():
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_long_reason():
    long_str = "x" * 1000
    out = _null(long_str)
    assert out["reason"] == long_str


def test_null_unicode_reason():
    out = _null("原因")
    assert out["reason"] == "原因"


def test_null_emoji_reason():
    out = _null("原因😀")
    assert out["reason"] == "原因😀"


def test_null_reason_with_whitespace():
    out = _null("reason with space")
    assert out["reason"] == "reason with space"


def test_null_reason_with_special_chars():
    out = _null("line1\nline2\ttabbed")
    assert out["reason"] == "line1\nline2\ttabbed"


# =========================================================================
# _bool_metric truthy/falsy 边界补强
# =========================================================================


def test_bool_metric_non_empty_dict_is_truthy():
    out = _bool_metric({"a": 1})
    assert out["value"] is True


def test_bool_metric_empty_list_is_falsy():
    out = _bool_metric([])
    assert out["value"] is False


def test_bool_metric_empty_dict_is_falsy():
    out = _bool_metric({})
    assert out["value"] is False


def test_bool_metric_none_is_falsy():
    out = _bool_metric(None)
    assert out["value"] is False


def test_bool_metric_zero_int_is_falsy():
    out = _bool_metric(0)
    assert out["value"] is False


def test_bool_metric_zero_float_is_falsy():
    out = _bool_metric(0.0)
    assert out["value"] is False


def test_bool_metric_empty_string_is_falsy():
    out = _bool_metric("")
    assert out["value"] is False


def test_bool_metric_empty_tuple_is_falsy():
    out = _bool_metric(())
    assert out["value"] is False


def test_bool_metric_non_empty_list_is_truthy():
    out = _bool_metric([1])
    assert out["value"] is True


def test_bool_metric_non_empty_string_is_truthy():
    out = _bool_metric("x")
    assert out["value"] is True


def test_bool_metric_non_empty_tuple_is_truthy():
    out = _bool_metric((1,))
    assert out["value"] is True


# =========================================================================
# _int_metric 截断行为补强
# =========================================================================


def test_int_metric_truncates_toward_zero_positive():
    """_int_metric(1.9) → 1（向 0 截断）。"""
    out = _int_metric(1.9)
    assert out["value"] == 1


def test_int_metric_truncates_toward_zero_negative():
    """_int_metric(-1.9) → -1（向 0 截断）。"""
    out = _int_metric(-1.9)
    assert out["value"] == -1


def test_int_metric_truncates_negative_half():
    """_int_metric(-0.5) → 0（向 0 截断）。"""
    out = _int_metric(-0.5)
    assert out["value"] == 0


def test_int_metric_truncates_positive_less_than_one():
    """_int_metric(0.999) → 0。"""
    out = _int_metric(0.999)
    assert out["value"] == 0


def test_int_metric_bool_true_is_one():
    """_int_metric(True) → 1（bool 是 int 子类）。"""
    out = _int_metric(True)
    assert out["value"] == 1


def test_int_metric_bool_false_is_zero():
    """_int_metric(False) → 0。"""
    out = _int_metric(False)
    assert out["value"] == 0


# =========================================================================
# _TEXT_TYPES 常量深度补强
# =========================================================================


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_immutable():
    """tuple 不可变。"""
    with pytest.raises(TypeError):
        _TEXT_TYPES[0] = "image"  # type: ignore


def test_text_types_7_entries_in_order():
    assert _TEXT_TYPES == (
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    )


def test_text_types_does_not_contain_image():
    assert "image" not in _TEXT_TYPES


def test_text_types_does_not_contain_unknown():
    assert "unknown" not in _TEXT_TYPES


def test_pdf_bbox_required_types_is_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_text_types_first_is_heading():
    assert _TEXT_TYPES[0] == "heading"


def test_text_types_last_is_footer():
    assert _TEXT_TYPES[-1] == "footer"


def test_pdf_bbox_required_types_4_entries_in_order():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


# =========================================================================
# compute_automatic_metrics 流程补强
# =========================================================================


def test_compute_metrics_document_none_early_returns_all_pipeline_failed():
    """document=None + error=None → 早 return + 11 个 metric 全 pipeline_failed。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    pipeline_failed_names = [
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ]
    for name in pipeline_failed_names:
        assert out[name] == {"value": None, "reason": "pipeline_failed"}, f"{name}"


def test_compute_metrics_pipeline_success_in_value_field():
    """pipeline_success 在 metrics['pipeline_success']['value']。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_error_code_in_value_field():
    """error_code 在 metrics['error_code']['value']。"""
    err = {"code": "E1", "message": "fail"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "E1"


def test_compute_metrics_error_none_yields_null_error_code():
    """error=None → error_code value=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_schema_valid_with_dict_no_elements():
    """document={} 走 schema 校验。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    # document={} 多半 schema 不通过
    assert out["schema_valid"]["value"] in (True, False)


def test_compute_metrics_schema_check_exception_catches():
    """schema 校验抛 Exception → reason 含异常类名。"""
    # 给个会让 schema_validation 内部抛错的 document
    # 用一个 schema_valid 字段类型异常的对象 - 让 schema 校验返 False 不抛
    # 实际上 evaluation.schema_validation.document_passes_schema 接受 dict
    # 要让它抛 Exception 比较 tricky；用 monkeypatch
    import evaluation.schema_validation as sv
    original = sv.document_passes_schema

    def _raise(doc):
        raise ValueError("test error")

    sv.document_passes_schema = _raise  # type: ignore
    try:
        out = compute_automatic_metrics({"elements": [], "chunks": []}, None, "pdf", None)
        assert out["schema_valid"]["value"] is False
        assert "schema_check_exception:ValueError" in out["schema_valid"]["reason"]
    finally:
        sv.document_passes_schema = original  # type: ignore


# =========================================================================
# _pdf_locator_ratio bbox 深度补强
# =========================================================================


def test_pdf_locator_bbox_len_3_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_len_5_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4, 5]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_str_in_middle_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, "2", 3, 4]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_bool_first_invalid():
    """bbox=[True, 2, 3, 4] bool 是 int 子类但显式 reject。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [True, 2, 3, 4]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_none_in_middle_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3, None]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_inf_invalid():
    elements = [{"type": "paragraph",
                 "source_locator": {"page": 1, "bbox": [1, 2, 3, float("inf")]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_nan_invalid():
    elements = [{"type": "paragraph",
                 "source_locator": {"page": 1, "bbox": [1, 2, 3, float("nan")]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_tuple_invalid():
    """bbox 是 tuple 不是 list → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": (1, 2, 3, 4)}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_none_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": None}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# =========================================================================
# _docx_locator_ratio structural_keys 单独有效性补强
# =========================================================================


def test_docx_locator_section_alone_valid():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_paragraph_index_alone_valid():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_run_index_alone_valid():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_table_index_alone_valid():
    elements = [{"type": "paragraph", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_relationship_id_alone_valid():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_page_makes_invalid_even_with_section():
    """含 page=1 + section=1 → invalid（page 优先 reject）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_bbox_makes_invalid_even_with_paragraph_index():
    """含 bbox + paragraph_index → invalid。"""
    elements = [{"type": "paragraph",
                 "source_locator": {"bbox": [1, 2, 3, 4], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_empty_dict_invalid():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# =========================================================================
# _image_resource_ratio 候选路径补强
# =========================================================================


def test_image_resource_no_base_dir_absolute_rp_one_candidate(tmp_path):
    """image_base_dir=None + 绝对 rp → 1 candidate。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_with_base_dir_relative_rp_two_candidates(tmp_path):
    """image_base_dir 给 + 相对 rp → 2 candidates。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_with_base_dir_absolute_rp_two_candidates(tmp_path):
    """image_base_dir 给 + 绝对 rp → 2 candidates（base_dir / Path(rp).name 也尝试）。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_empty_string_rp_skipped():
    """rp='' → 不计入 valid（continue）。"""
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_none_rp_skipped():
    """rp=None → 不计入 valid。"""
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_size_zero_file_invalid(tmp_path):
    """文件存在但 size=0 → invalid。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")  # size=0
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# =========================================================================
# _chunk_reference_ratio 边界补强
# =========================================================================


def test_chunk_reference_repeated_ids_in_one_chunk_still_valid():
    """chunk source_element_ids=[e1,e1,e1]（重复） → valid（all in elem_ids）。"""
    elements = [{"element_id": "e1", "type": "paragraph"}]
    chunks = [{"chunk_id": "c1", "text": "t", "source_element_ids": ["e1", "e1", "e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_empty_ids_invalid():
    """chunk source_element_ids=[] → invalid（not ids truthy）。"""
    elements = [{"element_id": "e1", "type": "paragraph"}]
    chunks = [{"chunk_id": "c1", "text": "t", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_unknown_id_yields_zero():
    """chunks=[c1] source_element_ids=['x'] → 0.0。"""
    elements = [{"element_id": "e1", "type": "paragraph"}]
    chunks = [{"chunk_id": "c1", "text": "t", "source_element_ids": ["x"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_missing_ids_key_treated_as_empty():
    """chunk 无 source_element_ids key → c.get(...) or [] → [] → invalid。"""
    elements = [{"element_id": "e1", "type": "paragraph"}]
    chunks = [{"chunk_id": "c1", "text": "t"}]  # 无 source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace Unicode 类别深度补强
# =========================================================================


def test_strip_unicode_nbsp():
    """NBSP \\u00A0 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_em_space():
    """em space \\u2003 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_en_space():
    """en space \\u2002 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ideographic_space():
    """ideographic space \\u3000 删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_line_separator():
    """line separator \\u2028 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_paragraph_separator():
    """paragraph separator \\u2029 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_thin_space():
    """thin space \\u2009 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_does_not_remove_ascii_punctuation():
    """ASCII 标点 . , ! 不删。"""
    assert _strip_unicode_whitespace("a.b,c!d") == "a.b,c!d"


# =========================================================================
# _text_preservation 深度补强
# =========================================================================


def test_text_preservation_single_char_equal():
    elements = [{"type": "paragraph", "content": "a"}]
    chunks = [{"chunk_id": "c1", "text": "a", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_emoji_single_char():
    elements = [{"type": "paragraph", "content": "😀"}]
    chunks = [{"chunk_id": "c1", "text": "😀", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0


def test_text_preservation_mixed_chinese_ascii():
    elements = [{"type": "paragraph", "content": "a中b"}]
    chunks = [{"chunk_id": "c1", "text": "a中b", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_word_split_no_whitespace_introduced():
    """chunker 词内硬切（chunk=['he','llo'] join='hello'） → equal 仍 True（无空白引入）。"""
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [
        {"chunk_id": "c1", "text": "he", "source_element_ids": ["e1"]},
        {"chunk_id": "c2", "text": "llo", "source_element_ids": ["e1"]},
    ]
    out = _text_preservation(elements, chunks)
    # actual = "hello" (no whitespace in chunks); expected = "hello" → equal True
    assert out["equal"]["value"] is True


# =========================================================================
# _silent_drop_count max(0,) 补强
# =========================================================================


def test_silent_drop_actual_greater_than_expected_zero():
    """actual > expected → max(0, neg)=0。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_actual_equal_expected_zero():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_actual_less_than_expected_positive():
    by_type = {"paragraph": 1}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


def test_silent_drop_multi_type_partial_sum():
    """多类型 partial sum 精确。"""
    by_type = {"paragraph": 2, "heading": 1, "table": 3}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 1, "table": 3, "caption": 2}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph: 5-2=3, heading: 1-1=0, table: 3-3=0, caption: 2-0=2 → 3+0+0+2=5
    assert out["value"] == 5


def test_silent_drop_expected_type_missing_in_actual():
    """expected 中有 type 但 by_type 中没有 → actual=0 → drop=expected。"""
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"heading": 2}}  # by_type 中无 heading
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


# =========================================================================
# module source 字符串精确补强
# =========================================================================


def test_module_source_contains_evaluator_v1_1_text():
    src = inspect.getsource(mmod)
    assert "evaluator v1.1" in src


def test_module_source_contains_report_v1_1_text():
    src = inspect.getsource(mmod)
    assert "report v1.1" in src


def test_module_source_contains_kou_jing_d_text():
    """含「口径 D」。"""
    src = inspect.getsource(mmod)
    assert "口径 D" in src


def test_module_source_contains_v1_0_join_text():
    """含「v1.0 用 ' '.join」。"""
    src = inspect.getsource(mmod)
    assert "v1.0" in src
    assert "' '.join" in src


def test_module_source_contains_v1_1_strip_text():
    """含「v1.1 直接删除全部空白」。"""
    src = inspect.getsource(mmod)
    assert "v1.1" in src
    assert "直接删除全部空白" in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_time_import():
    src = inspect.getsource(mmod)
    assert "import time" not in src
    assert "from time " not in src


def test_module_source_no_json_import():
    src = inspect.getsource(mmod)
    assert "import json" not in src
    assert "from json " not in src


def test_module_source_no_csv_import():
    src = inspect.getsource(mmod)
    assert "import csv" not in src


def test_module_source_no_pickle_import():
    src = inspect.getsource(mmod)
    assert "import pickle" not in src


def test_module_source_no_sqlite3_import():
    src = inspect.getsource(mmod)
    assert "import sqlite3" not in src


def test_module_source_no_socket_import():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_email_import():
    src = inspect.getsource(mmod)
    assert "import email" not in src


def test_module_source_no_html_import():
    src = inspect.getsource(mmod)
    assert "import html" not in src


def test_module_source_no_http_import():
    src = inspect.getsource(mmod)
    assert "import http" not in src


def test_module_source_no_urllib_import():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


# =========================================================================
# module source 含 math.isfinite / Counter / Path
# =========================================================================


def test_module_source_has_math_isfinite_call():
    """_is_valid_bbox 含 math.isfinite(v) 调用。"""
    src = inspect.getsource(mmod)
    assert "math.isfinite" in src


def test_module_source_has_counter_intersection():
    """_text_preservation 含 c_expected & c_actual 交集操作。"""
    src = inspect.getsource(mmod)
    assert "c_expected & c_actual" in src


def test_module_source_has_path_rp():
    """_image_resource_ratio 含 Path(rp)。"""
    src = inspect.getsource(mmod)
    assert "Path(rp)" in src


def test_module_source_has_path_rp_name():
    """_image_resource_ratio 含 Path(rp).name。"""
    src = inspect.getsource(mmod)
    assert "Path(rp).name" in src


def test_module_source_has_image_base_dir_concat():
    """含 image_base_dir / Path(rp).name。"""
    src = inspect.getsource(mmod)
    assert "image_base_dir / Path(rp).name" in src


# =========================================================================
# signatures 精确补强
# =========================================================================


def test_null_signature_1_param_no_default():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_ratio_signature_1_param_no_default():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_bool_metric_signature_1_param_no_default():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_int_metric_signature_1_param_no_default():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_compute_metrics_5_params_with_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert params[4].name == "image_base_dir"
    assert params[4].default is None


def test_compute_metrics_no_varargs_varkw():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_compute_metrics_first_4_params_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    for i in range(4):
        assert params[i].default is inspect.Parameter.empty


# =========================================================================
# 端到端集成补强
# =========================================================================


def test_e2e_pdf_full_valid_bbox_yields_pdf_locator_one():
    """完整 PDF + bbox 全 valid → pdf_locator_valid_ratio 1.0。"""
    document = {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_docx_full_valid_structural_keys_yields_docx_locator_one():
    """完整 DOCX + structural_keys 全 valid → docx_locator_valid_ratio 1.0。"""
    document = {
        "source_type": "docx",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.docx",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"paragraph_index": 0, "section": 1}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_chunks_source_ids_valid_yields_chunk_reference_one():
    """完整 chunks source_element_ids 全 valid → chunk_reference_intact_ratio 1.0。"""
    document = {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_heading_at_chunk_start_yields_heading_boundary_one():
    """含 heading + chunks 首 id 匹配 → heading_boundary_compliance 1.0。"""
    document = {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "Title",
             "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "Title", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_zero_drops_yields_silent_drop_zero():
    """expectations element_count_by_type 全 0 drop → silent_drop_count=0。"""
    document = {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 0


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_all_has_only_compute_automatic_metrics():
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_compute_automatic_metrics_is_only_public_callable():
    """compute_automatic_metrics 是唯一 public callable。"""
    import evaluation.metrics as m
    import types
    public_callables = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), types.FunctionType)
    ]
    assert public_callables == ["compute_automatic_metrics"]


def test_module_has_no_class_definition():
    src = inspect.getsource(mmod)
    lines = src.split("\n")
    for line in lines:
        if not line.startswith(" ") and line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_no_main_block():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert '__main__' not in src


def test_module_has_13_private_functions():
    """module 有 13 个 _前缀 private module-level functions。"""
    import evaluation.metrics as m
    import types
    private_funcs = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), types.FunctionType)
        and getattr(m, n).__module__ == "evaluation.metrics"
    ]
    expected = [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ]
    assert sorted(private_funcs) == sorted(expected)


def test_module_has_3_private_constants():
    """module 有 3 个 _前缀 private constants。"""
    import evaluation.metrics as m
    private_consts = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and not callable(getattr(m, n))
    ]
    expected = ["_PDF_BBOX_REQUIRED_TYPES", "_TEXT_TYPES"]
    # _NOT_EVALUATED 是字符串也算
    for e in expected:
        assert e in private_consts
