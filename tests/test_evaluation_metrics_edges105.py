"""evaluation/metrics.py 第三百二十八轮 edges 测试（Round 884）。

补强 edges104 未触及的角度（第二百五十九批）。

新角度：
- resource_path 空串：falsy → 跳过；与有效图片混合 → 0.5
- 非文本元素类型（table/list_item）都参与文本保留
- 期望值为 bool True：0 个实际 → drops += True-0，
  int(True)=1（现状锁定）
- document 缺 chunks 键：chunk_reference null
  no_chunks + recall 0.0 / precision null empty_actual
- forbidden tokens 第三百五十四批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam


def _doc(elements, chunks=None):
    d = {"elements": elements}
    if chunks is not None:
        d["chunks"] = chunks
    return d


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, st="pdf", exp=None, base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, None, st, exp, base)


# ---------- 空 rp 混合 ----------

def test_empty_rp_mixed_half_batch82(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"xx")
    els = [_el("e1", "image", resource_path=str(img)),
           _el("e2", "image", resource_path="")]
    m = _cam(_doc(els), base=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- 非文本类型参与保留 ----------

def test_table_list_item_in_text_batch82():
    els = [_el("e1", "table", content="T"),
           _el("e2", "list_item", content="L")]
    m = _cam(_doc(els, [{"text": "TL",
                         "source_element_ids": ["e1"]}]))
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["element_count_by_type"]["value"] == {
        "table": 1, "list_item": 1}


# ---------- 期望 bool ----------

def test_bool_expectation_drop_batch82():
    m = _cam(_doc([]),
             exp={"element_count_by_type": {"paragraph": True}})
    assert m["silent_drop_count"] == {"value": 1,
                                      "reason": None}


# ---------- 缺 chunks 键 ----------

def test_missing_chunks_key_batch82():
    m = _cam(_doc([_el("e1", "paragraph")]))
    assert m["chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"}
    assert m["text_preservation_equal"] == {
        "value": False, "reason": None}
    assert m["text_char_multiset_precision"]["reason"] == \
        "empty_actual"
    assert m["text_char_multiset_recall"] == {
        "value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch82():
    src = _src()
    assert "if not chunks:" in src
    assert "if not rp:" in src
    assert "drops += (exp - actual)" in src


# ---------- forbidden tokens 第三百五十四批 ----------

def test_source_no_eval_batch82():
    assert "eval(" not in _src()


def test_source_no_exec_batch82():
    assert "exec(" not in _src()


def test_source_no_compile_batch82():
    assert "compile(" not in _src()


def test_source_no_globals_batch82():
    assert "globals(" not in _src()


def test_source_no_locals_batch82():
    assert "locals(" not in _src()


def test_source_no_os_system_batch82():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch82():
    assert "subprocess" not in _src()


def test_source_no_popen_batch82():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch82():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch82():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch82():
    assert "socket" not in _src()


def test_source_no_requests_batch82():
    assert "requests" not in _src()


def test_source_no_urllib_batch82():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch82():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch82():
    assert "yield" not in _src()


def test_source_no_async_await_batch82():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch82():
    assert "open(" not in _src()
