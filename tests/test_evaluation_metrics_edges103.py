"""evaluation/metrics.py 第三百一十四轮 edges 测试（Round 870）。

补强 edges102 未触及的角度（第二百四十五批）。

新角度：
- 多 heading 多 chunk：全部对齐 1.0 / 部分对齐 0.5
- resource_path 指向目录（存在但非文件）→ 无效
- image 元素 resource_path None → 无效
- silent_drop 多类型混合：只累计缺口（超额不抵扣）
- expectations 传 truthy 字符串 → AttributeError（现状锁定）
- document 与 error 同时给出：pipeline_success False 但
  指标照常按 document 计算
- 文本多集合："aab" vs "abb" → equal False、P=R=2/3
- forbidden tokens 第三百四十批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, error=None, st="pdf", exp=None, base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, error, st, exp, base)


# ---------- 多 heading ----------

def test_two_headings_all_aligned_batch68(tmp_path):
    els = [_el("h1", "heading"), _el("h2", "heading")]
    chunks = [
        {"text": "A", "source_element_ids": ["h1"]},
        {"text": "B", "source_element_ids": ["h2"]}]
    m = _cam(_doc(els, chunks))
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_two_headings_partial_batch68(tmp_path):
    els = [_el("h1", "heading"), _el("h2", "heading")]
    chunks = [
        {"text": "AB", "source_element_ids": ["h1", "h2"]}]
    m = _cam(_doc(els, chunks))
    assert m["heading_boundary_compliance"] == {
        "value": 0.5, "reason": None}


# ---------- resource_path 异常 ----------

def test_resource_path_directory_invalid_batch68(tmp_path):
    (tmp_path / "d.png").mkdir()
    els = [_el("e1", "image", resource_path=str(
        tmp_path / "d.png"))]
    m = _cam(_doc(els))
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


def test_resource_path_none_invalid_batch68():
    els = [_el("e1", "image", resource_path=None)]
    m = _cam(_doc(els))
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- silent_drop 多类型 ----------

def test_silent_drop_multi_type_deficit_only_batch68():
    els = [_el("e1", "paragraph", content="A"),
           _el("e2", "paragraph", content="B"),
           _el("e3", "paragraph", content="C"),
           _el("e4", "paragraph", content="D"),
           _el("e5", "paragraph", content="E")]
    m = _cam(_doc(els),
             exp={"element_count_by_type": {
                 "paragraph": 3, "heading": 2}})
    assert m["silent_drop_count"] == {"value": 2,
                                      "reason": None}


# ---------- expectations 非字典 ----------

def test_expectations_string_attribute_error_batch68():
    try:
        _cam(_doc([_el("e1", "paragraph")]), exp="xy")
        raise AssertionError("no error")
    except AttributeError as e:
        assert "'str' object has no attribute 'get'" \
            in str(e)


# ---------- document + error 并存 ----------

def test_document_with_error_computed_batch68():
    m = _cam(_doc([_el("e1", "paragraph")]),
             error={"code": "E_X", "message": "m"})
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["error_code"] == {"value": "E_X",
                               "reason": None}
    assert m["element_count_total"] == {"value": 1,
                                        "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 1}, "reason": None}


# ---------- 文本多集合 ----------

def test_multiset_aab_vs_abb_batch68():
    els = [_el("e1", "paragraph", content="aab")]
    m = _cam(_doc(els, [{"text": "abb",
                         "source_element_ids": ["e1"]}]))
    assert m["text_preservation_equal"] == {
        "value": False, "reason": None}
    assert m["text_char_multiset_precision"]["value"] == \
        pytest.approx(2 / 3)
    assert m["text_char_multiset_recall"]["value"] == \
        pytest.approx(2 / 3)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch68():
    src = _src()
    assert 'matched = sum(1 for h in headings if h.get("element_id") in chunk_first_ids)' in src
    assert "if not rp:" in src
    assert "drops += (exp - actual)" in src


# ---------- forbidden tokens 第三百四十批 ----------

def test_source_no_eval_batch68():
    assert "eval(" not in _src()


def test_source_no_exec_batch68():
    assert "exec(" not in _src()


def test_source_no_compile_batch68():
    assert "compile(" not in _src()


def test_source_no_globals_batch68():
    assert "globals(" not in _src()


def test_source_no_locals_batch68():
    assert "locals(" not in _src()


def test_source_no_os_system_batch68():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch68():
    assert "subprocess" not in _src()


def test_source_no_popen_batch68():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch68():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch68():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch68():
    assert "socket" not in _src()


def test_source_no_requests_batch68():
    assert "requests" not in _src()


def test_source_no_urllib_batch68():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch68():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch68():
    assert "yield" not in _src()


def test_source_no_async_await_batch68():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch68():
    assert "open(" not in _src()
