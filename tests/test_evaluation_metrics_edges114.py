"""evaluation/metrics.py 第三百九十八轮 edges 测试（Round 954）。

补强 edges113 未触及的角度（第三百三十批，probe 实证）。

新角度：
- heading_boundary 语义：heading 是 chunk 首元素才算合规
  （首 → 1.0；中间 → 0.0；2 heading 1 命中 → 0.5；
  无 heading → no_heading_elements）
- 单侧空不对称：elements 有 + chunks 空 → eq False +
  P null empty_actual + R 0.0；反向 → P 0.0 + R null
  empty_expected
- silent_drop 混合多类型求和：{para 5, table 1, heading 2}
  vs 实际 {para 3, table 1} → 4（缺 2 + 全缺 2；饱和项 0）
- [None] 引用怪癖：element 缺 element_id → None 进集合；
  chunk source_element_ids [None] 真值 + None in 集合 →
  计有效 → 1.0
- type "footnote"（非 _PDF_BBOX_REQUIRED_TYPES）与缺
  type 键（get 默认 "unknown"）：by_type 记
  {footnote: 1, unknown: 1}；pdf locator 免 bbox →
  仅 page → 1.0
- forbidden tokens 第四百二十四批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _run(doc, st="pdf", exp=None):
    return compute_automatic_metrics(doc, None, st, exp)


# ---------- heading_boundary ----------

def _hdoc(chunk_ids):
    return {
        "elements": [
            {"type": "heading", "content": "H",
             "element_id": "h1"},
            {"type": "paragraph", "content": "P",
             "element_id": "p1"}],
        "chunks": [{"text": "X",
                    "source_element_ids": chunk_ids}]}


def test_heading_first_batch152():
    m = _run(_hdoc(["h1", "p1"]))
    assert m["heading_boundary_compliance"] == {"value": 1.0,
                                                "reason": None}


def test_heading_middle_zero_batch152():
    m = _run(_hdoc(["p1", "h1"]))
    assert m["heading_boundary_compliance"] == {"value": 0.0,
                                                "reason": None}


def test_no_headings_null_batch152():
    doc = {"elements": [
        {"type": "paragraph", "content": "P",
         "element_id": "p1"}],
        "chunks": [{"text": "P",
                    "source_element_ids": ["p1"]}]}
    assert _run(doc)["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_two_headings_half_batch152():
    doc = {"elements": [
        {"type": "heading", "content": "A",
         "element_id": "h1"},
        {"type": "heading", "content": "B",
         "element_id": "h2"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["h1"]}]}
    assert _run(doc)["heading_boundary_compliance"] == {
        "value": 0.5, "reason": None}


# ---------- 单侧空不对称 ----------

def test_one_sided_empty_actual_batch152():
    doc = {"elements": [
        {"type": "paragraph", "content": "ABC"}], "chunks": []}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_actual"}
    assert m["text_char_multiset_recall"] == {"value": 0.0,
                                              "reason": None}


def test_one_sided_empty_expected_batch152():
    doc = {"elements": [], "chunks": [{"text": "XY"}]}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {"value": 0.0,
                                                 "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected"}


# ---------- silent_drop 混合求和 ----------

def test_silent_drop_mixed_sum_batch152():
    doc = {"elements": [
        {"type": "paragraph", "content": "A"},
        {"type": "paragraph", "content": "B"},
        {"type": "paragraph", "content": "C"},
        {"type": "table", "content": "T"}], "chunks": []}
    exp = {"element_count_by_type": {"paragraph": 5,
                                     "table": 1,
                                     "heading": 2}}
    assert _run(doc, exp=exp)["silent_drop_count"] == {
        "value": 4, "reason": None}


# ---------- [None] 引用怪癖 ----------

def test_none_reference_quirk_batch152():
    doc = {"elements": [
        {"type": "paragraph", "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": [None]}]}
    assert _run(doc)["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- footnote / unknown 类型 ----------

def test_footnote_and_unknown_type_batch152():
    doc = {"elements": [
        {"type": "footnote", "content": "F",
         "source_locator": {"page": 1}},
        {"content": "N", "source_locator": {"page": 1}}],
        "chunks": []}
    m = _run(doc)
    assert m["element_count_by_type"] == {
        "value": {"footnote": 1, "unknown": 1},
        "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch152():
    src = _src()
    assert 'chunk_first_ids.add(ids[0])' in src
    assert 'if sum(c_actual.values()) == 0:' in src
    assert 'if sum(c_expected.values()) == 0:' in src
    assert 't = e.get("type", "unknown")' in src


# ---------- forbidden tokens 第四百二十四批 ----------

def test_source_no_eval_batch152():
    assert "eval(" not in _src()


def test_source_no_exec_batch152():
    assert "exec(" not in _src()


def test_source_no_compile_batch152():
    assert "compile(" not in _src()


def test_source_no_globals_batch152():
    assert "globals(" not in _src()


def test_source_no_locals_batch152():
    assert "locals(" not in _src()


def test_source_no_os_system_batch152():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch152():
    assert "subprocess" not in _src()


def test_source_no_popen_batch152():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch152():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch152():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch152():
    assert "socket" not in _src()


def test_source_no_requests_batch152():
    assert "requests" not in _src()


def test_source_no_urllib_batch152():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch152():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch152():
    assert "yield" not in _src()


def test_source_no_async_await_batch152():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch152():
    assert "open(" not in _src()
