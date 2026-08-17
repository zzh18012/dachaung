"""evaluation/metrics.py 第三百四十轮 edges 测试（Round 896）。

补强 edges105 未触及的角度（第二百七十二批，probe 实证）。

新角度：
- heading element_id None 与 chunk 首引用 None 互相匹配 → 1.0；
  首引用 'e9' 则 0.0
- docx locator 含 page=None（键存在即无效，不看值）→ 0.0
- 元素缺 type 键 → element_count_by_type 落 "unknown" 桶
- pdf 元素无 source_locator → 0.0（elements 非空不 null）
- _is_valid_bbox 矩阵：bool 混入 / inf / 字符串 / 浮点合法
- chunk source_element_ids [] → 不算 valid 但计分母 → 0.5
- 重复 element_id 集合去重后仍匹配
- 空白差异 equal：expected "A  B\n" vs actual "AB" → True + P=R=1.0
- expectations 计数值为字符串 → TypeError 未防护
- forbidden tokens 第三百六十六批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import _is_valid_bbox, compute_automatic_metrics


def _el(eid, etype, content="A", **kw):
    e = {"element_id": eid, "type": etype, "content": content}
    e.update(kw)
    return e


# ---------- heading None 匹配 ----------

def test_heading_none_id_matches_none_first_batch94():
    doc = {"elements": [_el(None, "heading")],
           "chunks": [{"text": "A",
                       "source_element_ids": [None]}]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["heading_boundary_compliance"] == {"value": 1.0,
                                                "reason": None}


def test_heading_none_id_vs_real_first_batch94():
    doc = {"elements": [_el(None, "heading")],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e9"]}]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["heading_boundary_compliance"] == {"value": 0.0,
                                                "reason": None}


# ---------- docx page=None 键存在 ----------

def test_docx_page_none_key_invalid_batch94():
    doc = {"elements": [_el(
        "e1", "paragraph",
        source_locator={"page": None, "paragraph_index": 0})],
        "chunks": []}
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"] == {"value": 0.0,
                                             "reason": None}


# ---------- unknown 桶 ----------

def test_by_type_unknown_bucket_batch94():
    doc = {"elements": [{"element_id": "e1", "content": "A"}],
           "chunks": []}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["element_count_by_type"] == {"value": {"unknown": 1},
                                          "reason": None}


# ---------- pdf 无 locator ----------

def test_pdf_no_locator_ratio_zero_batch94():
    doc = {"elements": [_el("e1", "paragraph")], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- bbox 矩阵 ----------

@pytest.mark.parametrize("bbox,ok", [
    ([1, 2, 3, 4], True),
    ([0.5, 1.5, 2.5, 3.5], True),
    ([1, 2, True, 4], False),          # bool 混入
    ([1, 2, 3, float("inf")], False),  # 非有限数
    ([1, 2, 3, "4"], False),           # 字符串
    ((1, 2, 3, 4), False),             # tuple 非 list
    ([1, 2, 3], False),                # 长度 3
])
def test_is_valid_bbox_matrix_batch94(bbox, ok):
    assert _is_valid_bbox(bbox) is ok


# ---------- chunk 引用 ----------

def test_chunk_ref_empty_ids_half_batch94():
    doc = {"elements": [_el("e1", "paragraph")],
           "chunks": [
               {"text": "A", "source_element_ids": ["e1"]},
               {"text": "B", "source_element_ids": []},
           ]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["chunk_reference_intact_ratio"] == {"value": 0.5,
                                                 "reason": None}


def test_chunk_ref_duplicate_elem_ids_batch94():
    doc = {"elements": [_el("e1", "paragraph"), _el("e1", "paragraph")],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1", "e1"]}]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["chunk_reference_intact_ratio"] == {"value": 1.0,
                                                 "reason": None}


# ---------- 空白差异 equal ----------

def test_text_preservation_whitespace_equal_batch94():
    doc = {"elements": [_el("e1", "paragraph", "A  B\n")],
           "chunks": [{"text": "AB",
                       "source_element_ids": ["e1"]}]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["text_preservation_equal"] is not None
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"] == {"value": 1.0,
                                                 "reason": None}
    assert m["text_char_multiset_recall"] == {"value": 1.0,
                                              "reason": None}


# ---------- expectations 字符串值 ----------

def test_silent_drop_string_value_typeerror_batch94():
    doc = {"elements": [_el("e1", "paragraph")], "chunks": []}
    with pytest.raises(TypeError):
        compute_automatic_metrics(
            doc, None, "text",
            {"element_count_by_type": {"paragraph": "3"}})


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch94():
    src = _src()
    assert 'metrics["element_count_by_type"] = {"value": by_type, "reason": None}' in src
    assert 't = e.get("type", "unknown")' in src
    assert 'if "page" in loc or "bbox" in loc:' in src
    assert "chunk_first_ids.add(ids[0])" in src


# ---------- forbidden tokens 第三百六十六批 ----------

def test_source_no_eval_batch94():
    assert "eval(" not in _src()


def test_source_no_exec_batch94():
    assert "exec(" not in _src()


def test_source_no_compile_batch94():
    assert "compile(" not in _src()


def test_source_no_globals_batch94():
    assert "globals(" not in _src()


def test_source_no_locals_batch94():
    assert "locals(" not in _src()


def test_source_no_os_system_batch94():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch94():
    assert "subprocess" not in _src()


def test_source_no_popen_batch94():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch94():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch94():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch94():
    assert "socket" not in _src()


def test_source_no_requests_batch94():
    assert "requests" not in _src()


def test_source_no_urllib_batch94():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch94():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch94():
    assert "yield" not in _src()


def test_source_no_async_await_batch94():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch94():
    assert "open(" not in _src()
