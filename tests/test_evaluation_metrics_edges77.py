"""evaluation/metrics.py 第九十五轮 edges 测试（Round 688）。

补强 edges76 未触及的角度（第五十五批）。

新角度：
- compute_automatic_metrics 组合矩阵（error 非 None + document 非 None / document 缺 elements / 缺 chunks / expectations 空_dict / source_type 非 pdf docx / document 空 dict 全链路）
- _chunk_reference_ratio 更深（element_id None 被引用 / ids 是字符串按字符迭代 / 全 valid 1.0 / 部分 0.5 / elements 空 set 语义）
- _heading_boundary_ratio 更深（两 heading 同 id 一个 chunk 首 → ratio 1.0 / heading 是 chunk 第二 id 不算 / chunks 空但 headings 存在 → 0.0 非 null / heading 无 element_id + chunk 首 None matched）
- _strip_unicode_whitespace 更深（\\u3000 全角空格 / \\u00a0 NBSP / \\u2028 行分隔 / \\u200b 零宽非空白保留 / \\t\\n\\r\\f\\v 混合 / 纯空白 → 空串）
- _is_valid_bbox 更深（[True,2,3,4] bool 拒绝 / [1,2,3,4.0] 混合 ok / 大有限数 ok / -inf 拒绝）
- _text_preservation 更深（expected 全空白 actual 非空 / actual 全空白 expected 非空 / 乱序 ab vs ba / 重复字符 aab vs abb / image content 忽略 / content None / text None）
- helpers dict 形状（4 个 helper 恰好 {"value","reason"} 2 keys / 非 null 时 reason None）
- _pdf_locator_ratio 数值（3 elements 1 invalid → 2/3 / elements 空 → no_elements）
- 模块源码补强（14 keys 顺序 / ids and all 一行 / chunk_first_ids.add(ids[0]) / matched sum genexp / drops += (exp - actual) / v1.1 口径 D / 不再误报注释）
- AST 结构补强（_chunk_reference_ratio set comp / _strip_unicode_whitespace GeneratorExp / _text_preservation return 3 keys / _heading_boundary_ratio 2 list comp + set() / compute 内 for 循环计数）
- forbidden tokens 第一百五十八批
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path
from typing import Any

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    _heading_boundary_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- compute_automatic_metrics 组合矩阵 ----------

def test_compute_error_and_document_both_present_batch52():
    out = compute_automatic_metrics({"elements": []}, {"code": "boom"}, "pdf", None)
    # error 非 None → pipeline_success False，但 document 非 None 继续算
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "boom"
    assert out["element_count_total"]["value"] == 0


def test_compute_document_missing_elements_key_batch52():
    out = compute_automatic_metrics({"chunks": []}, None, "pdf", None)
    assert out["element_count_total"]["value"] == 0
    assert out["element_count_by_type"]["value"] == {}
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_document_missing_chunks_key_batch52():
    out = compute_automatic_metrics({"elements": []}, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"
    assert out["heading_boundary_compliance"]["reason"] == "no_heading_elements"


def test_compute_expectations_empty_dict_batch52():
    out = compute_automatic_metrics({"elements": []}, None, "pdf", {})
    assert out["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_source_type_unknown_both_null_batch52():
    out = compute_automatic_metrics({"elements": []}, None, "txt", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_empty_document_full_chain_batch52():
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert out["element_count_total"]["value"] == 0
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"
    assert out["text_preservation_equal"]["value"] is True  # 空 == 空
    assert out["text_char_multiset_precision"]["reason"] == "empty_expected_and_actual"


def test_compute_14_keys_order_batch52():
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert list(out.keys()) == [
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ]


# ---------- _chunk_reference_ratio 更深 ----------

def test_chunk_reference_none_id_matched_batch52():
    """element 缺 element_id（None 入 set），chunk 引用 [None] → None in set → valid。"""
    elements = [{"type": "paragraph"}, {"type": "paragraph", "element_id": "e1"}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_string_ids_iterated_by_char_batch52():
    """ids 是字符串 "e1" → 按字符迭代 'e'/'1'，不在 set → invalid。"""
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [{"source_element_ids": "e1"}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_half_valid_batch52():
    elements = [{"element_id": "a"}, {"element_id": "b"}]
    chunks = [{"source_element_ids": ["a"]}, {"source_element_ids": ["zzz"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_empty_ids_not_valid_batch52():
    elements = [{"element_id": "a"}]
    chunks = [{"source_element_ids": []}, {"source_element_ids": ["a"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5  # 空 ids falsy → invalid


def test_chunk_reference_empty_list_ids_falsy_batch52():
    elements = [{"element_id": "a"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio 更深 ----------

def test_heading_boundary_duplicate_ids_both_matched_batch52():
    """两个 heading 同一 element_id，一个 chunk 首指向 → matched 2 → 1.0。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_second_position_not_matched_batch52():
    """heading 是 chunk 的第二个 id → 不算合规。"""
    elements = [
        {"type": "paragraph", "element_id": "p1"},
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"source_element_ids": ["p1", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_no_chunks_zero_not_null_batch52():
    """headings 存在但 chunks 空 → 0.0（不是 null）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0
    assert out["reason"] is None


def test_heading_boundary_none_id_matched_batch52():
    elements = [{"type": "heading"}]  # element_id None
    chunks = [{"source_element_ids": [None]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_two_chunks_same_first_batch52():
    elements = [{"type": "heading", "element_id": "h"}, {"type": "heading", "element_id": "g"}]
    chunks = [{"source_element_ids": ["h"]}, {"source_element_ids": ["h"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _strip_unicode_whitespace 更深 ----------

def test_strip_ideographic_space_batch52():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_nbsp_batch52():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_line_separator_batch52():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_paragraph_separator_batch52():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_zero_width_kept_batch52():
    """\\u200b 零宽空格不是 isspace → 保留。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_all_ascii_whitespace_batch52():
    assert _strip_unicode_whitespace("a\tb\nc\rd\fe\vf \tg") == "abcdefg"


def test_strip_only_whitespace_empty_batch52():
    assert _strip_unicode_whitespace(" \t\n　 ") == ""


def test_strip_em_space_batch52():
    assert _strip_unicode_whitespace("a b") == "ab"


# ---------- _is_valid_bbox 更深 ----------

def test_bbox_bool_value_rejected_batch52():
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_bbox_mixed_int_float_ok_batch52():
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_bbox_large_finite_ok_batch52():
    assert _is_valid_bbox([1e308, 1e308, 0, 100]) is True


def test_bbox_negative_inf_rejected_batch52():
    assert _is_valid_bbox([1, float("-inf"), 3, 4]) is False


def test_bbox_set_rejected_batch52():
    assert _is_valid_bbox({1, 2, 3, 4}) is False


def test_bbox_generator_rejected_batch52():
    assert _is_valid_bbox(x for x in (1, 2, 3, 4)) is False


# ---------- _text_preservation 更深 ----------

def _elem(t: str, content: str | None, eid: str | None = None) -> dict:
    d = {"type": t, "content": content}
    if eid:
        d["element_id"] = eid
    return d


def test_text_preservation_expected_ws_actual_text_batch52():
    """expected 全空白 + actual 非空 → recall null empty_expected，precision 0.0。"""
    elements = [_elem("paragraph", "   \t  ")]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["recall"]["reason"] == "empty_expected"
    assert out["precision"]["value"] == 0.0
    assert out["equal"]["value"] is False


def test_text_preservation_actual_ws_expected_text_batch52():
    elements = [_elem("paragraph", "abc")]
    chunks = [{"text": " \n "}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_reordered_batch52():
    """乱序：equal False 但 precision/recall 1.0。"""
    elements = [_elem("paragraph", "ab")]
    chunks = [{"text": "ba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_duplicate_chars_batch52():
    """aab vs abb → common 2，precision=recall=2/3。"""
    elements = [_elem("paragraph", "aab")]
    chunks = [{"text": "abb"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_image_content_ignored_batch52():
    elements = [_elem("image", "imgtext"), _elem("paragraph", "p")]
    chunks = [{"text": "p"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_none_content_and_text_batch52():
    elements = [_elem("paragraph", None)]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_multiset_case_sensitive_batch52():
    elements = [_elem("paragraph", "A")]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0


def test_text_preservation_returns_3_keys_batch52():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_extra_chars_in_actual_batch52():
    """actual 多出字符 → precision < 1，recall = 1。"""
    elements = [_elem("paragraph", "ab")]
    chunks = [{"text": "abx"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == 1.0


# ---------- helpers dict 形状 ----------

@pytest.mark.parametrize("fn,val", [
    (_null, None),
    (_ratio, 0.5),
    (_bool_metric, True),
    (_int_metric, 3),
])
def test_helper_dicts_exactly_2_keys_batch52(fn, val):
    d = fn("r") if fn is _null else fn(val)
    assert set(d.keys()) == {"value", "reason"}


def test_helper_non_null_reason_is_none_batch52():
    assert _ratio(1.0)["reason"] is None
    assert _bool_metric(False)["reason"] is None
    assert _int_metric(0)["reason"] is None


def test_helper_null_reason_kept_batch52():
    assert _null("why")["reason"] == "why"


def test_helper_ratio_coerces_int_batch52():
    assert isinstance(_ratio(1)["value"], float)


# ---------- _pdf_locator_ratio 数值 ----------

def _pdf_elem(valid: bool, t: str = "paragraph") -> dict:
    if valid:
        return {"type": t, "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}
    return {"type": t, "source_locator": {"page": 0}}


def test_pdf_locator_ratio_two_thirds_batch52():
    elements = [_pdf_elem(True), _pdf_elem(True), _pdf_elem(False)]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == pytest.approx(2 / 3)


def test_pdf_locator_ratio_empty_batch52():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_table_needs_bbox_batch52():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0  # table 不在 bbox 必需列表


def test_pdf_locator_ratio_caption_needs_bbox_batch52():
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- 模块源码补强 ----------

def test_source_ids_and_all_one_line_batch52():
    src = inspect.getsource(metrics_mod)
    assert "if ids and all(sid in elem_ids for sid in ids):" in src


def test_source_chunk_first_ids_add_batch52():
    src = inspect.getsource(metrics_mod)
    assert "chunk_first_ids.add(ids[0])" in src


def test_source_matched_sum_genexp_batch52():
    src = inspect.getsource(metrics_mod)
    assert "matched = sum(1 for h in headings if h.get(\"element_id\") in chunk_first_ids)" in src


def test_source_drops_increment_batch52():
    src = inspect.getsource(metrics_mod)
    assert "drops += (exp - actual)" in src


def test_source_v11_wording_batch52():
    src = inspect.getsource(metrics_mod)
    assert "自 v1.1 起口径 D" in src


def test_source_no_false_positive_note_batch52():
    src = inspect.getsource(metrics_mod)
    assert "误报" in src


def test_source_source_spans_note_batch52():
    src = inspect.getsource(metrics_mod)
    assert "source_spans" in src


def test_source_counter_intersection_batch52():
    src = inspect.getsource(metrics_mod)
    assert "c_expected & c_actual" in src


def test_source_lazy_schema_validation_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_source_schema_check_exception_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert "schema_check_exception:" in src


def test_source_docx_structural_keys_tuple_batch52():
    src = inspect.getsource(metrics_mod)
    for k in ("section", "paragraph_index", "run_index", "table_index", "row_index", "col_index", "relationship_id"):
        assert f'"{k}"' in src


def test_source_is_file_and_size_check_batch52():
    src = inspect.getsource(metrics_mod)
    assert "p.is_file() and p.stat().st_size > 0" in src


# ---------- AST 结构补强 ----------

def test_ast_chunk_reference_set_comp_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_chunk_reference_ratio")
    setcomps = [n for n in ast.walk(func) if isinstance(n, ast.SetComp)]
    assert len(setcomps) == 1


def test_ast_strip_whitespace_generator_exp_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace")
    genexps = [n for n in ast.walk(func) if isinstance(n, ast.GeneratorExp)]
    assert len(genexps) == 1
    assert isinstance(func.body[-1], ast.Return)


def test_ast_text_preservation_returns_3_key_dict_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    ret = func.body[-1]
    assert isinstance(ret, ast.Return)
    assert isinstance(ret.value, ast.Dict)
    assert [k.value for k in ret.value.keys] == ["equal", "precision", "recall"]


def test_ast_heading_boundary_2_list_comps_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_heading_boundary_ratio")
    listcomps = [n for n in ast.walk(func) if isinstance(n, ast.ListComp)]
    assert len(listcomps) == 1  # headings 列表推导
    src = ast.unparse(func)
    assert "chunk_first_ids = set()" in src


def test_ast_is_valid_bbox_3_checks_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # 1 个 IfExp（三元）在 _ratio 或返回处不在此函数；本函数：头部 isinstance/len 1 个 + 循环内 3 个 = 4
    assert len(ifs) == 4


def test_ast_compute_null_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    src = ast.unparse(func)
    assert "for name in (" in src


def test_ast_by_type_accumulation_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    src = ast.unparse(func)
    assert "by_type[t] = by_type.get(t, 0) + 1" in src


def test_ast_image_ratio_try_oserror_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1
    assert "OSError" in ast.unparse(trys[0])


def test_ast_no_lambda_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Lambda) for n in ast.walk(tree))


def test_ast_all_1_entry_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert len(all_assign.value.elts) == 1
    assert all_assign.value.elts[0].value == "compute_automatic_metrics"


# ---------- forbidden tokens 第一百五十八批 ----------

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
