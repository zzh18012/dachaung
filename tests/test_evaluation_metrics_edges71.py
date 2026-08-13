"""evaluation/metrics.py 第八十六轮 edges 测试（Round 636）。

补强 edges70 未触及的角度（第四十六批）。

新角度：
- compute_automatic_metrics 完整 document 输入
- compute_automatic_metrics source_type 多种值
- compute_automatic_metrics 各种 expectations 边界
- compute_automatic_metrics image_base_dir 各种情况
- _image_resource_ratio 多种 image 元素组合
- _silent_drop_count 各种 expectations 组合
- _heading_boundary_ratio 各种 heading 位置
- _text_preservation Counter 多集合行为
- _pdf_locator_ratio 多种元素组合
- _docx_locator_ratio 多种 locator 字段组合
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百零六批
"""

from __future__ import annotations

import ast
import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.metrics as metrics_mod
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


# ---------- compute_automatic_metrics 完整 document ----------

def test_compute_full_pdf_document_batch46():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "content": "Body text", "element_id": "e2",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 100]}},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["e1"]},
            {"text": "Body text", "source_element_ids": ["e2"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["error_code"]["value"] is None
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_compute_full_docx_document_batch46():
    document = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "Hello", "element_id": "e1",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [
            {"text": "Hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_source_type_unknown_batch46():
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "unknown", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_source_type_empty_string_batch46():
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_with_expectations_none_batch46():
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["silent_drop_count"]["value"] is None


def test_compute_with_expectations_empty_dict_batch46():
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", {})
    # 空 expectations 视为 falsy → null
    assert out["silent_drop_count"]["value"] is None


def test_compute_with_expectations_no_element_count_batch46():
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", {"other_key": "x"})
    # expectations 不为空但缺 element_count_by_type → null
    assert out["silent_drop_count"]["value"] is None


def test_compute_with_expectations_full_match_batch46():
    document = {
        "elements": [
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    expectations = {
        "element_count_by_type": {"paragraph": 1, "heading": 1}
    }
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 0


def test_compute_with_expectations_drops_batch46():
    """expectations 期望 2 个 paragraph，实际 1 个 → drop 1。"""
    document = {
        "elements": [{"type": "paragraph"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"paragraph": 2}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 1


def test_compute_image_base_dir_none_batch46():
    document = {
        "elements": [{"type": "image", "resource_path": "img.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None, image_base_dir=None)
    # 文件不存在 → 0.0
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_image_base_dir_real_dir_batch46(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake data")
    document = {
        "elements": [{"type": "image", "resource_path": str(img)}],
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_returns_14_keys_batch46():
    document = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(document, None, "pdf", None)
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
    assert set(out.keys()) == expected_keys


def test_compute_pipeline_failed_returns_14_keys_batch46():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_element_count_by_type_value_batch46():
    document = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


def test_compute_element_count_by_type_unknown_for_missing_type_batch46():
    document = {
        "elements": [{"type": "custom_type"}],  # type 缺失走 "unknown"
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 实际 e.get("type", "unknown") 返回 "custom_type"，不是 "unknown"
    assert out["element_count_by_type"]["value"] == {"custom_type": 1}


def test_compute_element_count_by_type_uses_unknown_for_missing_key_batch46():
    document = {
        "elements": [{"no_type_key": "x"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1}


def test_compute_error_dict_passes_code_batch46():
    document = None
    error = {"code": "parse_failed", "message": "broken"}
    out = compute_automatic_metrics(document, error, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_error_dict_missing_code_raises_keyerror_batch46():
    document = None
    error = {"message": "no code"}
    with pytest.raises(KeyError):
        compute_automatic_metrics(document, error, "pdf", None)  # type: ignore[arg-type]


# ---------- _image_resource_ratio 多种 image ----------

def test_image_resource_ratio_no_image_returns_null_batch46():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_missing_resource_path_batch46():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    # 有 image 但没 resource_path → valid=0, ratio 0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch46():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_none_resource_path_batch46():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file_batch46(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_zero_size_file_batch46(tmp_path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_relative_with_base_dir_batch46(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_batch46(tmp_path):
    img = tmp_path / "good.png"
    img.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 各种 expectations ----------

def test_silent_drop_count_no_expectations_batch46():
    out = _silent_drop_count({}, None)
    assert out["value"] is None


def test_silent_drop_count_empty_expectations_batch46():
    out = _silent_drop_count({}, {})
    assert out["value"] is None


def test_silent_drop_count_no_element_count_key_batch46():
    out = _silent_drop_count({}, {"other": 1})
    assert out["value"] is None


def test_silent_drop_count_actual_more_than_expected_batch46():
    """实际比期望多 → 不算 drop（只数 deficit）。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_multi_type_partial_drop_batch46():
    by_type = {"paragraph": 1, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 3, "heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph drop 2 + heading drop 1 = 3
    assert out["value"] == 3


def test_silent_drop_count_expected_type_missing_in_actual_batch46():
    """期望的 type 实际没有 → 全部 drop。"""
    by_type = {"paragraph": 2}
    expectations = {"element_count_by_type": {"paragraph": 2, "heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    # heading drop 3
    assert out["value"] == 3


def test_silent_drop_count_extra_type_in_actual_ignored_batch46():
    """实际多出的 type 不算 drop（不数 surplus）。"""
    by_type = {"paragraph": 2, "image": 5}
    expectations = {"element_count_by_type": {"paragraph": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_returns_int_batch46():
    by_type = {"paragraph": 1}
    expectations = {"element_count_by_type": {"paragraph": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert isinstance(out["value"], int)


def test_silent_drop_count_zero_drop_batch46():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


# ---------- _heading_boundary_ratio 各种 ----------

def test_heading_boundary_ratio_no_heading_returns_null_batch46():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_returns_zero_batch46():
    """chunks=[] 但有 headings → matched=0, ratio=0.0（不是 null）。"""
    elements = [{"type": "heading", "element_id": "e1"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0
    assert out["reason"] is None


def test_heading_boundary_ratio_perfect_match_batch46():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match_batch46():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # 1 matched / 2 headings = 0.5
    assert out["value"] == 0.5


def test_heading_boundary_ratio_no_match_batch46():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["wrong"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_first_chunk_id_used_batch46():
    """只用 chunk 的第一个 element_id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "extra"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # ids[0] = "h1" → match
    assert out["value"] == 1.0


def test_heading_boundary_ratio_first_chunk_id_wrong_batch46():
    """chunk 的第一个 id 不匹配 heading → 不算 match。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["wrong", "h1"]}]  # ids[0] = "wrong"
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_empty_ids_batch46():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    # 空 ids → 不参与 → 0/1 = 0.0
    assert out["value"] == 0.0


# ---------- _text_preservation Counter 行为 ----------

def test_text_preservation_perfect_match_batch46():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_chunked_text_batch46():
    """chunker 把 word 切开 → 加空格 → 删除空白后仍 equal。"""
    elements = [{"type": "paragraph", "content": "helloworld"}]
    chunks = [{"text": "hello"}, {"text": "world"}]
    out = _text_preservation(elements, chunks)
    # 删除空白后：expected="helloworld", actual="helloworld"
    assert out["equal"]["value"] is True


def test_text_preservation_missing_char_batch46():
    """actual 丢失字符 → equal=False, recall<1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] < 1.0


def test_text_preservation_extra_char_batch46():
    """actual 多字符 → equal=False, precision<1。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] < 1.0


def test_text_preservation_reordered_batch46():
    """字符顺序不同 → equal=False, 但 Counter 相同 → precision=recall=1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # Counter 相同 → precision/recall 都是 1.0
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_batch46():
    """image 不参与 expected_sequence。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_empty_elements_empty_chunks_batch46():
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    # 都空 → equal=True, precision=null empty_expected_and_actual, recall=null
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] is not None or out["precision"]["value"] is not None


def test_text_preservation_returns_three_keys_batch46():
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    assert set(out.keys()) == {"equal", "precision", "recall"}


# ---------- _pdf_locator_ratio 多种元素 ----------

def test_pdf_locator_ratio_empty_returns_null_batch46():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_all_text_with_bbox_batch46():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_one_missing_bbox_batch46():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_caption_needs_bbox_batch46():
    """caption 在 _PDF_BBOX_REQUIRED_TYPES → 需要 bbox。"""
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_list_item_needs_bbox_batch46():
    elements = [{"type": "list_item", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_table_no_bbox_needed_batch46():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_returns_ratio_batch46():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert isinstance(out["value"], float)


# ---------- _docx_locator_ratio 多种 locator ----------

def test_docx_locator_ratio_empty_returns_null_batch46():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_run_index_batch46():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_table_index_batch46():
    elements = [{"type": "paragraph", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_row_col_index_batch46():
    elements = [{"type": "paragraph", "source_locator": {"row_index": 0, "col_index": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_no_structural_key_batch46():
    elements = [{"type": "paragraph", "source_locator": {"random_key": "x"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- module source 补强 ----------

def test_source_contains_pure_function_note_batch46():
    src = inspect.getsource(metrics_mod)
    assert "纯函数" in src


def test_source_contains_no_modification_note_batch46():
    src = inspect.getsource(metrics_mod)
    assert "不修改 document" in src


def test_source_contains_text_preservation_v11_batch46():
    src = inspect.getsource(metrics_mod)
    assert "v1.1" in src


def test_source_contains_v1_0_normalize_text_batch46():
    src = inspect.getsource(metrics_mod)
    assert "v1.0" in src


def test_source_contains_no_forgery_note_batch46():
    src = inspect.getsource(metrics_mod)
    assert "不伪造" in src


# ---------- AST 结构补强 ----------

def test_ast_text_preservation_uses_counter_batch46():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation"][0]
    has_counter = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "Counter":
                has_counter = True
    assert has_counter


def test_ast_chunk_reference_ratio_uses_set_comprehension_batch46():
    """_chunk_reference_ratio 用 set comprehension 做元素 id 集合。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_chunk_reference_ratio"][0]
    has_set = False
    for n in ast.walk(func):
        # set comprehension 是 ast.SetComp；显式 set() 是 ast.Call
        if isinstance(n, (ast.Set, ast.SetComp)):
            has_set = True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "set":
            has_set = True
    assert has_set


def test_ast_image_resource_ratio_uses_list_comprehension_batch46():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio"][0]
    has_list_comp = False
    for n in ast.walk(func):
        if isinstance(n, ast.ListComp):
            has_list_comp = True
    assert has_list_comp


def test_ast_silent_drop_count_uses_dict_get_batch46():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count"][0]
    has_get = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "get":
            has_get = True
    assert has_get


def test_ast_pdf_locator_ratio_uses_isinstance_batch46():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_pdf_locator_ratio"][0]
    has_isinstance = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "isinstance":
                has_isinstance = True
    assert has_isinstance


# ---------- forbidden tokens 第一百零六批 ----------

def test_source_no_eval_batch46():
    src = inspect.getsource(metrics_mod)
    assert "eval(" not in src


def test_source_no_exec_batch46():
    src = inspect.getsource(metrics_mod)
    assert "exec(" not in src


def test_source_no_compile_batch46():
    src = inspect.getsource(metrics_mod)
    assert "compile(" not in src


def test_source_no_globals_batch46():
    src = inspect.getsource(metrics_mod)
    assert "globals(" not in src


def test_source_no_locals_batch46():
    src = inspect.getsource(metrics_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch46():
    src = inspect.getsource(metrics_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch46():
    src = inspect.getsource(metrics_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch46():
    src = inspect.getsource(metrics_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch46():
    src = inspect.getsource(metrics_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch46():
    src = inspect.getsource(metrics_mod)
    assert "subprocess" not in src


def test_source_no_class_batch46():
    src = inspect.getsource(metrics_mod)
    assert "\nclass " not in src


def test_source_no_async_batch46():
    src = inspect.getsource(metrics_mod)
    assert "async def" not in src


def test_source_no_yield_batch46():
    src = inspect.getsource(metrics_mod)
    assert "yield" not in src


def test_source_no_walrus_batch46():
    src = inspect.getsource(metrics_mod)
    assert ":=" not in src


def test_source_no_lambda_batch46():
    """除了 sorted key 中的 lambda，其他地方不应有。"""
    src = inspect.getsource(metrics_mod)
    # metrics.py 没用 lambda（没有 sorted）
    assert "lambda" not in src
