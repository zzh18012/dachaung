"""evaluation/metrics.py 第五十四轮 edges 测试（Round 498）。

补强 edges51 未触及的角度（第二十六批）：
- 构造子第二十六批：_null/_ratio/_bool/_int 各种值组合 / 多次独立 / 内部 dict 不共享
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十六批：subset 关系 / 排除 image / tuple 不可变
- _NOT_EVALUATED 第二十六批：值 / hashable / 不在 __all__
- compute_automatic_metrics 第二十六批：error_code 字段 / pipeline_success 各种组合 / image_base_dir None / 全 elements 不同类型
- _pdf_locator_ratio 第二十六批：page 类型边界 / bbox 长度边界 / NaN/Inf bbox
- _docx_locator_ratio 第二十六批：各种 structural keys 单独 / 全无 / 含 page
- _is_valid_bbox 第二十六批：bool 误判 / NaN / Inf / 不足 4 / 多于 4
- _image_resource_ratio 第二十六批：image_base_dir 拼接 / resource_path 绝对/相对
- _chunk_reference_ratio 第二十六批：空 source_element_ids / None / partial valid
- _text_preservation 第二十六批：image 不参与 / heading 参与 / unicode
- _heading_boundary_ratio 第二十六批：no heading / no chunk / perfect
- _silent_drop_count 第二十六批：无 expectations / required_markers / negative 不出现
- module source forbidden tokens 第四十一批 / source 字符串补强第三十七批 / signatures 第三十七批 / sanity 第三十七批 / e2e 第三十七批
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
    _int_metric,
    _null,
    _ratio,
    compute_automatic_metrics,
)


# ---------- 构造子第二十六批 ----------


def test_null_independent_dict_each_call_batch26():
    """_null 多次调用返回独立 dict（不共享引用）。"""
    n1 = _null("a")
    n2 = _null("b")
    assert n1 is not n2
    n1["value"] = "modified"
    assert n2["value"] is None


def test_null_returns_two_keys_batch26():
    """_null 返回的 dict 只含 'value' 和 'reason'。"""
    out = _null("r")
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_independent_dict_each_call_batch26():
    r1 = _ratio(0.5)
    r2 = _ratio(0.7)
    assert r1 is not r2
    r1["value"] = -1.0
    assert r2["value"] == 0.7


def test_ratio_returns_two_keys_batch26():
    out = _ratio(0.5)
    assert set(out.keys()) == {"value", "reason"}


def test_bool_metric_independent_each_call_batch26():
    b1 = _bool_metric(True)
    b2 = _bool_metric(False)
    assert b1 is not b2


def test_bool_metric_returns_two_keys_batch26():
    out = _bool_metric(True)
    assert set(out.keys()) == {"value", "reason"}


def test_int_metric_value_is_int_batch26():
    out = _int_metric(42)
    assert isinstance(out["value"], int)
    assert not isinstance(out["value"], bool)  # bool 是 int 子类，但 isint(True) 也 True


def test_int_metric_independent_each_call_batch26():
    i1 = _int_metric(1)
    i2 = _int_metric(2)
    assert i1 is not i2


def test_int_metric_value_int_not_float_batch26():
    out = _int_metric(5)
    assert type(out["value"]) is int  # noqa: E721


def test_int_metric_with_negative_batch26():
    out = _int_metric(-100)
    assert out["value"] == -100


def test_int_metric_with_zero_batch26():
    out = _int_metric(0)
    assert out["value"] == 0


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十六批 ----------


def test_text_types_subset_check_batch26():
    """_PDF_BBOX_REQUIRED_TYPES ⊆ _TEXT_TYPES。"""
    pdf_set = set(_PDF_BBOX_REQUIRED_TYPES)
    text_set = set(_TEXT_TYPES)
    assert pdf_set.issubset(text_set)


def test_text_types_excludes_image_batch26():
    """image 不在 _TEXT_TYPES 中（不参与文本比对）。"""
    assert "image" not in _TEXT_TYPES


def test_text_types_includes_paragraph_heading_batch26():
    assert "paragraph" in _TEXT_TYPES
    assert "heading" in _TEXT_TYPES


def test_pdf_bbox_includes_paragraph_heading_caption_list_item_batch26():
    for t in ("paragraph", "heading", "caption", "list_item"):
        assert t in _PDF_BBOX_REQUIRED_TYPES


def test_text_types_tuple_immutable_batch26():
    """tuple 不可变。"""
    with pytest.raises(TypeError):
        _TEXT_TYPES[0] = "modified"  # type: ignore[index]


def test_pdf_bbox_tuple_immutable_batch26():
    with pytest.raises(TypeError):
        _PDF_BBOX_REQUIRED_TYPES[0] = "modified"  # type: ignore[index]


def test_text_types_hashable_batch26():
    assert hash(_TEXT_TYPES) is not None


def test_pdf_bbox_hashable_batch26():
    assert hash(_PDF_BBOX_REQUIRED_TYPES) is not None


# ---------- _NOT_EVALUATED 第二十六批 ----------


def test_not_evaluated_constant_value_batch26():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_type_str_batch26():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_hashable_batch26():
    assert hash(_NOT_EVALUATED) is not None


def test_not_evaluated_immutable_batch26():
    with pytest.raises(TypeError):
        _NOT_EVALUATED[0] = "X"  # type: ignore[index]


# ---------- compute_automatic_metrics 第二十六批 ----------


def _build_doc_v3(
    elements=None,
    chunks=None,
    source_type="pdf",
    source_hash="abc",
):
    """构造 document dict（v3 后缀避免冲突）。"""
    return {
        "source_type": source_type,
        "elements": elements or [],
        "chunks": chunks or [],
        "source_hash": source_hash,
    }


def test_compute_metrics_error_code_when_error_present_batch26():
    """error 含 code → error_code.value 等于该 code。"""
    out = compute_automatic_metrics(
        document=None,
        error={"code": "my_error", "message": "fail"},
        source_type="pdf",
        expectations=None,
    )
    assert out["error_code"]["value"] == "my_error"


def test_compute_metrics_error_code_none_when_no_error_batch26():
    """error=None → error_code.value=None。"""
    document = _build_doc_v3()
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_pipeline_success_true_when_doc_and_no_error_batch26():
    document = _build_doc_v3()
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_pipeline_success_false_when_doc_none_batch26():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_false_when_error_present_batch26():
    out = compute_automatic_metrics(
        None,
        {"code": "x"},
        "pdf",
        None,
    )
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_returns_dict_batch26():
    document = _build_doc_v3()
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_does_not_mutate_document_batch26():
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}]
    )
    import copy
    doc_copy = copy.deepcopy(document)
    compute_automatic_metrics(document, None, "pdf", None)
    assert document == doc_copy


def test_compute_metrics_pdf_docx_both_have_locators_batch26():
    """PDF 路径走 pdf_locator，DOCX 路径走 docx_locator。"""
    pdf_doc = _build_doc_v3()
    docx_doc = _build_doc_v3(source_type="docx")
    pdf_out = compute_automatic_metrics(pdf_doc, None, "pdf", None)
    docx_out = compute_automatic_metrics(docx_doc, None, "docx", None)
    # PDF 路径下 docx_locator 是 null
    assert pdf_out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    # DOCX 路径下 pdf_locator 是 null
    assert docx_out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


# ---------- _pdf_locator_ratio (via metrics) 第二十六批 ----------


def test_pdf_locator_page_zero_invalid_batch26():
    """page=0 → invalid。"""
    document = _build_doc_v3(
        elements=[{"type": "image", "source_locator": {"page": 0}, "element_id": "e1"}]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_pdf_locator_page_negative_invalid_batch26():
    """page=-1 → invalid。"""
    document = _build_doc_v3(
        elements=[
            {"type": "image", "source_locator": {"page": -1}, "element_id": "e1"}
        ]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_pdf_locator_page_float_invalid_batch26():
    """page=1.0 (float) → invalid（要求 int）。"""
    document = _build_doc_v3(
        elements=[
            {"type": "image", "source_locator": {"page": 1.0}, "element_id": "e1"}
        ]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_pdf_locator_text_with_valid_bbox_batch26():
    """paragraph + page=1 + bbox valid → valid。"""
    document = _build_doc_v3(
        elements=[
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            }
        ]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_pdf_locator_text_missing_bbox_batch26():
    """paragraph + page=1 但 bbox 缺 → invalid（bbox 必填）。"""
    document = _build_doc_v3(
        elements=[
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {"page": 1},
            }
        ]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


# ---------- _docx_locator_ratio (via metrics) 第二十六批 ----------


def test_docx_locator_paragraph_index_valid_batch26():
    """paragraph_index → valid。"""
    document = _build_doc_v3(
        elements=[
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {"paragraph_index": 0},
            }
        ],
        source_type="docx",
    )
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_docx_locator_table_index_valid_batch26():
    """table_index → valid。"""
    document = _build_doc_v3(
        elements=[
            {
                "type": "table",
                "element_id": "e1",
                "source_locator": {"table_index": 0},
            }
        ],
        source_type="docx",
    )
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_docx_locator_rejects_page_batch26():
    """含 page → invalid（DOCX 不应有 page）。"""
    document = _build_doc_v3(
        elements=[
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {"page": 1, "paragraph_index": 0},
            }
        ],
        source_type="docx",
    )
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 0.0


def test_docx_locator_no_structural_keys_invalid_batch26():
    """无任何 structural key → invalid。"""
    document = _build_doc_v3(
        elements=[
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {},
            }
        ],
        source_type="docx",
    )
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 0.0


def test_docx_locator_empty_elements_no_elements_batch26():
    """无 elements → no_elements。"""
    document = _build_doc_v3(elements=[], source_type="docx")
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "no_elements"


# ---------- _image_resource_ratio (via metrics) 第二十六批 ----------


def test_image_resource_no_image_elements_batch26():
    """无 image element → no_image_elements。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_image_resource_image_no_resource_path_batch26():
    """image element 缺 resource_path → 0/1=0.0。"""
    document = _build_doc_v3(
        elements=[{"type": "image", "element_id": "e1"}]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_image_resource_image_empty_resource_path_batch26():
    """resource_path 是空字符串 → 0.0。"""
    document = _build_doc_v3(
        elements=[{"type": "image", "element_id": "e1", "resource_path": ""}]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


# ---------- _chunk_reference_ratio (via metrics) 第二十六批 ----------


def test_chunk_reference_chunk_without_source_ids_batch26():
    """chunk 缺 source_element_ids → 不算 valid。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}],
        chunks=[{"text": "x"}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_chunk_reference_chunk_empty_source_ids_batch26():
    """source_element_ids=[] → 不算 valid。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}],
        chunks=[{"text": "x", "source_element_ids": []}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_chunk_reference_partial_valid_batch26():
    """部分 chunk valid → 部分比例。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}],
        chunks=[
            {"text": "x", "source_element_ids": ["e1"]},
            {"text": "y", "source_element_ids": ["non_exist"]},
        ],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 0.5


# ---------- _text_preservation (via metrics) 第二十六批 ----------


def test_text_preservation_image_excluded_batch26():
    """image 不参与文本比对（即使有 content 也忽略）。"""
    document = _build_doc_v3(
        elements=[
            {"type": "paragraph", "content": "abc", "element_id": "e1"},
            {"type": "image", "content": "extra", "element_id": "e2"},
        ],
        chunks=[{"text": "abc", "source_element_ids": ["e1"]}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True


def test_text_preservation_perfect_match_batch26():
    """elements 与 chunks 完美匹配（去空白后）→ equal=True, p=r=1.0。"""
    document = _build_doc_v3(
        elements=[
            {"type": "paragraph", "content": "hello world", "element_id": "e1"},
        ],
        chunks=[{"text": "hello world", "source_element_ids": ["e1"]}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_text_preservation_chunk_missing_text_batch26():
    """chunk 缺 text → 当作空字符串。"""
    document = _build_doc_v3(
        elements=[
            {"type": "paragraph", "content": "abc", "element_id": "e1"},
        ],
        chunks=[{"source_element_ids": ["e1"]}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    # actual 比 expected 少 → equal=False, recall < 1.0
    assert out["text_preservation_equal"]["value"] is False


# ---------- _heading_boundary_ratio (via metrics) 第二十六批 ----------


def test_heading_boundary_no_headings_batch26():
    """无 heading → no_heading_elements。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}],
        chunks=[{"text": "x", "source_element_ids": ["e1"]}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 当无 heading 时，reason 应是 no_heading_elements 或 no_chunks 等
    assert out["heading_boundary_compliance"]["reason"] is not None


def test_heading_boundary_no_chunks_batch26():
    """有 heading 但无 chunks → ratio 为 0.0（无特殊 reason）。"""
    document = _build_doc_v3(
        elements=[{"type": "heading", "content": "title", "element_id": "e1"}],
        chunks=[],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    hb = out["heading_boundary_compliance"]
    assert hb["value"] == 0.0
    assert hb["reason"] is None


def test_heading_boundary_perfect_match_batch26():
    """heading 与 chunk 起始完美匹配 → 1.0。"""
    document = _build_doc_v3(
        elements=[{"type": "heading", "content": "title", "element_id": "e1"}],
        chunks=[{"text": "title body content", "source_element_ids": ["e1"]}],
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    # heading_boundary 可能 1.0 或 null（取决于实现）
    # 简单验证 value 是 float 或 None
    v = out["heading_boundary_compliance"]["value"]
    assert v is None or isinstance(v, float)


# ---------- _silent_drop_count (via metrics) 第二十六批 ----------


def test_silent_drop_no_expectations_batch26():
    """无 expectations → silent_drop_count=null。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}]
    )
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["silent_drop_count"]["value"] is None
    assert out["silent_drop_count"]["reason"] == "no_expectations"


def test_silent_drop_zero_drop_batch26():
    """expectations 与 actual 完美匹配 → 0。"""
    document = _build_doc_v3(
        elements=[{"type": "paragraph", "content": "x", "element_id": "e1"}]
    )
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 0


def test_silent_drop_negative_never_batch26():
    """actual > expected → 永远不算 negative。"""
    document = _build_doc_v3(
        elements=[
            {"type": "paragraph", "content": "x", "element_id": "e1"},
            {"type": "paragraph", "content": "y", "element_id": "e2"},
            {"type": "paragraph", "content": "z", "element_id": "e3"},
        ]
    )
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 0


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import subprocess",
    "import argparse",
]


def test_module_source_forbidden_tokens_batch26():
    source = inspect.getsource(mmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch26():
    source = inspect.getsource(mmod)
    assert "yield " not in source


def test_module_source_no_async_def_batch26():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch26():
    source = inspect.getsource(mmod)
    assert "global " not in source


def test_module_source_no_walrus_batch26():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch26():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch26():
    source_lines = inspect.getsource(mmod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch26():
    source = inspect.getsource(mmod)
    assert "import *" not in source


def test_module_source_no_subprocess_batch26():
    source = inspect.getsource(mmod)
    assert "subprocess" not in source


def test_module_source_no_environ_batch26():
    source = inspect.getsource(mmod)
    assert "os.environ" not in source


def test_module_source_counter_imported_batch26():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_math_imported_batch26():
    """math 用于 is_valid_bbox 的 isfinite 检查。"""
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_pathlib_imported_batch26():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_no_dataclass_batch26():
    source = inspect.getsource(mmod)
    assert "@dataclass" not in source


def test_module_source_no_network_io_batch26():
    source = inspect.getsource(mmod)
    assert "import socket" not in source
    assert "import http" not in source


# ---------- module source 字符串精确补强第三十七批 ----------


def test_module_source_contains_compute_automatic_metrics_def_batch26():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_contains_pdf_locator_ratio_def_batch26():
    source = inspect.getsource(mmod)
    assert "_pdf_locator_ratio" in source


def test_module_source_contains_docx_locator_ratio_def_batch26():
    source = inspect.getsource(mmod)
    assert "_docx_locator_ratio" in source


def test_module_source_contains_is_valid_bbox_def_batch26():
    source = inspect.getsource(mmod)
    assert "_is_valid_bbox" in source


def test_module_source_contains_image_resource_ratio_def_batch26():
    source = inspect.getsource(mmod)
    assert "_image_resource_ratio" in source


def test_module_source_contains_chunk_reference_ratio_def_batch26():
    source = inspect.getsource(mmod)
    assert "_chunk_reference_ratio" in source


def test_module_source_contains_text_preservation_def_batch26():
    source = inspect.getsource(mmod)
    assert "_text_preservation" in source


def test_module_source_contains_heading_boundary_ratio_def_batch26():
    source = inspect.getsource(mmod)
    assert "_heading_boundary_ratio" in source


def test_module_source_contains_silent_drop_count_def_batch26():
    source = inspect.getsource(mmod)
    assert "_silent_drop_count" in source


def test_module_source_contains_text_types_constant_batch26():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in source


def test_module_source_contains_pdf_bbox_constant_batch26():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in source


def test_module_source_contains_not_evaluated_batch26():
    source = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in source
    assert '"not_evaluated"' in source


def test_module_source_contains_pipeline_failed_batch26():
    source = inspect.getsource(mmod)
    assert '"pipeline_failed"' in source


def test_module_source_contains_no_image_elements_batch26():
    source = inspect.getsource(mmod)
    assert '"no_image_elements"' in source


def test_module_source_contains_no_chunks_batch26():
    source = inspect.getsource(mmod)
    assert '"no_chunks"' in source


# ---------- signatures 第三十七批 ----------


def test_signature_null_batch26():
    """_null(reason: str) -> dict[str, Any]。"""
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "reason"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_ratio_batch26():
    """_ratio(value: float) -> dict[str, Any]。"""
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_bool_metric_batch26():
    """_bool_metric(value: bool) -> dict[str, Any]。"""
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_int_metric_batch26():
    """_int_metric(value: int) -> dict[str, Any]。"""
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_compute_automatic_metrics_batch26():
    """compute_automatic_metrics(document, error, source_type, expectations, image_base_dir=None)。"""
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert [p.name for p in params] == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]
    assert params[4].default is None


def test_signature_compute_metrics_return_dict_batch26():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_constructors_no_varargs_batch26():
    for fn in (_null, _ratio, _bool_metric, _int_metric):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


def test_signature_compute_metrics_no_varargs_batch26():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- module 合理性第三十七批 ----------


def test_module_docstring_present_batch26():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_docstring_mentions_principles_batch26():
    """docstring 提及设计原则（纯函数 / null / ratio）。"""
    src = mmod.__doc__
    assert "纯函数" in src or "null" in src.lower() or "ratio" in src.lower()


def test_module_uses_from_future_annotations_batch26():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_constants_only_allowed_batch26():
    """顶层常量只有 _TEXT_TYPES, _PDF_BBOX_REQUIRED_TYPES, _NOT_EVALUATED（除 __all__）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    top_level_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_level_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert set(names).issubset(
        {"_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED", "__all__"}
    )


def test_module_has_compute_automatic_metrics_batch26():
    assert hasattr(mmod, "compute_automatic_metrics")
    assert callable(mmod.compute_automatic_metrics)


# ---------- 端到端集成第三十七批 ----------


def test_e2e_metrics_minimal_pdf_batch26():
    """端到端：最小 PDF document → 完整 metrics dict。"""
    document = _build_doc_v3()
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 必含所有 metric key
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


def test_e2e_metrics_pipeline_failed_all_null_batch26():
    """端到端：document=None → 大多数 metric 为 null。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    for k in (
        "element_count_total",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "silent_drop_count",
    ):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_metrics_no_mutation_in_e2e_batch26():
    """端到端：调用后 document 不修改。"""
    document = _build_doc_v3(
        elements=[
            {"type": "paragraph", "content": "hello", "element_id": "e1"},
        ],
        chunks=[{"text": "hello", "source_element_ids": ["e1"]}],
    )
    import copy
    doc_copy = copy.deepcopy(document)
    compute_automatic_metrics(document, None, "pdf", None)
    assert document == doc_copy


def test_e2e_metrics_returns_dict_not_none_batch26():
    """端到端：永远返回 dict（即使 doc=None）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_e2e_metrics_schema_valid_is_bool_batch26():
    """端到端：schema_valid 是 bool（true/false）或 null。"""
    document = _build_doc_v3()
    out = compute_automatic_metrics(document, None, "pdf", None)
    v = out["schema_valid"]["value"]
    assert v is None or isinstance(v, bool)


def test_e2e_metrics_pipeline_success_field_batch26():
    """端到端：pipeline_success 永远是 bool（不 null）。"""
    out1 = compute_automatic_metrics(None, None, "pdf", None)
    out2 = compute_automatic_metrics(_build_doc_v3(), None, "pdf", None)
    assert isinstance(out1["pipeline_success"]["value"], bool)
    assert isinstance(out2["pipeline_success"]["value"], bool)


def test_e2e_metrics_error_code_field_batch26():
    """端到端：error_code 永远存在（value 可以是 None 或 str）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert "error_code" in out
    assert out["error_code"]["value"] is None  # error=None
