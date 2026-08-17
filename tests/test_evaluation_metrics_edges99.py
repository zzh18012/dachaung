"""evaluation/metrics.py 第二百八十六轮 edges 测试（Round 842）。

补强 edges98 未触及的角度（第二百一十六批）。

新角度：
- page 传 float 1.5 → isinstance(int) 不成立 → 0.0
  （bool 渗漏已测，float 不渗漏）
- bbox 含 float("inf") → math.isfinite 拦截 → 0.0
- bbox 四个纯 float → 合法 1.0
- 图片空文件（存在但 0 字节）→ st_size>0 拦截 → 0.0
- 两图一实一空 → 0.5
- source_element_ids 引用不存在 id → 0.0
- docx locator 仅 relationship_id → 结构键命中 1.0
- docx locator 空 dict {} → 无结构键 0.0
- elements 显式 None → len(None) TypeError（现状记录）
- forbidden tokens 第三百一十二批
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


def _cam(document, st="pdf", exp=None, base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, None, st, exp, base)


def _pdf_el(eid, t="paragraph", **loc_over):
    loc = {"page": 1, "bbox": [0.0, 0.0, 10.0, 10.0]}
    loc.update(loc_over)
    return _el(eid, t, source_locator=loc)


# ---------- page float ----------

def test_page_float_invalid_batch55():
    m = _cam(_doc([_pdf_el("e1", page=1.5)]))
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- bbox inf ----------

def test_bbox_inf_invalid_batch55():
    m = _cam(_doc([_pdf_el(
        "e1", bbox=[1.0, 2.0, 3.0, float("inf")])]))
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


def test_bbox_all_floats_valid_batch55():
    m = _cam(_doc([_pdf_el(
        "e1", bbox=[0.5, 1.5, 2.5, 3.5])]))
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 图片实存 ----------

def _img(eid, rp):
    return _el(eid, "image", content=None, resource_path=rp,
               source_locator={"page": 1})


def test_image_empty_file_zero_batch55(tmp_path):
    (tmp_path / "a.png").write_bytes(b"")
    m = _cam(_doc([_img("i1", str(tmp_path / "a.png"))]),
             base=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


def test_image_mixed_half_batch55(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"")
    m = _cam(_doc([_img("i1", str(tmp_path / "a.png")),
                   _img("i2", str(tmp_path / "b.png"))]),
             base=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- ghost 引用 ----------

def test_ghost_reference_zero_batch55():
    els = [_el("p1", "paragraph")]
    m = _cam(_doc(els, [{"source_element_ids": ["ghost"]}]))
    assert m["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- docx 结构键 ----------

def test_docx_relationship_id_only_batch55():
    els = [_el("e1", "paragraph",
               source_locator={"relationship_id": "rId7"})]
    m = _cam(_doc(els), st="docx")
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


def test_docx_empty_locator_zero_batch55():
    els = [_el("e1", "paragraph", source_locator={})]
    m = _cam(_doc(els), st="docx")
    assert m["docx_locator_valid_ratio"] == {"value": 0.0,
                                             "reason": None}


# ---------- elements None ----------

def test_elements_none_typeerror_batch55():
    try:
        _cam({"elements": None, "chunks": []})
        raise AssertionError("no error")
    except TypeError as e:
        assert "len" in str(e) or "NoneType" in str(e)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "if not isinstance(page, int) or page < 1:" in src
    assert "if not math.isfinite(v):" in src
    assert "if p.is_file() and p.stat().st_size > 0:" in src


# ---------- forbidden tokens 第三百一十二批 ----------

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
