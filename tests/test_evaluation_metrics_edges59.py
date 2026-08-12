"""evaluation/metrics.py 第六十轮 edges 测试（Round 547）。

补强 edges58 未触及的角度（第三十三批）。
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
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


# ---------- _TEXT_TYPES 第三十三批 ----------


def test_text_types_count_seven_batch33():
    assert len(_TEXT_TYPES) == 7


def test_text_types_paragraph_in_pdf_bbox_required_batch33():
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


def test_text_types_all_in_text_types_or_image_batch33():
    """_TEXT_TYPES 不含 image（与 _PDF_BBOX_REQUIRED_TYPES 都是 _TEXT_TYPES 子集）。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


# ---------- _PDF_BBOX_REQUIRED_TYPES 第三十三批 ----------


def test_pdf_bbox_required_types_count_four_batch33():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_first_heading_batch33():
    assert _PDF_BBOX_REQUIRED_TYPES[0] == "heading"


# ---------- _NOT_EVALUATED 第三十三批 ----------


def test_not_evaluated_constant_module_level_batch33():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in src


# ---------- 构造器第三十三批 ----------


def test_null_value_is_none_batch33():
    out = _null("x")
    assert out["value"] is None


def test_ratio_keys_count_batch33():
    out = _ratio(0.5)
    assert len(out) == 2


def test_bool_metric_keys_count_batch33():
    out = _bool_metric(True)
    assert len(out) == 2


def test_int_metric_keys_count_batch33():
    out = _int_metric(5)
    assert len(out) == 2


def test_null_keys_set_batch33():
    out = _null("reason_x")
    assert set(out.keys()) == {"value", "reason"}


# ---------- compute_automatic_metrics 第三十三批 ----------


def test_compute_automatic_metrics_no_document_no_error_batch33():
    """document=None, error=None → pipeline_success=False, error_code=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


def test_compute_automatic_metrics_error_no_code_batch33():
    """error dict 无 code key → error_code 是 None（d.get）。"""
    out = compute_automatic_metrics(None, {}, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_automatic_metrics_with_image_batch33(tmp_path):
    """含 image element 但无文件 → ratio=0.0（不是 null）。"""
    doc = {
        "elements": [{"type": "image", "element_id": "i1", "resource_path": "x.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_automatic_metrics_with_image_no_image_elements_batch33(tmp_path):
    """无 image element → null。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] is None


