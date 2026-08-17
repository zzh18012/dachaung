"""evaluation/metrics.py 第二百七十二轮 edges 测试（Round 828）。

补强 edges96 未触及的角度（第二百零二批）。

新角度：
- 多类型 silent_drop 求和：paragraph 1/2 + heading 0/2 →
  drops 2
- expectations 传 truthy 字符串 "x" → `'str' object has no
  attribute 'get'`（只挡 falsy，不挡非 dict —— 现状记录）
- element_count_by_type 保持首见插入序
  （["paragraph", "heading"]，非字母序）
- image 元素只需 page（不在 _PDF_BBOX_REQUIRED_TYPES）→
  1.0（与 table/header/footer 同族的正向清单补全）
- schema_valid 校验返回 False（非异常）→ {"value": False,
  "reason": None}（false 也能带 null reason）
- forbidden tokens 第二百九十八批
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


def _cam(document, st="pdf", exp=None):
    with patch.object(sv, "document_passes_schema", lambda d: True):
        return cam(document, None, st, exp)


# ---------- 多类型 drop ----------

def test_multi_type_silent_drop_sum_batch55():
    els = [_el("e1", "paragraph"), _el("h1", "heading")]
    m = _cam(_doc(els),
             exp={"element_count_by_type": {
                 "paragraph": 2, "heading": 2}})
    assert m["silent_drop_count"] == {"value": 2, "reason": None}


# ---------- expectations 非 dict ----------

def test_expectations_string_attribute_error_batch55():
    try:
        _cam(_doc([_el("e1", "paragraph")]), exp="x")
        raise AssertionError("no error")
    except AttributeError as e:
        assert "'str' object has no attribute 'get'" in str(e)


# ---------- 首见插入序 ----------

def test_by_type_first_seen_order_batch55():
    els = [_el("e1", "paragraph"), _el("h1", "heading"),
           _el("e2", "paragraph")]
    m = _cam(_doc(els))
    assert list(
        m["element_count_by_type"]["value"].keys()) == [
        "paragraph", "heading"]


# ---------- image 只需 page ----------

def test_image_element_page_only_valid_batch55():
    els = [_el("i1", "image", content=None,
               source_locator={"page": 1})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- schema_valid False ----------

def test_schema_valid_false_null_reason_batch55():
    with patch.object(sv, "document_passes_schema",
                      lambda d: False):
        m = cam(_doc([_el("e1", "paragraph")]), None, "pdf",
                None)
    assert m["schema_valid"] == {"value": False, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "drops += (exp - actual)" in src
    assert "by_type[t] = by_type.get(t, 0) + 1" in src


# ---------- forbidden tokens 第二百九十八批 ----------

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
