"""evaluation/metrics.py 第九十七轮 edges 测试（Round 702）。

补强 edges78 未触及的角度（第六十七批）。

新角度：
- compute document=None 全键集与顺序（14 键：pipeline_success False / error_code None / schema_valid pipeline_failed / 11 个 null）
- error_code 透传（code 字符串 / code None）
- _silent_drop_count（expectations {} → no_expectations / element_count_by_type {} → 二级 reason / expected>actual 不计负 / 多类型求和 / by_type 缺类型按 0）
- _text_preservation 不对称空（expected "" actual "x" → precision 0.0 recall null empty_expected / 反向 → precision null empty_actual recall 0.0 / 全 image → 双 null empty_expected_and_actual）
- _is_valid_bbox（tuple 拒 / str 拒 / 长度 3·5 拒 / inf·NaN 拒 / 负数可 / bool 拒）
- _strip_unicode_whitespace（零宽空格 U+200B 保留（isspace False）/ 行分隔符 U+2028 删）
- _pdf_locator_ratio（page "1" 拒 / page 1.0 拒 / page 0·-1 拒 / page True 通过（bool 是 int 子类，记录现状））
- _docx_locator_ratio（run/table/row/col_index 也是结构键 / 只 page 拒）
- _heading_boundary_ratio（heading 缺 element_id 不匹配 / chunk 空 ids 不计）
- _chunk_reference_ratio（chunk 缺键 → 无效 / element 缺 element_id 时 None 入集合的现状）
- element_count_by_type（type 显式 None → {None: 1} 非 unknown）
- AST 补强（_TEXT_TYPES 7 项 unparse / _PDF_BBOX_REQUIRED_TYPES 4 项 / 模块常量顺序 / compute 前两个下标赋值）
- forbidden tokens 第一百七十二批
"""

from __future__ import annotations

import ast
import inspect
import math
from typing import Any

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _silent_drop_count,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- compute document=None 全键集 ----------

def test_compute_failed_full_key_order_batch52():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert list(out.keys()) == [
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ]
    assert out["pipeline_success"]["value"] is False
    assert out["schema_valid"]["reason"] == "pipeline_failed"
    for k in out:
        if k in ("pipeline_success", "error_code"):
            continue
        assert out[k]["reason"] == "pipeline_failed", k


def test_error_code_passthrough_batch52():
    out = compute_automatic_metrics(None, {"code": "parse_failed", "message": "x"}, "pdf", None)
    assert out["error_code"] == {"value": "parse_failed", "reason": None}


def test_error_code_none_in_dict_batch52():
    out = compute_automatic_metrics(None, {"code": None}, "pdf", None)
    assert out["error_code"]["value"] is None


# ---------- _silent_drop_count ----------

def test_silent_drop_empty_expectations_batch52():
    assert _silent_drop_count({"paragraph": 1}, {})["reason"] == "no_expectations"


def test_silent_drop_empty_expected_counts_batch52():
    out = _silent_drop_count({"paragraph": 1}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_no_negative_batch52():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 3}})
    assert out["value"] == 0  # expected < actual 不计


def test_silent_drop_multi_type_sum_batch52():
    out = _silent_drop_count(
        {"paragraph": 1, "heading": 2},
        {"element_count_by_type": {"paragraph": 4, "heading": 2, "table": 3}},
    )
    # paragraph 3 + table 3 = 6
    assert out["value"] == 6


def test_silent_drop_missing_type_counts_zero_batch52():
    out = _silent_drop_count({}, {"element_count_by_type": {"caption": 2}})
    assert out["value"] == 2


# ---------- _text_preservation 不对称空 ----------

