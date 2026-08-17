"""evaluation/metrics.py 第四百六十一轮 edges 测试（Round 1017）。

补强 edges122 未触及的角度（第三百九十三批，probe 实证）。

新角度：
- 七文本类型 page-only locator 矩阵：bbox 豁免 3 类
  （table/header/footer）合规 + 强制 4 类（heading/
  paragraph/caption/list_item）不合规 → pdf_locator
  精确 3/7（0.42857142857142855）
- expectations.element_count_by_type 含 None 值 →
  actual < exp 直接 TypeError（无守卫，现状记录；
  edges83 记过 chunks None / error 缺 code，此为第三个
  未守卫路径）
- heading 在 chunk 的第二个位置（ids[1] 非 ids[0]）→
  heading_boundary 0.0（首元素规则；edges100 锁过
  "第二 chunk 的首元素 1.0"，此处是同 chunk 内第二位）
- forbidden tokens 第四百八十七批（open 0）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


# ---------- 七类型矩阵 ----------

def test_seven_type_matrix_three_sevenths_batch215():
    types = ["heading", "paragraph", "caption", "list_item",
             "table", "header", "footer"]
    els = [{"type": t, "element_id": f"e{i}",
            "source_locator": {"page": 1}}
           for i, t in enumerate(types)]
    m = compute_automatic_metrics({"elements": els}, None, "pdf",
                                  None)
    assert (m["pdf_locator_valid_ratio"]["value"]
            == 3 / 7)
    assert m["pdf_locator_valid_ratio"]["value"] == \
        0.42857142857142855


# ---------- expectations None 值 ----------

def test_expectations_none_count_typeerror_batch215():
    with pytest.raises(TypeError, match="'<' not supported"):
        compute_automatic_metrics(
            {"elements": [], "chunks": []}, None, "pdf",
            {"element_count_by_type": {"paragraph": None}})


# ---------- heading 同 chunk 第二位 ----------

def test_heading_second_position_zero_batch215():
    els = [
        {"type": "heading", "element_id": "h1", "content": "H",
         "source_locator": {"page": 1}},
        {"type": "paragraph", "element_id": "p1",
         "content": "P",
         "source_locator": {"page": 1,
                            "bbox": [0, 0, 1, 1]}}]
    chunks = [{"chunk_id": "c1", "text": "PH",
               "source_element_ids": ["p1", "h1"],
               "char_count": 2}]
    m = compute_automatic_metrics(
        {"elements": els, "chunks": chunks}, None, "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch215():
    src = _src()
    assert ('matched = sum(1 for h in headings'
            ' if h.get("element_id") in chunk_first_ids)') in src
    assert "if actual < exp:" in src
    assert "by_type[t] = by_type.get(t, 0) + 1" in src


# ---------- forbidden tokens 第四百八十七批 ----------

def test_source_no_eval_batch215():
    assert "eval(" not in _src()


def test_source_no_exec_batch215():
    assert "exec(" not in _src()


def test_source_no_compile_batch215():
    assert "compile(" not in _src()


def test_source_no_globals_batch215():
    assert "globals(" not in _src()


def test_source_no_locals_batch215():
    assert "locals(" not in _src()


def test_source_no_os_system_batch215():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch215():
    assert "subprocess" not in _src()


def test_source_no_popen_batch215():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch215():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch215():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch215():
    assert "socket" not in _src()


def test_source_no_requests_batch215():
    assert "requests" not in _src()


def test_source_no_urllib_batch215():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch215():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch215():
    assert "yield" not in _src()


def test_source_no_async_await_batch215():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch215():
    assert "open(" not in _src()
