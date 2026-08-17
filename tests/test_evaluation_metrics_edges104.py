"""evaluation/metrics.py 第三百二十一轮 edges 测试（Round 877）。

补强 edges103 未触及的角度（第二百五十二批）。

新角度：
- image 比例分母只数 image 元素（paragraph 不掺和）
- 双方 element_id 均缺失：chunk 引 [None] 对元素集
  {None} → 计为有效（现状锁定）
- _int_metric(2.9) → 2（float 截断）
- source_type "txt"：pdf 与 docx locator 双 null
- _strip_unicode_whitespace：\\x0b（垂直制表符）也删
- 期望 0 的类型不产生 silent_drop
- forbidden tokens 第三百四十七批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import (
    _int_metric,
    _strip_unicode_whitespace,
    compute_automatic_metrics as cam,
)


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, st="pdf", exp=None, base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, None, st, exp, base)


# ---------- image 分母 ----------

def test_image_ratio_denominator_images_only_batch75(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"xx")
    els = [_el("e1", "paragraph"),
           _el("e2", "image",
               resource_path=str(img))]
    m = _cam(_doc(els), base=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 双缺失 id ----------

def test_none_element_id_reference_quirk_batch75():
    els = [{"type": "paragraph", "content": "A"}]
    chunks = [{"text": "A",
               "source_element_ids": [None]}]
    m = _cam(_doc(els, chunks))
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 构造器 ----------

def test_int_metric_float_truncates_batch75():
    assert _int_metric(2.9) == {"value": 2, "reason": None}
    assert _int_metric(-0.9) == {"value": 0, "reason": None}


# ---------- 非 pdf/docx ----------

def test_source_type_txt_both_null_batch75():
    m = _cam(_doc([_el("e1", "paragraph")]), st="txt")
    assert m["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


# ---------- 垂直制表符 ----------

def test_strip_vertical_tab_batch75():
    assert _strip_unicode_whitespace("A\t\n B\x0bC") == "ABC"


# ---------- 期望 0 ----------

def test_zero_expectation_no_drop_batch75():
    m = _cam(_doc([_el("e1", "paragraph")]),
             exp={"element_count_by_type": {
                 "paragraph": 0, "heading": 0}})
    assert m["silent_drop_count"] == {"value": 0,
                                      "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch75():
    src = _src()
    assert 'images = [e for e in elements if e.get("type") == "image"]' in src
    assert "elem_ids = {e.get(\"element_id\") for e in elements}" in src
    assert 'return "".join(ch for ch in s if not ch.isspace())' in src


# ---------- forbidden tokens 第三百四十七批 ----------

def test_source_no_eval_batch75():
    assert "eval(" not in _src()


def test_source_no_exec_batch75():
    assert "exec(" not in _src()


def test_source_no_compile_batch75():
    assert "compile(" not in _src()


def test_source_no_globals_batch75():
    assert "globals(" not in _src()


def test_source_no_locals_batch75():
    assert "locals(" not in _src()


def test_source_no_os_system_batch75():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch75():
    assert "subprocess" not in _src()


def test_source_no_popen_batch75():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch75():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch75():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch75():
    assert "socket" not in _src()


def test_source_no_requests_batch75():
    assert "requests" not in _src()


def test_source_no_urllib_batch75():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch75():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch75():
    assert "yield" not in _src()


def test_source_no_async_await_batch75():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch75():
    assert "open(" not in _src()
