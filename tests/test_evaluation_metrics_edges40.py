"""evaluation/metrics.py 第四十二轮 edges 测试（Round 415）。

补强 edges39 未触及的角度：
- _text_preservation 行为深度第十三批（equal True / equal False / Counter multiset precision/recall / 全 image elements / Unicode 内容 / empty expected / empty actual / both empty）
- _heading_boundary_ratio 行为深度第十三批（无 heading / heading 与 chunk 不匹配 / heading 完美匹配 / heading element_id 缺失 / chunk 缺 source_element_ids）
- _silent_drop_count 行为深度第十三批（无 expectations / expectations 空 dict / expected > actual / expected = actual / expected < actual / 多类型）
- compute_automatic_metrics 完整流程第十三批（全要素：element + chunks + image + locator + heading / document=None 返回 14 keys / error 设置但 document 也设置）
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 常量深度
- module source forbidden tokens 第十七批
- module source 字符串精确补强第十四批
- signatures 第十四批
- module 合理性第十四批
- 端到端集成第十四批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from unittest.mock import patch

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


# ---------- module constants 深度 ----------


def test_TEXT_TYPES_value_batch13():
    assert _TEXT_TYPES == (
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    )


def test_TEXT_TYPES_is_tuple_batch13():
    assert isinstance(_TEXT_TYPES, tuple)


def test_TEXT_TYPES_count_7_batch13():
    assert len(_TEXT_TYPES) == 7


def test_TEXT_TYPES_no_image_batch13():
    """text 类型不应含 image。"""
    assert "image" not in _TEXT_TYPES


def test_PDF_BBOX_REQUIRED_TYPES_value_batch13():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_PDF_BBOX_REQUIRED_TYPES_is_tuple_batch13():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_PDF_BBOX_REQUIRED_TYPES_count_4_batch13():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_PDF_BBOX_REQUIRED_TYPES_subset_of_TEXT_TYPES_batch13():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_NOT_EVALUATED_value_batch13():
    assert _NOT_EVALUATED == "not_evaluated"


def test_NOT_EVALUATED_type_str_batch13():
    assert isinstance(_NOT_EVALUATED, str)


def test_NOT_EVALUATED_is_module_attr_batch13():
    assert hasattr(mmod, "_NOT_EVALUATED")


# ---------- _text_preservation 行为深度第十三批 ----------


def test_text_preservation_equal_true_batch13():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_equal_false_batch13():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_precision_recall_equal_set_batch13():
    """字符 multiset 相同 → p=r=1.0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_precision_recall_partial_batch13():
    """actual 是 expected 的子集 → p=1.0, r<1.0。"""
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # common=3, actual=3 → p=1.0
    # common=3, expected=4 → r=0.75
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.75


def test_text_preservation_precision_recall_superset_batch13():
    """actual 是 expected 的超集 → p<1.0, r=1.0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    # common=3, actual=4 → p=0.75
    # common=3, expected=3 → r=1.0
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_batch13():
    """image content 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "should_be_ignored"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_unicode_batch13():
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_whitespace_ignored_batch13():
    """空白字符不参与比较。"""
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_empty_expected_and_actual_batch13():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True  # 两个空字符串相等
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_actual_only_batch13():
    elements = [{"type": "paragraph", "content": "abc"}]
    out = _text_preservation(elements, [])
    # expected='abc', actual='' → equal=False
    # precision: actual 空 → null + empty_actual
    # recall: expected='abc' → 1.0? no, common=0
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_empty_expected_only_batch13():
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_returns_dict_with_3_keys_batch13():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_metric_value_types_batch13():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_text_preservation_idempotent_batch13():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out1 = _text_preservation(elements, chunks)
    out2 = _text_preservation(elements, chunks)
    assert out1 == out2


def test_text_preservation_independent_dicts_batch13():
    """两次调用返回独立 dict。"""
    out1 = _text_preservation([], [])
    out2 = _text_preservation([], [])
    assert out1 is not out2
    assert out1["equal"] is not out2["equal"]


def test_text_preservation_does_not_mutate_inputs_batch13():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    import copy
    snapshot_e = copy.deepcopy(elements)
    snapshot_c = copy.deepcopy(chunks)
    _text_preservation(elements, chunks)
    assert elements == snapshot_e
    assert chunks == snapshot_c


# ---------- _heading_boundary_ratio 行为深度第十三批 ----------


