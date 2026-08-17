"""evaluation/metrics.py 第三百轮 edges 测试（Round 856）。

补强 edges100 未触及的角度（第二百三十批）。

新角度：
- 成功路径 error_code 为 {"value": None, "reason": None}
- page 传字符串 "1" → isinstance(int) 不成立 → 0.0
  （bool/float/string 三种非 int 全挡）
- source_element_ids 传字符串 "e1"：truthy → all() 逐字符
  迭代 → 'e' 不在集合 → 0.0（现状记录）
- expectations element_count_by_type 值为字符串 "2" →
  int < str TypeError（现状记录）
- document 带无关额外键不影响计算
- elements 空 → element_count_total 0 非 null +
  by_type 空 dict
- forbidden tokens 第三百二十六批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam


def _doc(elements, chunks=()):
    d = {"elements": elements, "chunks": list(chunks)}
    return d


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, st="pdf", exp=None, base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, None, st, exp, base)


# ---------- error_code 成功 ----------

def test_error_code_null_on_success_batch55():
    m = _cam(_doc([_el("e1", "paragraph")]))
    assert m["error_code"] == {"value": None, "reason": None}


# ---------- page 字符串 ----------

def test_page_string_invalid_batch55():
    els = [_el("e1", "paragraph",
               source_locator={"page": "1",
                               "bbox": [0, 0, 1, 1]})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- ids 字符串 ----------

def test_ids_string_char_iteration_batch55():
    els = [_el("e1", "paragraph")]
    m = _cam(_doc(els, [{"source_element_ids": "e1"}]))
    assert m["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- silent_drop 字符串期望 ----------

def test_silent_drop_string_expectation_typeerror_batch55():
    try:
        _cam(_doc([_el("e1", "paragraph")]),
             exp={"element_count_by_type": {"paragraph": "2"}})
        raise AssertionError("no error")
    except TypeError as e:
        assert "'<' not supported" in str(e)


# ---------- 额外键 ----------

def test_document_extra_keys_ignored_batch55():
    doc = _doc([_el("e1", "paragraph")],
               [{"source_element_ids": ["e1"]}])
    doc["unrelated"] = {"deep": [1, 2, 3]}
    m = _cam(doc)
    assert m["pipeline_success"] == {"value": True,
                                     "reason": None}
    assert m["element_count_total"] == {"value": 1,
                                        "reason": None}


# ---------- 空元素 ----------

def test_empty_elements_zero_and_empty_dict_batch55():
    m = _cam(_doc([]))
    assert m["element_count_total"] == {"value": 0,
                                        "reason": None}
    assert m["element_count_by_type"] == {"value": {},
                                          "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'metrics["error_code"] = (' in src
    assert 'if actual < exp:' in src
    assert 'metrics["element_count_by_type"] = {"value": by_type, "reason": None}' in src


# ---------- forbidden tokens 第三百二十六批 ----------

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
