"""evaluation/metrics.py 第二百六十五轮 edges 测试（Round 821）。

补强 edges95 未触及的角度（第一百九十二批）。

新角度：
- _TEXT_TYPES 全员参与文本比对：paragraph + header + table +
  list_item + caption + footer 六类拼接 "ABCDEF" 与单 chunk
  全等（与 image 排除相对照的正向清单）
- 元素无 source_locator 键 → `or {}` → page None → 0.0
- bbox 内含 bool [1,2,3,True] → _is_valid_bbox 显式拒 →
  段落 0.0（bool 是 int 子类，靠 isinstance(v, bool) 先拦）
- docx locator 含 bbox 键（值合法）→ 键存在即拒 → 0.0
- chunk 无 text 键 → `or ""` → actual 空 → equal False +
  precision null empty_actual + recall 0.0
- forbidden tokens 第二百九十一批
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


def _cam(document, st="pdf"):
    with patch.object(sv, "document_passes_schema", lambda d: True):
        return cam(document, None, st, None)


# ---------- _TEXT_TYPES 全员 ----------

def test_all_text_types_participate_batch55():
    els = [_el("e1", "paragraph", content="A"),
           _el("e2", "header", content="B"),
           _el("e3", "table", content="C"),
           _el("e4", "list_item", content="D"),
           _el("e5", "caption", content="E"),
           _el("e6", "footer", content="F")]
    chs = [{"text": "ABCDEF", "source_element_ids": ["e1"]}]
    m = _cam(_doc(els, chs))
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {"value": 1.0,
                                              "reason": None}


# ---------- 无 locator ----------

def test_element_without_locator_invalid_batch55():
    m = _cam(_doc([_el("e1", "paragraph")]))
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- bbox 内 bool ----------

def test_bbox_bool_member_rejected_batch55():
    els = [_el("e1", "paragraph",
               source_locator={"page": 1,
                               "bbox": [1, 2, 3, True]})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- docx bbox 键 ----------

def test_docx_bbox_key_rejected_batch55():
    els = [_el("e1", "paragraph",
               source_locator={"section": 1,
                               "bbox": [1, 2, 3, 4]})]
    m = _cam(_doc(els), st="docx")
    assert m["docx_locator_valid_ratio"] == {"value": 0.0,
                                             "reason": None}


# ---------- chunk 无 text 键 ----------

def test_chunk_without_text_key_batch55():
    els = [_el("e1", "paragraph", content="A")]
    chs = [{"source_element_ids": ["e1"]}]
    m = _cam(_doc(els, chs))
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_actual"}
    assert m["text_char_multiset_recall"] == {"value": 0.0,
                                              "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_text_types_tuple_batch55():
    src = _src()
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src
    assert "if isinstance(v, bool):" in src


# ---------- forbidden tokens 第二百九十一批 ----------

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
