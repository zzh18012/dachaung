"""evaluation/metrics.py 第二百零八轮 edges 测试（Round 758）。

补强 edges83-86 未触及的角度（第一百二十二批）。

新角度：
- bbox 无非负约束：[-1, -2.5, -3, -4] 与 mixed [1, 2.5, 3, 4.0] 均
  valid（isfinite 只查有限性）；5 元素拒
- page 边界：0 / -5 invalid，10**20 valid（无上界）
- DOCX 空 locator {} invalid；section-only valid
- element type 传 list → dict 键不可哈希 TypeError（未守卫）
- error dict 无 code 键 → KeyError 'code'（error["code"] 直取）
- expectations 含未知类型键：该类型按 0 实际计 → 全额 drop
  （paragraph 3 实 1 + table 2 实 0 = 4）
- image 的 content 不进 expected 序列（带 content 的 image 被滤掉）
- elements 空但 chunk 引用非空 id → ratio 0.0（非 null）
- heading 存在但 chunk 无 ids → 0.0（非 null）
- 14 个指标键顺序精确（失败路径与成功路径同序）
- forbidden tokens 第二百二十八批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics

_KEY_ORDER = [
    "pipeline_success", "error_code", "schema_valid",
    "element_count_total", "element_count_by_type",
    "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
    "image_resource_exists_ratio", "chunk_reference_intact_ratio",
    "text_preservation_equal", "text_char_multiset_precision",
    "text_char_multiset_recall", "heading_boundary_compliance",
    "silent_drop_count",
]


def _doc(elements, chunks=()):
    return {"elements": list(elements), "chunks": list(chunks)}


def _el(**k):
    return k


# ---------- bbox 约束面 ----------

def test_bbox_negative_values_accepted_batch54():
    d = _doc([_el(type="paragraph",
                  source_locator={"page": 1, "bbox": [-1, -2.5, -3, -4]})])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0, "reason": None}


def test_bbox_mixed_int_float_accepted_batch54():
    d = _doc([_el(type="paragraph",
                  source_locator={"page": 1, "bbox": [1, 2.5, 3, 4.0]})])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0, "reason": None}


def test_bbox_five_elements_rejected_batch54():
    d = _doc([_el(type="paragraph",
                  source_locator={"page": 1, "bbox": [1, 2, 3, 4, 5]})])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0, "reason": None}


# ---------- page 边界 ----------

@pytest.mark.parametrize("page,expected", [(0, 0.0), (-5, 0.0),
                                           (10 ** 20, 1.0)])
def test_page_boundaries_batch54(page, expected):
    d = _doc([_el(type="paragraph",
                  source_locator={"page": page, "bbox": [1, 2, 3, 4]})])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == expected


# ---------- DOCX locator ----------

def test_docx_empty_locator_invalid_batch54():
    d = _doc([_el(type="paragraph", source_locator={})])
    out = compute_automatic_metrics(d, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 0.0, "reason": None}


def test_docx_section_only_valid_batch54():
    d = _doc([_el(type="paragraph", source_locator={"section": 1})])
    out = compute_automatic_metrics(d, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 1.0, "reason": None}


# ---------- 未守卫输入 ----------

def test_unhashable_type_keyerror_batch54():
    with pytest.raises(TypeError):
        compute_automatic_metrics(_doc([_el(type=["a"])]), None,
                                  "pdf", None)


def test_error_without_code_key_batch54():
    with pytest.raises(KeyError):
        compute_automatic_metrics(_doc([]), {"message": "x"}, "pdf", None)


# ---------- expectations 未知类型 ----------

def test_expectations_unknown_type_full_drop_batch54():
    d = _doc([_el(type="paragraph", content="a")], [{"text": "a"}])
    out = compute_automatic_metrics(
        d, None, "pdf",
        {"element_count_by_type": {"paragraph": 3, "table": 2}})
    assert out["silent_drop_count"] == {"value": 4, "reason": None}


# ---------- image content 滤除 ----------

def test_image_content_excluded_from_expected_batch54():
    d = _doc([_el(type="paragraph", content="a"),
              _el(type="image", content="IMG")], [{"text": "a"}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": True, "reason": None}


# ---------- 空元素集 ----------

def test_no_elements_chunk_ref_zero_batch54():
    d = _doc([], [{"source_element_ids": ["x"]}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"] == {"value": 0.0,
                                                   "reason": None}


def test_heading_no_chunk_ids_zero_batch54():
    d = _doc([_el(type="heading", element_id="h1")], [{"text": "x"}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["heading_boundary_compliance"] == {"value": 0.0,
                                                  "reason": None}


# ---------- 键顺序 ----------

def test_metric_key_order_failed_path_batch54():
    assert list(compute_automatic_metrics(None, None, "pdf", None)) == \
        _KEY_ORDER


def test_metric_key_order_success_path_batch54():
    d = _doc([_el(type="paragraph", content="a", element_id="e1")],
             [{"text": "a", "source_element_ids": ["e1"]}])
    assert list(compute_automatic_metrics(d, None, "pdf", None)) == \
        _KEY_ORDER


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_bbox_and_drop_lines_batch54():
    src = _src()
    assert "len(bbox) != 4" in src
    assert "math.isfinite(v)" in src
    assert "drops += (exp - actual)" in src


# ---------- forbidden tokens 第二百二十八批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