def test_compute_automatic_metrics_with_chunks_no_elements_batch33():
    doc = {"elements": [], "chunks": [{"text": "x", "source_element_ids": ["e1"]}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # chunks 引用 e1 但 elements 空 → 0/1
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_compute_automatic_metrics_no_chunks_batch33():
    doc = {"elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] is None
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_automatic_metrics_keys_count_batch33():
    """成功时返回 metrics keys：13 个基础 + 1 个 error_code + 1 个 pipeline_success + 1 schema_valid + 1 silent_drop_count = 14 个左右。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
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
    assert expected_keys.issubset(set(out.keys()))


def test_compute_automatic_metrics_schema_valid_with_invalid_doc_batch33():
    """document 不通过 schema 校验 → schema_valid=False。

    注：元素必须是 dict 列表才能正常迭代；这里给一个合法结构但缺 element_id
    以触发 schema valid=False。
    """
    doc = {"elements": [{"type": "paragraph", "content": "x"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # schema 校验失败（缺 element_id）→ schema_valid=False
    assert out["schema_valid"]["value"] is False


# ---------- _pdf_locator_ratio 第三十三批 ----------


def test_pdf_locator_ratio_no_elements_returns_null_batch33():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_text_with_valid_bbox_batch33():
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_heading_without_bbox_batch33():
    """heading 在 _PDF_BBOX_REQUIRED_TYPES → 需要 bbox。"""
    elements = [{"type": "heading", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_caption_with_valid_bbox_batch33():
    elements = [
        {
            "type": "caption",
            "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_image_no_bbox_required_batch33():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES → 只看 page。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 第三十三批 ----------


def test_docx_locator_ratio_no_elements_returns_null_batch33():
    out = _docx_locator_ratio([])
    assert out["value"] is None


def test_docx_locator_ratio_with_table_index_batch33():
    elements = [{"type": "table", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_row_col_index_batch33():
    elements = [{"type": "paragraph", "source_locator": {"row_index": 1, "col_index": 2}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_mixed_batch33():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (page)
        {"type": "paragraph", "source_locator": {"weird_key": "x"}},  # invalid (no structural)
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0 / 3.0


# ---------- _is_valid_bbox 第三十三批 ----------


def test_is_valid_bbox_returns_bool_type_batch33():
    assert type(_is_valid_bbox([0, 0, 0, 0])) is bool


def test_is_valid_bbox_with_floats_batch33():
    assert _is_valid_bbox([0.5, 0.5, 1.5, 1.5]) is True


def test_is_valid_bbox_with_ints_batch33():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_mixed_int_float_batch33():
    assert _is_valid_bbox([0, 0.5, 1, 1.5]) is True


# ---------- _image_resource_ratio 第三十三批 ----------


def test_image_resource_ratio_image_base_dir_none_no_file_batch33():
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_returns_dict_batch33(tmp_path):
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert isinstance(out, dict)


def test_image_resource_ratio_keys_count_batch33(tmp_path):
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert len(out) == 2


# ---------- _chunk_reference_ratio 第三十三批 ----------


def test_chunk_reference_ratio_no_chunks_returns_null_batch33():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    out = _chunk_reference_ratio(elements, [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_returns_dict_batch33():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert isinstance(out, dict)


# ---------- _strip_unicode_whitespace 第三十三批 ----------


def test_strip_unicode_whitespace_empty_string_batch33():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace_batch33():
    assert _strip_unicode_whitespace("   \t\n") == ""


def test_strip_unicode_whitespace_no_whitespace_batch33():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_returns_str_batch33():
    assert isinstance(_strip_unicode_whitespace(""), str)


# ---------- _text_preservation 第三十三批 ----------


def test_text_preservation_returns_three_keys_batch33():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_perfect_match_batch33():
    elements = [{"type": "paragraph", "content": "hello", "element_id": "e1"}]
    chunks = [{"text": "hello", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_actual_missing_chunk_text_batch33():
    elements = [{"type": "paragraph", "content": "abc", "element_id": "e1"}]
    chunks = [{"text": "ab", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual="ab"
    # equal=False, precision=2/2=1.0, recall=2/3=0.667
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(2 / 3)


# ---------- _heading_boundary_ratio 第三十三批 ----------


def test_heading_boundary_ratio_returns_dict_batch33():
    elements = [{"type": "heading", "content": "x", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert isinstance(out, dict)


def test_heading_boundary_ratio_keys_count_batch33():
    elements = [{"type": "heading", "content": "x", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert len(out) == 2


def test_heading_boundary_ratio_no_heading_returns_null_batch33():
    elements = [{"type": "paragraph", "content": "x", "element_id": "e1"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


# ---------- _silent_drop_count 第三十三批 ----------


def test_silent_drop_count_no_expectations_returns_null_batch33():
    out = _silent_drop_count({}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null_batch33():
    out = _silent_drop_count({}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expected_counts_returns_null_batch33():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_returns_dict_batch33():
    out = _silent_drop_count({}, None)
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第五十批 ----------


def test_module_source_no_subprocess_batch33():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch33():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch33():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch33():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch33():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch33():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch33():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch33():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch33():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch33():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch33():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_unlink_batch33():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十六批 ----------


def test_module_source_contains_module_docstring_batch33():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_text_types_constant_batch33():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_required_constant_batch33():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_not_evaluated_constant_batch33():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in src


def test_module_source_contains_null_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_contains_ratio_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_contains_bool_metric_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_contains_int_metric_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_contains_compute_automatic_metrics_func_batch33():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_pdf_locator_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_is_valid_bbox_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_contains_image_resource_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_contains_chunk_reference_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_contains_strip_unicode_whitespace_batch33():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_text_preservation_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_contains_heading_boundary_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_contains_silent_drop_count_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


# ---------- signatures 第四十六批 ----------


def test_signature_null_params_batch33():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_params_batch33():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_bool_metric_params_batch33():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_int_metric_params_batch33():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_compute_automatic_metrics_params_count_batch33():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


# ---------- module 合理性第四十六批 ----------


def test_module_has_future_annotations_batch33():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch33():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch33():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch33():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch33():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch33():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_all_has_compute_automatic_metrics_batch33():
    src = inspect.getsource(mmod)
    assert '"compute_automatic_metrics"' in src


def test_module_no_main_block_batch33():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十六批 ----------


def test_e2e_compute_automatic_metrics_full_pdf_batch33(tmp_path):
    """端到端 PDF：完整 pipeline 输出。"""
    doc = {
        "elements": [
            {
                "type": "heading",
                "content": "title",
                "element_id": "h1",
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 30.0]},
            },
            {
                "type": "paragraph",
                "content": "hello",
                "element_id": "e1",
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 50.0]},
            },
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["docx_locator_valid_ratio"]["value"] is None


def test_e2e_pipeline_failed_passes_all_null_batch33():
    out = compute_automatic_metrics(None, {"code": "X"}, "pdf", None)
    for k in [
        "element_count_total",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    ]:
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_idempotent_full_run_batch33():
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_no_input_modification_batch33():
    import json
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    error = None
    expectations = {"element_count_by_type": {"paragraph": 1}}
    doc_before = json.dumps(doc, sort_keys=True)
    exp_before = json.dumps(expectations, sort_keys=True)
    compute_automatic_metrics(doc, error, "pdf", expectations)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(expectations, sort_keys=True) == exp_before


def test_e2e_returns_dict_batch33():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_e2e_docx_with_full_data_batch33():
    """端到端 DOCX 完整。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {"paragraph_index": 0, "section": 1},
            },
            {
                "type": "heading",
                "content": "title",
                "element_id": "h1",
                "source_locator": {"paragraph_index": 1, "section": 1},
            },
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "x", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_silent_drop_with_expectations_batch33():
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 3, "heading": 2}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 4
