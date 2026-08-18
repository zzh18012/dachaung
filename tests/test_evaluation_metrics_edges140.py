"""evaluation/metrics.py 第五百六十一轮 edges 测试（Round 1225）。

补强 edges139 未触及的角度（第五百九十七批，probe 实证）。

新角度（字符多重集对称 / 顺序无关与保序对照）：
- **顺序无关**——元素 "AB"+"CD"
  vs 块文本 "DCBA" → multiset
  P/R 双 1.0 而 text_preservation
  False（多重集只数频次，保序另
  算首锁）
- **块多字符**——"AB" vs "ABX" →
  P 2/3 / R 1.0（分母是块侧字符
  数）
- **块缺字符**——"ABX" vs "AB" →
  P 1.0 / R 2/3（分母换成元素侧）
- **重复字符换位**——"AABB" vs
  "ABAB" → 双 1.0 + pres False
- **空文档**——0 元素 → ect 0（非
  null）/ pres True（空对空相等）
- forbidden tokens 第六百九十四批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _el(eid, etype, loc):
    return {"element_id": eid, "type": etype, "content": "c",
            "source_locator": loc, "metadata": {}}


_H = {"page": 1, "bbox": [1, 2, 3, 4]}


def _doc(contents, chunk_texts):
    els = []
    for i, c in enumerate(contents):
        e = _el("e%d" % i, "paragraph", _H)
        e["content"] = c
        els.append(e)
    chunks = [{"chunk_id": "c%d" % i, "text": t,
               "source_element_ids": ["e0"], "metadata": {}}
              for i, t in enumerate(chunk_texts)]
    return {"source_type": "pdf", "elements": els,
            "chunks": chunks}


def _doc_single(content, chunk_text):
    els = [_el("e0", "paragraph", _H)]
    els[0]["content"] = content
    chunks = [{"chunk_id": "c0", "text": chunk_text,
               "source_element_ids": ["e0"], "metadata": {}}]
    return {"source_type": "pdf", "elements": els,
            "chunks": chunks}


# ---------- 顺序无关 ----------

def test_multiset_order_insensitive_batch423():
    els = [_el("e0", "paragraph", _H), _el("e1", "paragraph", _H)]
    els[0]["content"] = "AB"
    els[1]["content"] = "CD"
    chunks = [{"chunk_id": "c0", "text": "DCBA",
               "source_element_ids": ["e0", "e1"],
               "metadata": {}}]
    m = compute_automatic_metrics(
        {"source_type": "pdf", "elements": els,
         "chunks": chunks}, None, "pdf", None)
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {
        "value": False, "reason": None}


# ---------- 块多字符 ----------

def test_multiset_chunk_extra_batch423():
    m = compute_automatic_metrics(
        _doc_single("AB", "ABX"), None, "pdf", None)
    assert m["text_char_multiset_precision"] == {
        "value": 0.6666666666666666, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 块缺字符 ----------

def test_multiset_chunk_missing_batch423():
    m = compute_automatic_metrics(
        _doc_single("ABX", "AB"), None, "pdf", None)
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 重复字符换位 ----------

def test_multiset_dupes_swapped_batch423():
    m = compute_automatic_metrics(
        _doc_single("AABB", "ABAB"), None, "pdf", None)
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {
        "value": False, "reason": None}


# ---------- 空文档 ----------

def test_empty_doc_counts_zero_batch423():
    m = compute_automatic_metrics(
        {"source_type": "pdf", "elements": [], "chunks": []},
        None, "pdf", None)
    assert m["element_count_total"] == {"value": 0,
                                        "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch423():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第六百九十四批 ----------

def test_source_no_eval_batch423():
    assert "eval(" not in _src()


def test_source_no_exec_batch423():
    assert "exec(" not in _src()


def test_source_no_compile_batch423():
    assert "compile(" not in _src()


def test_source_no_globals_batch423():
    assert "globals(" not in _src()


def test_source_no_locals_batch423():
    assert "locals(" not in _src()


def test_source_no_os_system_batch423():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch423():
    assert "subprocess" not in _src()


def test_source_no_popen_batch423():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch423():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch423():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch423():
    assert "socket" not in _src()


def test_source_no_requests_batch423():
    assert "requests" not in _src()


def test_source_no_urllib_batch423():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch423():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch423():
    assert "yield" not in _src()


def test_source_no_async_await_batch423():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch423():
    assert "open(" not in _src()