def test_text_preservation_expected_empty_only_batch52():
    elements = [{"type": "image", "resource_path": "x"}]
    chunks = [{"text": "x"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0  # common 0 / |actual| 1
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_actual_empty_only_batch52():
    elements = [{"type": "paragraph", "content": "x"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_all_image_both_null_batch52():
    elements = [{"type": "image", "resource_path": "x"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True  # "" == ""
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_image_content_ignored_batch52():
    """image 的 content 即使非空也不计入 expected。"""
    elements = [
        {"type": "image", "content": "IMGDATA"},
        {"type": "paragraph", "content": "ab"},
    ]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


# ---------- _is_valid_bbox ----------

def test_bbox_tuple_rejected_batch52():
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_bbox_string_rejected_batch52():
    assert _is_valid_bbox("0001") is False


def test_bbox_wrong_lengths_batch52():
    assert _is_valid_bbox([0, 0, 1]) is False
    assert _is_valid_bbox([0, 0, 1, 1, 1]) is False
    assert _is_valid_bbox([]) is False


def test_bbox_infinite_rejected_batch52():
    assert _is_valid_bbox([0, 0, 1, math.inf]) is False
    assert _is_valid_bbox([0, 0, math.nan, 1]) is False


def test_bbox_negative_ok_batch52():
    assert _is_valid_bbox([-1.5, -2, 0, 3]) is True


def test_bbox_bool_rejected_batch52():
    assert _is_valid_bbox([True, False, True, False]) is False


# ---------- _strip_unicode_whitespace 特殊字符 ----------

def test_strip_keeps_zero_width_space_batch52():
    """U+200B 的 isspace() 是 False，所以保留。"""
    s = "a" + chr(0x200B) + "b"
    assert _strip_unicode_whitespace(s) == s


def test_strip_removes_line_separator_batch52():
    """U+2028 行分隔符的 isspace() 是 True，所以删除。"""
    assert _strip_unicode_whitespace("a" + chr(0x2028) + "b") == "ab"


# ---------- _pdf_locator_ratio page 类型 ----------

def test_pdf_page_string_rejected_batch52():
    out = _pdf_locator_ratio([{"type": "header", "source_locator": {"page": "1"}}])
    assert out["value"] == 0.0


def test_pdf_page_float_rejected_batch52():
    out = _pdf_locator_ratio([{"type": "header", "source_locator": {"page": 1.0}}])
    assert out["value"] == 0.0


def test_pdf_page_zero_and_negative_batch52():
    assert _pdf_locator_ratio([{"type": "header", "source_locator": {"page": 0}}])["value"] == 0.0
    assert _pdf_locator_ratio([{"type": "header", "source_locator": {"page": -1}}])["value"] == 0.0


def test_pdf_page_true_quirk_batch52():
    """bool 是 int 子类：page=True 现状下算合法（1 ≥ 1）。"""
    out = _pdf_locator_ratio([{"type": "header", "source_locator": {"page": True}}])
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 结构键 ----------

@pytest.mark.parametrize("key", [
    "run_index", "table_index", "row_index", "col_index", "section",
])
def test_docx_structural_keys_batch52(key):
    out = _docx_locator_ratio([{"source_locator": {key: 0}}])
    assert out["value"] == 1.0


def test_docx_page_only_rejected_batch52():
    out = _docx_locator_ratio([{"source_locator": {"page": 1}}])
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio / _chunk_reference_ratio ----------

def test_heading_missing_element_id_not_matched_batch52():
    elements = [{"type": "heading"}, {"type": "heading", "element_id": "h"}]
    chunks = [{"source_element_ids": ["h"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_chunk_empty_ids_not_counted_batch52():
    elements = [{"type": "heading", "element_id": "h"}]
    chunks = [{"source_element_ids": []}, {"source_element_ids": None}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_missing_key_invalid_batch52():
    elements = [{"element_id": "e1"}]
    chunks = [{"no_ids": 1}, {"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_ref_first_id_only_batch52():
    """all() 语义：所有 id 都要存在。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1"]}]
    assert _chunk_reference_ratio(elements, chunks)["value"] == 1.0


# ---------- element_count_by_type 显式 None ----------

def test_by_type_explicit_none_key_batch52():
    out = compute_automatic_metrics(
        {"elements": [{"type": None, "content": "x"}]}, None, "pdf", None
    )
    assert out["element_count_by_type"]["value"] == {None: 1}


# ---------- helpers 快速补充 ----------

def test_null_value_is_none_batch52():
    assert _null("r") == {"value": None, "reason": "r"}


def test_bool_metric_false_batch52():
    assert _bool_metric(0)["value"] is False


def test_int_metric_negative_batch52():
    assert _int_metric(-5) == {"value": -5, "reason": None}


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(metrics_mod))


def test_ast_text_types_unparse_batch52():
    tree = _tree()
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "_TEXT_TYPES"
    )
    assert ast.unparse(assign) == (
        "_TEXT_TYPES = ('heading', 'paragraph', 'list_item', 'table', "
        "'caption', 'header', 'footer')"
    )


def test_ast_pdf_bbox_types_unparse_batch52():
    tree = _tree()
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "_PDF_BBOX_REQUIRED_TYPES"
    )
    assert ast.unparse(assign) == "_PDF_BBOX_REQUIRED_TYPES = ('heading', 'paragraph', 'caption', 'list_item')"


def test_ast_module_constants_order_batch52():
    tree = _tree()
    names = [
        n.targets[0].id for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
    ]
    assert names == ["_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED", "__all__"]


def test_ast_compute_first_two_subscript_assigns_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    subs = [
        ast.unparse(n.targets[0]) for n in func.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)
    ]
    assert subs[0] == "metrics['pipeline_success']"
    assert subs[1] == "metrics['error_code']"


# ---------- forbidden tokens 第一百七十二批 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch52():
    assert "open(" not in _src()
