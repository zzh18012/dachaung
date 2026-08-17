"""evaluation/metrics.py 第三百八十四轮 edges 测试（Round 940）。

补强 edges111 未触及的角度（第三百一十六批，probe 实证）。

新角度：
- 真正通过 app Schema 的完整文档 → schema_valid
  {"value": True}（schema_version "0.1.0" + 64 位
  source_hash + element/chunk 全字段）；仅缺 source_hash
  → False 非 exception
- _is_valid_bbox 六型全拒：bool 元素、5 元、数字字符串、
  NaN、inf、非 list（paragraph bbox 必填 → ratio 0.0）
- image 元素的 content 不进 expected：元素 image
  content "X" + chunk "X" → equal False、P 0.0（空
  expected 侧 R null empty_expected）
- 顺序分叉：expected "BA" vs actual "AB" → equal False
  而 multiset P=R=1.0（有序比对与多集合比对语义差）
- _strip_unicode_whitespace 删 NBSP（\\xa0）与表意空格
  （\\u3000）
- document 与 error 双 None：success False、error_code
  None、下游全部 pipeline_failed
- forbidden tokens 第四百一十批
"""

from __future__ import annotations

import inspect

import pytest

from evaluation.metrics import (
    _strip_unicode_whitespace,
    compute_automatic_metrics,
)

_VALID = {
    "schema_version": "0.1.0",
    "document_id": "doc-1", "source_path": "s/h.pdf",
    "source_type": "pdf", "parser_name": "fallback",
    "parser_version": "1.2", "source_hash": "a" * 64,
    "relations": [], "warnings": [], "errors": [],
    "metadata": {},
    "elements": [{
        "element_id": "e1", "type": "paragraph", "content": "AB",
        "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]},
        "parent_id": None, "confidence": 1.0, "metadata": {}}],
    "chunks": [{"chunk_id": "c1", "text": "AB",
                "source_element_ids": ["e1"], "metadata": {}}],
}


def _run(doc, st="pdf", exp=None):
    return compute_automatic_metrics(doc, None, st, exp)


# ---------- schema_valid 真 True ----------

def test_schema_valid_true_full_doc_batch138():
    m = _run(_VALID)
    assert m["schema_valid"] == {"value": True, "reason": None}
    assert m["pipeline_success"] == {"value": True, "reason": None}


def test_schema_valid_false_missing_field_batch138():
    broken = dict(_VALID)
    broken.pop("source_hash")
    m = _run(broken)
    assert m["schema_valid"] == {"value": False, "reason": None}


# ---------- bbox 六型全拒 ----------

def _pdf_doc(bbox):
    return {"elements": [{
        "element_id": "e1", "type": "paragraph", "content": "A",
        "source_locator": {"page": 1, "bbox": bbox}}],
        "chunks": []}


@pytest.mark.parametrize("label,bbox", [
    ("bools", [True, 0, 0, 1]),
    ("five", [0, 0, 1, 1, 2]),
    ("strs", ["0", "0", "1", "1"]),
    ("nan", [0, 0, float("nan"), 1]),
    ("inf", [0, 0, float("inf"), 1]),
    ("notlist", "abcd"),
])
def test_bbox_variants_rejected_batch138(label, bbox):
    assert _run(_pdf_doc(bbox))["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- image content 不进 expected ----------

def test_image_content_dropped_batch138():
    doc = {"elements": [{"element_id": "i1", "type": "image",
                         "content": "X",
                         "resource_path": "x.png"}],
           "chunks": [{"text": "X",
                       "source_element_ids": ["i1"]}]}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 0.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected"}


# ---------- 顺序分叉 ----------

def test_order_divergence_batch138():
    doc = {"elements": [
        {"type": "paragraph", "content": "B"},
        {"type": "paragraph", "content": "A"}],
        "chunks": [{"text": "AB"}]}
    m = _run(doc)
    # 同字符集不同顺序：equal False 而 multiset P/R 全 1.0
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- NBSP 与表意空格 ----------

def test_strip_nbsp_ideographic_batch138():
    assert _strip_unicode_whitespace("a\xa0b　c") == "abc"


# ---------- 双 None ----------

def test_both_none_batch138():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["error_code"] == {"value": None, "reason": None}
    assert m["schema_valid"] == {"value": None,
                                 "reason": "pipeline_failed"}
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_key_lines_batch138():
    src = _src()
    assert "if not isinstance(bbox, list) or len(bbox) != 4:" in src
    assert "if isinstance(v, bool):" in src
    assert "if not math.isfinite(v):" in src
    assert 'e.get("content") or ""' in src
    assert 'c.get("text") or ""' in src


# ---------- forbidden tokens 第四百一十批 ----------

def test_source_no_eval_batch138():
    assert "eval(" not in _src()


def test_source_no_exec_batch138():
    assert "exec(" not in _src()


def test_source_no_compile_batch138():
    assert "compile(" not in _src()


def test_source_no_globals_batch138():
    assert "globals(" not in _src()


def test_source_no_locals_batch138():
    assert "locals(" not in _src()


def test_source_no_os_system_batch138():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch138():
    assert "subprocess" not in _src()


def test_source_no_popen_batch138():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch138():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch138():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch138():
    assert "socket" not in _src()


def test_source_no_requests_batch138():
    assert "requests" not in _src()


def test_source_no_urllib_batch138():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch138():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch138():
    assert "yield" not in _src()


def test_source_no_async_await_batch138():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch138():
    assert "open(" not in _src()
