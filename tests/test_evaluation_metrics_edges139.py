"""evaluation/metrics.py 第五百六十轮 edges 测试（Round 1218）。

补强 edges138 未触及的角度（第五百九十批，probe 实证）。

新角度（悬空引用算 intact / 错误通道旁路 / hbc 分母）：
- **悬空引用 0.0**——chunk source_
  element_ids 指向不存在元素 →
  chunk_reference_intact_ratio 0.0
  （schema 层照过（edges132 锁），
  metrics 层在此捕获——跨层对照
  首锁）
- **半悬空 0.5**——一真一假 → 按块
  计比率
- **错误通道旁路**——error dict
  {"code": "parse_failed"} 直传 →
  element/locator 指标照算不置
  null，error_code 原样回显
  "parse_failed"（metrics 不因
  error 短路首锁）
- **hbc 分母是题**——[heading+para]
  与 [para] 两块 → 1.0（纯段块不
  进分母，hbc 只数 heading 元素是
  否居块首）
- forbidden tokens 第六百八十八批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _el(eid, etype, loc):
    return {"element_id": eid, "type": etype, "content": "c",
            "source_locator": loc, "metadata": {}}


def _doc(els, chunks):
    return {"source_type": "pdf", "elements": els, "chunks": chunks}


_H = {"page": 1, "bbox": [1, 2, 3, 4]}


# ---------- 悬空引用算 intact ----------

def test_dangling_ref_intact_zero_batch416():
    els = [_el("e0", "paragraph", _H)]
    chunks = [{"chunk_id": "c0", "text": "c",
               "source_element_ids": ["nope"], "metadata": {}}]
    m = compute_automatic_metrics(_doc(els, chunks), None, "pdf",
                                  None)
    assert m["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


def test_half_dangling_intact_batch416():
    els = [_el("e0", "paragraph", _H)]
    chunks = [
        {"chunk_id": "c0", "text": "c",
         "source_element_ids": ["e0"], "metadata": {}},
        {"chunk_id": "c1", "text": "c",
         "source_element_ids": ["nope"], "metadata": {}},
    ]
    m = compute_automatic_metrics(_doc(els, chunks), None, "pdf",
                                  None)
    assert m["chunk_reference_intact_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- 错误通道旁路 ----------

def test_error_channel_metrics_still_computed_batch416():
    els = [_el("e0", "paragraph", _H)]
    m = compute_automatic_metrics(
        _doc(els, []), {"code": "parse_failed", "message": "x"},
        "pdf", None)
    assert m["element_count_total"] == {"value": 1,
                                        "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


def test_error_code_echoed_batch416():
    els = [_el("e0", "paragraph", _H)]
    m = compute_automatic_metrics(
        _doc(els, []), {"code": "parse_failed", "message": "x"},
        "pdf", None)
    assert m["error_code"] == {"value": "parse_failed",
                               "reason": None}


# ---------- hbc 分母是题 ----------

def test_hbc_para_chunk_immune_batch416():
    els = [
        _el("e0", "heading", _H),
        _el("e1", "paragraph", _H),
        _el("e2", "paragraph", _H),
    ]
    chunks = [
        {"chunk_id": "c0", "text": "c",
         "source_element_ids": ["e0", "e1"], "metadata": {}},
        {"chunk_id": "c1", "text": "c",
         "source_element_ids": ["e2"], "metadata": {}},
    ]
    m = compute_automatic_metrics(_doc(els, chunks), None, "pdf",
                                  None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_hbc_heading_second_zero_batch416():
    els = [
        _el("e0", "paragraph", _H),
        _el("e1", "heading", _H),
    ]
    chunks = [{"chunk_id": "c0", "text": "c",
               "source_element_ids": ["e0", "e1"], "metadata": {}}]
    m = compute_automatic_metrics(_doc(els, chunks), None, "pdf",
                                  None)
    assert m["heading_boundary_compliance"] == {
        "value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch416():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第六百八十八批 ----------

def test_source_no_eval_batch416():
    assert "eval(" not in _src()


def test_source_no_exec_batch416():
    assert "exec(" not in _src()


def test_source_no_compile_batch416():
    assert "compile(" not in _src()


def test_source_no_globals_batch416():
    assert "globals(" not in _src()


def test_source_no_locals_batch416():
    assert "locals(" not in _src()


def test_source_no_os_system_batch416():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch416():
    assert "subprocess" not in _src()


def test_source_no_popen_batch416():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch416():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch416():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch416():
    assert "socket" not in _src()


def test_source_no_requests_batch416():
    assert "requests" not in _src()


def test_source_no_urllib_batch416():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch416():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch416():
    assert "yield" not in _src()


def test_source_no_async_await_batch416():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch416():
    assert "open(" not in _src()
