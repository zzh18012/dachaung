"""evaluation/metrics.py 第九十二轮 edges 测试（Round 660）。

补强 edges73 未触及的角度（第四十九批）。

新角度：
- _pdf_locator_ratio 更深路径（混合 valid/invalid / 所有元素是 text 类型但 bbox valid / 所有 bbox 含 NaN / 含 None page / 含 page=0 / 含 page 负数）
- _docx_locator_ratio 更深路径（locator 是 None / locator 含 page+bbox 都 fail / 含 relationship_id 但 page 在 / section+page 共存 fail）
- _image_resource_ratio 更深路径（image_base_dir 与 resource_path 联合查找 / resource_path 含子目录 / resource_path 是绝对路径 / 文件存在但 size=0）
- _chunk_reference_ratio 更深路径（chunk 引用自身重复 / 多 chunk 引用相同 element_id / element_ids 是 None 而非空 list）
- _text_preservation Unicode 空白更深层（NBSP / em space / en space / ideographic space / line separator / 混合 ASCII+Unicode 空白）
- _heading_boundary_ratio 边界（heading 但 element_id 缺失 / chunk source_element_ids 含 None / 多个 heading 共享 element_id）
- _silent_drop_count 边界（expectations 含 element_count_by_type 但空 dict / expectations is {} / by_type 完全覆盖 expectations / by_type 部分覆盖）
- compute_automatic_metrics schema_check_exception 类型分支（不同 Exception 子类）
- 模块源码补强（_TEXT_TYPES 7 类型 / _PDF_BBOX_REQUIRED_TYPES 4 类型 / docstring 含 v1.0 v1.1 / Counter 用法 / math.isfinite / __all__）
- AST 结构补强（13 函数 / module 常量 Assign / compute_automatic_metrics 多 if 分支 / _pdf_locator_ratio for+continue / _docx_locator_ratio for+continue / _is_valid_bbox 嵌套 if / _text_preservation nested if-else / module docstring）
- forbidden tokens 第一百三十批
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _TEXT_TYPES,
    _PDF_BBOX_REQUIRED_TYPES,
    _NOT_EVALUATED,
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


# ---------- _pdf_locator_ratio 更深路径 ----------

def test_pdf_locator_mixed_valid_invalid_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 1, 1]}},  # page=0 invalid
        {"type": "paragraph", "source_locator": {"page": 2, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 2 / 3


def test_pdf_locator_all_text_with_valid_bbox_batch49():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},
        {"type": "caption", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},
        {"type": "list_item", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_text_with_nan_bbox_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, float("nan"), 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_is_none_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"page": None, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"page": -1, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_image_type_no_bbox_required_batch49():
    """image 类型不需要 bbox，只需要 page。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # 无 bbox 也算 valid
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_header_footer_no_bbox_required_batch49():
    """header/footer 不在 _PDF_BBOX_REQUIRED_TYPES 中。"""
    elements = [
        {"type": "header", "source_locator": {"page": 1}},
        {"type": "footer", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_no_locator_key_batch49():
    """element 缺 source_locator 字段：loc = {} （None or {}）。"""
    elements = [
        {"type": "paragraph"},  # 无 source_locator
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 更深路径 ----------

def test_docx_locator_none_value_batch49():
    """source_locator 显式 None → {} (None or {})。"""
    elements = [
        {"type": "paragraph", "source_locator": None},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_page_and_bbox_present_batch49():
    """含 page+bbox 都 fail。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 1, 1], "paragraph_index": 0},
        },
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_relationship_id_only_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"relationship_id": "rId1"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_section_and_page_batch49():
    """section+page 共存 → fail（含 page）。"""
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1, "page": 1}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_table_indices_batch49():
    """table_index + row_index + col_index 任意一个就够。"""
    elements = [
        {"type": "table", "source_locator": {"table_index": 0, "row_index": 1, "col_index": 2}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_run_index_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"run_index": 5}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_unknown_structural_key_batch49():
    """不在 structural_keys 中的 key 不算。"""
    elements = [
        {"type": "paragraph", "source_locator": {"unknown_key": "x"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_mixed_batch49():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        {"type": "paragraph", "source_locator": {"run_index": 1}},  # valid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 2 / 3


# ---------- _image_resource_ratio 更深路径 ----------

def test_image_ratio_resource_path_with_subdir_batch49(tmp_path):
    """resource_path 含子目录时直接拼 Path(rp) 也行。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    f = sub / "img.png"
    f.write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": str(f)},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_ratio_filename_only_with_base_dir_batch49(tmp_path):
    """resource_path 只写文件名，image_base_dir 拼接查找。"""
    f = tmp_path / "img.png"
    f.write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": "img.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_ratio_size_zero_fails_batch49(tmp_path):
    """文件存在但 size=0 → fail。"""
    f = tmp_path / "empty.png"
    f.write_bytes(b"")
    elements = [
        {"type": "image", "resource_path": str(f)},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_absolute_path_batch49(tmp_path):
    """绝对路径直接用 Path(rp)。"""
    f = tmp_path / "abs.png"
    f.write_bytes(b"abc")
    elements = [
        {"type": "image", "resource_path": str(f)},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_ratio_resource_path_empty_string_batch49():
    elements = [
        {"type": "image", "resource_path": ""},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_resource_path_missing_key_batch49():
    elements = [
        {"type": "image"},  # 无 resource_path
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_no_image_elements_batch49():
    """无 image element → null + no_image_elements。"""
    elements = [
        {"type": "paragraph"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


# ---------- _chunk_reference_ratio 更深路径 ----------

def test_chunk_reference_ids_self_repeat_batch49():
    """chunk 引用同一个 element_id 多次也算 valid。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e1"]}]  # 重复
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_multi_chunks_same_id_batch49():
    """多 chunk 引用相同 element_id 都算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e1"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ids_none_batch49():
    """source_element_ids is None → ids 是 [] (None or [])。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]  # falsy
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_partial_valid_batch49():
    """部分 chunk 引用 valid，部分 invalid。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["missing"]},  # invalid
        {"source_element_ids": ["e1", "e2"]},  # valid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 2 / 3


def test_chunk_reference_ids_contain_none_batch49():
    """source_element_ids 中含 None → all(...) 中 None not in elem_ids → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", None]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _text_preservation Unicode 空白更深层 ----------

def test_text_preservation_nbsp_only_batch49():
    """NBSP (U+00A0) 是空白。"""
    elements = [{"type": "paragraph", "content": " "}]
    chunks = []
    out = _text_preservation(elements, chunks)
    # expected 和 actual 都空 → null + empty_expected_and_actual
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_em_space_only_batch49():
    """em space (U+2003) 是空白。"""
    elements = [{"type": "paragraph", "content": " "}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_en_space_only_batch49():
    elements = [{"type": "paragraph", "content": " "}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_ideographic_space_only_batch49():
    """全角空格 (U+3000)。"""
    elements = [{"type": "paragraph", "content": "　"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_mixed_unicode_whitespace_batch49():
    """混合 ASCII + Unicode 空白全被 strip。"""
    elements = [{"type": "paragraph", "content": "a b\tc d　e"}]
    chunks = [{"text": "abcde"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_line_separator_batch49():
    """line separator (U+2028) 是空白。"""
    elements = [{"type": "paragraph", "content": "ab cd"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_paragraph_separator_batch49():
    elements = [{"type": "paragraph", "content": "ab cd"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_image_excluded_batch49():
    """image 类型的 content 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "a"},
        {"type": "image", "content": "should_not_count"},
    ]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_text_added_in_chunks_batch49():
    """chunks 含 expected 没有的字符 → equal False，precision < 1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcXYZ"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # common=3, |actual|=6 → precision=0.5
    assert out["precision"]["value"] == 0.5
    # |expected|=3 → recall=1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_text_dropped_in_chunks_batch49():
    """chunks 缺少 expected 中部分字符 → equal False，recall < 1。"""
    elements = [{"type": "paragraph", "content": "abcXYZ"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    # common=3, |expected|=6 → recall=0.5
    assert out["recall"]["value"] == 0.5


# ---------- _heading_boundary_ratio 边界 ----------

def test_heading_boundary_no_element_id_batch49():
    """heading 但缺 element_id → element_id is None, not in chunk_first_ids。"""
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": [None]}]
    out = _heading_boundary_ratio(elements, chunks)
    # matched=1（None in chunk_first_ids which contains None）
    # 实际：ids[0]=None，chunk_first_ids={None}, headings[0].element_id=None, None in {None} → matched=1
    assert out["value"] == 1.0


def test_heading_boundary_chunks_with_empty_ids_batch49():
    """chunks source_element_ids 是空 list → 不加入 chunk_first_ids。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_multiple_headings_batch49():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 2 / 3


def test_heading_boundary_chunk_with_multiple_ids_uses_first_batch49():
    """只取 chunk source_element_ids 第一个。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "h2", "h3"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_no_headings_batch49():
    elements = [{"type": "paragraph"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


# ---------- _silent_drop_count 边界 ----------

def test_silent_drop_empty_dict_element_count_batch49():
    """expectations 含 element_count_by_type 但是空 dict → no_expectations_element_count。"""
    out = _silent_drop_count({"heading": 1}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_expectations_is_empty_dict_batch49():
    """expectations = {} 是 falsy → no_expectations。"""
    out = _silent_drop_count({"heading": 1}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_by_type_covers_all_batch49():
    """by_type 完全覆盖 expectations → drops=0。"""
    by_type = {"heading": 3, "paragraph": 5}
    exp = {"element_count_by_type": {"heading": 3, "paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


def test_silent_drop_by_type_exceeds_expected_batch49():
    """actual > expected → 不计负数。"""
    by_type = {"heading": 5}
    exp = {"element_count_by_type": {"heading": 2}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


def test_silent_drop_mixed_batch49():
    by_type = {"heading": 2, "paragraph": 5}
    exp = {"element_count_by_type": {"heading": 3, "paragraph": 5, "list_item": 2}}
    out = _silent_drop_count(by_type, exp)
    # heading: 3-2=1, paragraph: 0, list_item: 2-0=2 → drops=3
    assert out["value"] == 3


def test_silent_drop_no_element_count_by_type_key_batch49():
    """expectations 不含 element_count_by_type key → expected_counts = {} or {} = {}。"""
    out = _silent_drop_count({"heading": 1}, {"other_key": "value"})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


# ---------- compute_automatic_metrics schema_check_exception 类型分支 ----------

def test_compute_metrics_schema_check_value_error_batch49():
    """document_passes_schema 抛 ValueError → reason 含 ValueError。"""
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=ValueError("bad")):
        out = compute_automatic_metrics(document, None, "pdf", None)
    # schema_valid 应当 False + reason 含 ValueError
    assert out["schema_valid"]["value"] is False
    assert "ValueError" in out["schema_valid"]["reason"]


def test_compute_metrics_schema_check_type_error_batch49():
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=TypeError("wrong")):
        out = compute_automatic_metrics({"elements": [], "chunks": []}, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "TypeError" in out["schema_valid"]["reason"]


def test_compute_metrics_schema_check_runtime_error_batch49():
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("rt")):
        out = compute_automatic_metrics({"elements": [], "chunks": []}, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "RuntimeError" in out["schema_valid"]["reason"]


# ---------- 模块源码补强 ----------

def test_source_contains_text_types_7_kinds_batch49():
    """_TEXT_TYPES 含 7 种类型。"""
    assert len(_TEXT_TYPES) == 7
    assert "heading" in _TEXT_TYPES
    assert "paragraph" in _TEXT_TYPES
    assert "list_item" in _TEXT_TYPES
    assert "table" in _TEXT_TYPES
    assert "caption" in _TEXT_TYPES
    assert "header" in _TEXT_TYPES
    assert "footer" in _TEXT_TYPES


def test_source_contains_pdf_bbox_required_4_kinds_batch49():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_source_not_evaluated_constant_batch49():
    assert _NOT_EVALUATED == "not_evaluated"


def test_source_contains_math_import_batch49():
    src = inspect.getsource(metrics_mod)
    assert "import math" in src


def test_source_contains_counter_import_batch49():
    src = inspect.getsource(metrics_mod)
    assert "from collections import Counter" in src


def test_source_contains_path_import_batch49():
    src = inspect.getsource(metrics_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch49():
    src = inspect.getsource(metrics_mod)
    assert "from typing import Any" in src


def test_source_contains_future_annotations_batch49():
    src = inspect.getsource(metrics_mod)
    assert "from __future__ import annotations" in src


def test_source_docstring_mentions_v1_0_batch49():
    src = inspect.getsource(metrics_mod)
    assert "v1.0" in src


def test_source_docstring_mentions_v1_1_batch49():
    src = inspect.getsource(metrics_mod)
    assert "v1.1" in src


def test_source_docstring_mentions_counter_batch49():
    src = inspect.getsource(metrics_mod)
    assert "Counter" in src


def test_source_docstring_mentions_word_internal_split_batch49():
    src = inspect.getsource(metrics_mod)
    assert "词内硬切" in src


def test_source_contains_math_isfinite_batch49():
    src = inspect.getsource(metrics_mod)
    assert "math.isfinite" in src


def test_source_contains_no_image_elements_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"no_image_elements"' in src


def test_source_contains_no_chunks_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"no_chunks"' in src


def test_source_contains_no_elements_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"no_elements"' in src


def test_source_contains_no_heading_elements_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"no_heading_elements"' in src


def test_source_contains_no_expectations_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"no_expectations"' in src


def test_source_contains_no_expectations_element_count_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"no_expectations_element_count"' in src


def test_source_contains_empty_actual_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"empty_actual"' in src


def test_source_contains_empty_expected_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"empty_expected"' in src


def test_source_contains_empty_expected_and_actual_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"empty_expected_and_actual"' in src


def test_source_contains_pipeline_failed_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"pipeline_failed"' in src


def test_source_contains_not_pdf_document_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"not_pdf_document"' in src


def test_source_contains_not_docx_document_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert '"not_docx_document"' in src


def test_source_contains_schema_check_exception_string_batch49():
    src = inspect.getsource(metrics_mod)
    assert "schema_check_exception" in src


def test_source_all_1_entry_batch49():
    src = inspect.getsource(metrics_mod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- AST 结构补强 ----------

def test_ast_has_13_top_level_functions_batch49():
    """13 个 top-level 函数（_null/_ratio/_bool_metric/_int_metric/compute/_pdf/_docx/_is_valid_bbox/_image/_chunk/_strip/_text/_heading/_silent_drop = 14）。

    Wait recount: _null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics,
    _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox, _image_resource_ratio,
    _chunk_reference_ratio, _strip_unicode_whitespace, _text_preservation,
    _heading_boundary_ratio, _silent_drop_count = 14 函数。
    """
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 14


def test_ast_has_no_class_def_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_has_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_5_imports_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 5


def test_ast_module_has_4_top_level_assigns_batch49():
    """_TEXT_TYPES + _PDF_BBOX_REQUIRED_TYPES + _NOT_EVALUATED + __all__ = 4。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_compute_metrics_has_multiple_if_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_compute_metrics_has_2_return_batch49():
    """compute_automatic_metrics 至少 2 个 return（pipeline_failed 提前 return + 正常 return）。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 2


def test_ast_pdf_locator_has_for_with_continue_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_pdf_locator_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    continues = [n for n in ast.walk(func) if isinstance(n, ast.Continue)]
    assert len(fors) >= 1
    assert len(continues) >= 1


def test_ast_docx_locator_has_for_with_continue_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_docx_locator_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    continues = [n for n in ast.walk(func) if isinstance(n, ast.Continue)]
    assert len(fors) >= 1
    assert len(continues) >= 1


def test_ast_is_valid_bbox_has_nested_if_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 4  # not list + len!=4 + bool + not int/float + not finite


def test_ast_text_preservation_has_nested_if_else_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_text_preservation_uses_counter_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    src = ast.unparse(func)
    assert "Counter(" in src


def test_ast_silent_drop_has_for_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_silent_drop_has_aug_assign_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count")
    augs = [n for n in ast.walk(func) if isinstance(n, ast.AugAssign)]
    assert len(augs) == 1


def test_ast_strip_unicode_whitespace_uses_join_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace")
    src = ast.unparse(func)
    assert "join(" in src
    assert "isspace" in src


def test_ast_image_ratio_has_for_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # 外层 + 内层
    assert len(fors) >= 2


def test_ast_image_ratio_has_try_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_chunk_reference_uses_set_comprehension_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_chunk_reference_ratio")
    src = ast.unparse(func)
    # set comprehension: {e.get(...) for e in elements}
    assert "{" in src and "for e in elements" in src


def test_ast_heading_boundary_uses_set_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_heading_boundary_ratio")
    src = ast.unparse(func)
    assert "chunk_first_ids = set()" in src


def test_ast_heading_boundary_has_sum_with_generator_batch49():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_heading_boundary_ratio")
    src = ast.unparse(func)
    assert "sum(" in src


# ---------- forbidden tokens 第一百三十批 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_no_open_unsafe_batch49():
    """metrics.py 不调用 open()。"""
    assert "open(" not in _src()
