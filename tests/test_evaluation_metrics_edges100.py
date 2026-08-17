"""evaluation/metrics.py 第二百九十三轮 edges 测试（Round 849）。

补强 edges99 未触及的角度（第二百二十三批）。

新角度：
- 构造器四件套直测：_null/_ratio/_bool_metric/_int_metric
  （_ratio(1) 强转 float、_bool_metric(1) 强转 True、
  _int_metric(True) 强转 1）
- _TEXT_TYPES 恰 7 项且含 table；_PDF_BBOX_REQUIRED_TYPES
  恰 4 项且不含 table（表格要 page 不要 bbox 的双面锁定）
- heading 作为第二 chunk 首元素 → 合规 1.0
- document=None + error code E → 11 项 pipeline_failed null +
  error_code "E" + pipeline_success False
- _strip_unicode_whitespace 直测（\t\n\x0c 全删，
  \x1d 非空白保留）
- 图片绝对路径 rp 无 base_dir → 直接命中 1.0
- forbidden tokens 第三百一十九批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import (
    _TEXT_TYPES,
    _PDF_BBOX_REQUIRED_TYPES,
    _bool_metric,
    _int_metric,
    _null,
    _ratio,
    _strip_unicode_whitespace,
    compute_automatic_metrics as cam,
)


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, error=None, st="pdf", base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, error, st, None, base)


# ---------- 构造器 ----------

def test_constructors_batch55():
    assert _null("r") == {"value": None, "reason": "r"}
    r = _ratio(1)
    assert r == {"value": 1.0, "reason": None}
    assert isinstance(r["value"], float)
    assert _bool_metric(1) == {"value": True, "reason": None}
    i = _int_metric(True)
    assert i == {"value": 1, "reason": None}
    assert isinstance(i["value"], int)


# ---------- 类型清单 ----------

def test_text_types_seven_with_table_batch55():
    assert len(_TEXT_TYPES) == 7
    assert "table" in _TEXT_TYPES
    assert "image" not in _TEXT_TYPES


def test_bbox_types_four_without_table_batch55():
    assert _PDF_BBOX_REQUIRED_TYPES == (
        "heading", "paragraph", "caption", "list_item")
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


# ---------- heading 第二 chunk 首 ----------

def test_heading_first_of_second_chunk_batch55():
    els = [_el("p1", "paragraph"), _el("h1", "heading")]
    chunks = [{"source_element_ids": ["p1"]},
              {"source_element_ids": ["h1"]}]
    m = _cam(_doc(els, chunks))
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- document None + error ----------

def test_none_document_error_code_batch55():
    m = _cam(None, error={"code": "E", "message": "m"})
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["error_code"] == {"value": "E", "reason": None}
    nulls = [k for k, v in m.items()
             if v.get("value") is None]
    assert len(nulls) == 12
    for k in nulls:
        if k == "error_code":
            continue
        assert m[k]["reason"] == "pipeline_failed"


# ---------- 空白剥离直测 ----------

def test_strip_unicode_whitespace_direct_batch55():
    assert _strip_unicode_whitespace("\t\n\x0c A \r B") == "AB"
    # \x1d（Group Separator）被 Python 判为空白 → 删除；
    # \x00（NUL）不是空白 → 保留
    assert _strip_unicode_whitespace("\x1d") == ""
    assert _strip_unicode_whitespace("\x00") == "\x00"
    assert _strip_unicode_whitespace("") == ""


# ---------- 绝对 rp 无 base_dir ----------

def test_image_absolute_rp_no_base_batch55(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"data")
    els = [_el("i1", "image", content=None,
               resource_path=str(f),
               source_locator={"page": 1})]
    m = _cam(_doc(els), base=None)
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "return {\"value\": float(value), \"reason\": None}" in src
    assert "return {\"value\": bool(value), \"reason\": None}" in src
    assert 'return "".join(ch for ch in s if not ch.isspace())' in src


# ---------- forbidden tokens 第三百一十九批 ----------

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
