"""evaluation/metrics.py 第二百七十九轮 edges 测试（Round 835）。

补强 edges97 未触及的角度（第二百零九批）。

新角度：
- schema 校验抛异常 → schema_valid value=False +
  reason="schema_check_exception:ValueError"
- error dict 缺 "code" 键 → KeyError（现状记录）
- expected/actual 双空 → precision/recall null
  （empty_expected_and_actual）但 equal 为 True
- 单侧空：expected 空 → precision 0.0 / recall null；
  actual 空 → precision null / recall 0.0
- 乱序不交换：expected "ab" vs actual "ba" →
  equal False 且 P=R=1.0（多集合对乱序盲）
- silent_drop 超额交付（actual > expected）→ 0 非 null
- expectations 无 element_count_by_type →
  no_expectations_element_count
- heading 非 chunk 首元素 → 0.0
- 空 source_element_ids 的 chunk 不计入 intact
- NBSP / 全角空格参与空白剥离
- forbidden tokens 第三百零五批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, st="pdf", exp=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, None, st, exp)


# ---------- schema 异常 ----------

def test_schema_check_exception_reason_batch55():
    def boom(d):
        raise ValueError("x")

    with patch.object(sv, "document_passes_schema", boom):
        m = cam(_doc([_el("e1", "paragraph")]), None, "pdf",
                None)
    assert m["schema_valid"] == {
        "value": False,
        "reason": "schema_check_exception:ValueError"}


# ---------- error 缺 code ----------

def test_error_dict_missing_code_keyerror_batch55():
    try:
        with patch.object(sv, "document_passes_schema",
                          lambda d: True):
            cam(_doc([]), {"message": "m"}, "pdf", None)
        raise AssertionError("no error")
    except KeyError as e:
        assert e.args[0] == "code"


# ---------- 双空 / 单侧空 ----------

def test_both_empty_nulls_equal_true_batch55():
    m = _cam(_doc([_el("i1", "image", content=None)],
                  [{"text": None}]))
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    for k in ("text_char_multiset_precision",
              "text_char_multiset_recall"):
        assert m[k] == {"value": None,
                        "reason": "empty_expected_and_actual"}


def test_expected_empty_asymmetric_batch55():
    m = _cam(_doc([_el("i1", "image", content=None)],
                  [{"text": "AB"}]))
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 0.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected"}


def test_actual_empty_asymmetric_batch55():
    m = _cam(_doc([_el("e1", "paragraph", content="AB")],
                  [{"text": None}]))
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_actual"}
    assert m["text_char_multiset_recall"] == {
        "value": 0.0, "reason": None}


# ---------- 乱序不交换 ----------

def test_transposition_equal_false_prf_one_batch55():
    m = _cam(_doc([_el("e1", "paragraph", content="ab")],
                  [{"text": "ba"}]))
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- silent_drop 超额 ----------

def test_silent_drop_over_delivery_zero_batch55():
    els = [_el("e1", "paragraph"), _el("e2", "paragraph"),
           _el("e3", "paragraph")]
    m = _cam(_doc(els), exp={"element_count_by_type": {
        "paragraph": 2}})
    assert m["silent_drop_count"] == {"value": 0, "reason": None}


def test_expectations_without_counts_reason_batch55():
    m = _cam(_doc([_el("e1", "paragraph")]),
             exp={"something_else": 1})
    assert m["silent_drop_count"] == {
        "value": None,
        "reason": "no_expectations_element_count"}


# ---------- heading 非首 ----------

def test_heading_not_first_zero_batch55():
    els = [_el("h1", "heading"), _el("p1", "paragraph")]
    chunks = [{"source_element_ids": ["p1", "h1"]}]
    m = _cam(_doc(els, chunks))
    assert m["heading_boundary_compliance"] == {
        "value": 0.0, "reason": None}


# ---------- 空 ids chunk ----------

def test_empty_ids_chunk_half_batch55():
    els = [_el("p1", "paragraph")]
    chunks = [{"source_element_ids": []},
              {"source_element_ids": ["p1"]}]
    m = _cam(_doc(els, chunks))
    assert m["chunk_reference_intact_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- NBSP / 全角空格 ----------

def test_unicode_whitespace_stripped_batch55():
    nbsp_text = "A 　B"
    assert nbsp_text[1].isspace() and nbsp_text[2].isspace()
    m = _cam(_doc([_el("e1", "paragraph",
                       content="A 　B")],
                  [{"text": "AB"}]))
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "schema_check_exception:{type(e).__name__}" in src
    assert "chunk_first_ids.add(ids[0])" in src
    assert '_null("empty_actual")' in src
    assert '_null("empty_expected")' in src


# ---------- forbidden tokens 第三百零五批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