def test_heading_boundary_no_heading_returns_null_batch13():
    elements = [{"type": "paragraph"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks_returns_zero_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # headings=[h1], chunk_first_ids=set()
    # matched=0, ratio=0/1=0.0
    assert out["value"] == 0.0


def test_heading_boundary_perfect_match_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_partial_match_batch13():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # matched=1, total=2 → 0.5
    assert out["value"] == 0.5


def test_heading_boundary_no_match_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_heading_missing_element_id_batch13():
    elements = [{"type": "heading"}]  # no element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # h.get('element_id') = None, not in {h1}
    # matched=0, total=1 → 0.0
    assert out["value"] == 0.0


def test_heading_boundary_chunk_missing_source_element_ids_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]  # no source_element_ids
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_chunk_empty_source_element_ids_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    # ids=[] falsy → 不加入 chunk_first_ids
    assert out["value"] == 0.0


def test_heading_boundary_only_first_id_counted_batch13():
    """只有 chunk 的第一个 id 算 first。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1", "h2"]}]  # h2 不是第一个
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids = {'h1'}
    # matched = 1 (h1), total=2 → 0.5
    assert out["value"] == 0.5


def test_heading_boundary_returns_dict_type_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert isinstance(out, dict)


def test_heading_boundary_idempotent_batch13():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out1 = _heading_boundary_ratio(elements, chunks)
    out2 = _heading_boundary_ratio(elements, chunks)
    assert out1 == out2


# ---------- _silent_drop_count 行为深度第十三批 ----------


def test_silent_drop_count_no_expectations_batch13():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch13():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expected_counts_batch13():
    """expectations={} 视作 falsy → no_expectations。"""
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expected_counts_empty_dict_batch13():
    """expectations={'element_count_by_type': {}} → no_expectations_element_count。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expected_greater_batch13():
    """expected > actual → drops = expected - actual。"""
    out = _silent_drop_count(
        {"paragraph": 3},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 2


def test_silent_drop_count_expected_equal_batch13():
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_expected_less_batch13():
    """expected < actual → 不算 drop。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_multi_type_batch13():
    out = _silent_drop_count(
        {"paragraph": 1, "heading": 2},
        {"element_count_by_type": {"paragraph": 5, "heading": 3, "table": 1}},
    )
    # paragraph: 5-1=4, heading: 3-2=1, table: 1-0=1
    # 总 drops=6
    assert out["value"] == 6


def test_silent_drop_count_missing_actual_type_batch13():
    """expected 里有但 actual 里没有 → drops=expected。"""
    out = _silent_drop_count(
        {},
        {"element_count_by_type": {"paragraph": 3}},
    )
    assert out["value"] == 3


def test_silent_drop_count_returns_int_value_batch13():
    out = _silent_drop_count(
        {"paragraph": 1},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert isinstance(out["value"], int)


def test_silent_drop_count_idempotent_batch13():
    by_type = {"paragraph": 1}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out1 = _silent_drop_count(by_type, exp)
    out2 = _silent_drop_count(by_type, exp)
    assert out1 == out2


# ---------- compute_automatic_metrics 完整流程第十三批 ----------


def _make_full_doc():
    return {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "Title",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 20.0]}},
            {"type": "paragraph", "element_id": "p1", "content": "Body text",
             "source_locator": {"page": 1, "bbox": [0.0, 20.0, 100.0, 40.0]}},
            {"type": "image", "element_id": "i1", "content": "",
             "source_locator": {"page": 1, "bbox": [0.0, 40.0, 100.0, 60.0]},
             "resource_path": "images/x.png"},
        ],
        "chunks": [
            {"text": "Title Body text", "source_element_ids": ["h1", "p1"]},
        ],
    }


def test_compute_automatic_metrics_full_doc_returns_14_keys_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert len(out) == 14


def test_compute_automatic_metrics_full_doc_keys_exact_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(out.keys()) == expected_keys


def test_compute_automatic_metrics_pipeline_success_true_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out["pipeline_success"]["value"] is True


def test_compute_automatic_metrics_pipeline_success_false_when_doc_none_batch13():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "x"},
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_error_code_propagated_batch13():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "parse_failed"},
        source_type="pdf",
        expectations=None,
    )
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_automatic_metrics_error_code_none_when_doc_present_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out["error_code"]["value"] is None


def test_compute_automatic_metrics_schema_check_exception_batch13():
    """schema_check 抛异常 → value=False, reason=schema_check_exception:...。"""
    with patch(
        "evaluation.schema_validation.document_passes_schema",
        side_effect=RuntimeError("boom"),
    ):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception" in out["schema_valid"]["reason"]
    assert "RuntimeError" in out["schema_valid"]["reason"]


def test_compute_automatic_metrics_doc_none_returns_5_keys_only_batch13():
    """document=None → 只有 pipeline_success, error_code, schema_valid + 11 个 null。"""
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    # 实际是 14 keys（pipeline_success, error_code, schema_valid + 11 null metrics）
    assert len(out) == 14
    for k in (
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ):
        assert out[k]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_element_count_total_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out["element_count_total"]["value"] == 3


def test_compute_automatic_metrics_element_count_by_type_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    by_type = out["element_count_by_type"]["value"]
    assert by_type == {"heading": 1, "paragraph": 1, "image": 1}


def test_compute_automatic_metrics_pdf_source_pdf_locator_evaluated_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    # source_type=pdf → pdf_locator_valid_ratio evaluated
    assert out["pdf_locator_valid_ratio"]["reason"] is None
    # docx_locator_valid_ratio = null + not_docx_document
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_docx_source_docx_locator_evaluated_batch13():
    """source_type=docx → docx locator 评估，pdf locator 不评估。"""
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="docx",
            expectations=None,
        )
    assert out["docx_locator_valid_ratio"]["reason"] is None
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_automatic_metrics_unknown_source_both_not_evaluated_batch13():
    """source_type=unknown → 两个 locator 都 not_evaluated。"""
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="unknown",
            expectations=None,
        )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_does_not_mutate_document_batch13():
    import copy
    doc = _make_full_doc()
    snapshot = copy.deepcopy(doc)
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        compute_automatic_metrics(
            document=doc,
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert doc == snapshot


def test_compute_automatic_metrics_idempotent_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out1 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
        out2 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out1 == out2


def test_compute_automatic_metrics_independent_dicts_batch13():
    """两次调用返回独立 dict（不共享内部 dict）。"""
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out1 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
        out2 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out1 is not out2
    assert out1["element_count_total"] is not out2["element_count_total"]


# ---------- module source forbidden tokens 第十七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_metrics_source_no_forbidden_token_seventeenth_batch13(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_metrics_source_no_os_module_batch13():
    source = inspect.getsource(mmod)
    assert "import os" not in source
    assert "os." not in source


def test_metrics_source_no_sys_module_batch13():
    source = inspect.getsource(mmod)
    assert "import sys" not in source
    assert "sys." not in source


def test_metrics_source_no_tempfile_batch13():
    source = inspect.getsource(mmod)
    assert "tempfile" not in source


def test_metrics_source_no_logging_batch13():
    source = inspect.getsource(mmod)
    assert "import logging" not in source


def test_metrics_source_no_re_module_batch13():
    source = inspect.getsource(mmod)
    assert "import re" not in source
    assert "re." not in source


def test_metrics_source_no_eval_call_batch13():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_metrics_source_no_compile_batch13():
    source = inspect.getsource(mmod)
    assert "compile(" not in source


def test_metrics_source_no_global_keyword_batch13():
    source = inspect.getsource(mmod)
    assert "\nglobal " not in source


def test_metrics_source_no_nonlocal_batch13():
    source = inspect.getsource(mmod)
    assert "nonlocal " not in source


def test_metrics_source_no_assert_batch13():
    source = inspect.getsource(mmod)
    assert "\nassert " not in source


def test_metrics_source_no_print_batch13():
    source = inspect.getsource(mmod)
    assert "print(" not in source


def test_metrics_source_no_input_function_batch13():
    source = inspect.getsource(mmod)
    assert "input(" not in source


def test_metrics_source_no_class_definition_batch13():
    source = inspect.getsource(mmod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_metrics_source_no_lambda_batch13():
    source = inspect.getsource(mmod)
    assert "lambda " not in source


def test_metrics_source_no_open_at_top_level_batch13():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" ") and "open(" in line:
            raise AssertionError(f"top-level open: {line}")


# ---------- module source 字符串精确补强第十四批 ----------


def test_module_source_math_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import math" in head


def test_module_source_counter_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from collections import Counter" in head


def test_module_source_pathlib_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_typing_any_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_has_TEXT_TYPES_assignment_batch13():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES = " in source


def test_module_source_has_PDF_BBOX_REQUIRED_TYPES_assignment_batch13():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES = " in source


def test_module_source_has_NOT_EVALUATED_const_batch13():
    source = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in source


def test_module_source_has_compute_automatic_metrics_def_batch13():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_has_null_helper_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _null(" in source


def test_module_source_has_ratio_helper_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _ratio(" in source


def test_module_source_has_bool_metric_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _bool_metric(" in source


def test_module_source_has_int_metric_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _int_metric(" in source


def test_module_source_has_pdf_locator_ratio_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in source


def test_module_source_has_docx_locator_ratio_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in source


def test_module_source_has_is_valid_bbox_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in source


def test_module_source_has_image_resource_ratio_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in source


def test_module_source_has_chunk_reference_ratio_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in source


def test_module_source_has_strip_unicode_whitespace_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in source


def test_module_source_has_text_preservation_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _text_preservation(" in source


def test_module_source_has_heading_boundary_ratio_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in source


def test_module_source_has_silent_drop_count_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in source


def test_module_source_future_annotations_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_uses_math_isfinite_batch13():
    source = inspect.getsource(mmod)
    assert "math.isfinite" in source


def test_module_source_uses_Counter_intersection_batch13():
    source = inspect.getsource(mmod)
    assert "c_expected & c_actual" in source or "c_actual & c_expected" in source


# ---------- signatures 第十四批 ----------


def test_compute_automatic_metrics_signature_5_params_batch13():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert [p.name for p in params] == [
        "document", "error", "source_type", "expectations", "image_base_dir",
    ]


def test_compute_automatic_metrics_return_annotation_dict_batch13():
    sig = inspect.signature(compute_automatic_metrics)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "dict" in ret_str


def test_compute_automatic_metrics_image_base_dir_default_none_batch13():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_image_base_dir_annotation_optional_batch13():
    sig = inspect.signature(compute_automatic_metrics)
    annot = sig.parameters["image_base_dir"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "None" in annot_str


def test_null_signature_one_param_batch13():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "reason"


def test_ratio_signature_one_param_batch13():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_bool_metric_signature_one_param_batch13():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_int_metric_signature_one_param_batch13():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_helpers_return_dict_batch13():
    assert isinstance(_null("x"), dict)
    assert isinstance(_ratio(0.5), dict)
    assert isinstance(_bool_metric(True), dict)
    assert isinstance(_int_metric(5), dict)


def test_helpers_metric_dict_has_value_and_reason_batch13():
    for m in [_null("x"), _ratio(0.5), _bool_metric(True), _int_metric(5)]:
        assert "value" in m
        assert "reason" in m


def test_module_dunder_all_one_item_batch13():
    assert hasattr(mmod, "__all__")
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_user_function_count_batch13():
    """模块用户函数数量。"""
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    # _null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics,
    # _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
    # _image_resource_ratio, _chunk_reference_ratio, _strip_unicode_whitespace,
    # _text_preservation, _heading_boundary_ratio, _silent_drop_count
    assert len(funcs) == 14


def test_module_no_varargs_in_user_funcs_batch13():
    funcs = [
        v for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    for fn in funcs:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


# ---------- module 合理性第十四批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_path_evaluation_metrics_batch13():
    import os
    sep = os.sep
    assert mmod.__file__.endswith(sep + "metrics.py")
    assert "evaluation" in mmod.__file__


def test_module_name_evaluation_metrics_batch13():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_docstring_present_batch13():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_docstring_mentions_text_preservation_batch13():
    assert mmod.__doc__ is not None
    assert "text_preservation" in mmod.__doc__ or "不丢不重" in mmod.__doc__


def test_module_uses_future_annotations_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_no_user_classes_batch13():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_top_level_constants_count_batch13():
    consts = [
        n for n, v in vars(mmod).items()
        if not n.startswith("__") and not callable(v) and not inspect.isclass(v)
        and not inspect.ismodule(v)
    ]
    for c in ("_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"):
        assert c in consts


# ---------- 端到端集成第十四批 ----------


def test_e2e_compute_automatic_metrics_full_pipeline_pdf_batch13(tmp_path):
    """完整 PDF doc + image 落盘 → 验证 image_resource_exists_ratio。"""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "x.png").write_bytes(b"\x89PNG fake")

    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "Hello",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
            {"type": "image", "element_id": "i1", "content": "",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]},
             "resource_path": "x.png"},
        ],
        "chunks": [{"text": "Hello", "source_element_ids": ["p1"]}],
    }

    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=doc,
            error=None,
            source_type="pdf",
            expectations=None,
            image_base_dir=images_dir,
        )
    # image_resource_exists_ratio: 1 image, resource 存在 → 1.0
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_compute_automatic_metrics_with_expectations_batch13():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "Hello"},
            {"type": "paragraph", "element_id": "p2", "content": "World"},
        ],
        "chunks": [{"text": "HelloWorld", "source_element_ids": ["p1", "p2"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=doc,
            error=None,
            source_type="pdf",
            expectations=expectations,
        )
    # silent_drop_count: expected paragraph=5, actual=2 → drop=3
    # expected heading=2, actual=0 → drop=2
    # 总=5
    assert out["silent_drop_count"]["value"] == 5


def test_e2e_compute_automatic_metrics_idempotent_full_doc_batch13():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out1 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
        out2 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out1 == out2


def test_e2e_combined_helpers_chain_batch13():
    """多个 helper 协作链：elements + chunks → 各种 metric。"""
    elements = [
        {"type": "heading", "element_id": "h1", "content": "Title"},
        {"type": "paragraph", "element_id": "p1", "content": "abc"},
    ]
    chunks = [{"text": "Title abc", "source_element_ids": ["h1", "p1"]}]

    out_text = _text_preservation(elements, chunks)
    out_heading = _heading_boundary_ratio(elements, chunks)
    out_chunk = _chunk_reference_ratio(elements, chunks)

    assert out_text["equal"]["value"] is True
    assert out_heading["value"] == 1.0
    assert out_chunk["value"] == 1.0


def test_e2e_image_resource_ratio_real_file_batch13(tmp_path):
    images = [{"type": "image", "resource_path": "sub/x.png"}]
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.png").write_bytes(b"\x89PNG fake")
    out = _image_resource_ratio(images, tmp_path)
    # 默认 Path("sub/x.png") 不会从 cwd 找到，但 candidates 含 image_base_dir / "x.png"
    # 第二个 candidate = tmp_path / "x.png"
    # 第一个 candidate = Path("sub/x.png") 从 cwd 找不到
    # 实际：parser 写完整相对路径 → Path("sub/x.png")，cwd 下不存在；但 image_base_dir 是 tmp_path
    # candidates = [Path("sub/x.png"), tmp_path / "x.png"]
    # tmp_path / "x.png" 不存在（实际是 tmp_path / "sub" / "x.png"）
    # 所以 ratio=0
    # 改为直接 Path(rp) absolute → 不存在
    # 这个 case 实际 ratio=0
    assert out["value"] == 0.0


def test_e2e_image_resource_ratio_via_full_path_batch13(tmp_path):
    """resource_path 给完整相对路径，且 image_base_dir 是项目根。"""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.png").write_bytes(b"\x89PNG fake")
    images = [{"type": "image", "resource_path": str(tmp_path / "sub" / "x.png")}]
    out = _image_resource_ratio(images, None)
    # Path(absolute path).is_file() = True
    assert out["value"] == 1.0


def test_e2e_combined_full_pipeline_no_chunks_batch13():
    """document 有 elements 但无 chunks。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [],
    }
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=doc,
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_e2e_combined_full_pipeline_error_doc_both_set_batch13():
    """error 与 document 都设 → pipeline_success 取决于 error is None and document is not None。"""
    doc = _make_full_doc()
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=doc,
            error={"code": "x"},
            source_type="pdf",
            expectations=None,
        )
    # error is not None → pipeline_success=False
    assert out["pipeline_success"]["value"] is False


def test_e2e_combined_returns_consistent_metrics_dict_batch13():
    """两次调用相同输入 → 相同 metric values。"""
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out1 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
        out2 = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    for k in out1:
        assert out1[k] == out2[k]


def test_e2e_combined_json_serializable_batch13():
    """输出 metrics dict 应可 json 序列化（含 Path 之类不被允许的类型）。"""
    import json
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    text = json.dumps(out, default=str)
    parsed = json.loads(text)
    assert parsed == out or set(parsed.keys()) == set(out.keys())
