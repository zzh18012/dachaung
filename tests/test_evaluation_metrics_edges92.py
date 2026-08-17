"""evaluation/metrics.py 第二百三十七轮 edges 测试（Round 793）。

补强 edges91 未触及的角度（第一百五十七批）。

新角度：
- 文本保留三空态：双空 → equal True（"" == ""）且双 null
  empty_expected_and_actual；空 actual → precision null +
  recall 0.0；空 expected（image-only）→ precision 0.0 +
  recall null（半评估态在两侧不对称出现）
- content 或 chunk text 传 int → TypeError("sequence item 0:
  expected str instance")（join 前无类型防线，"or 空"只挡
  falsy 不挡非空非 str）
- source_type "txt" → 双 locator 同时 null：
  not_pdf_document + not_docx_document（既非 pdf 也非 docx 的
  第三字符串）
- bbox 长度 3 → 0.0（len != 4 分支）
- page 传 float 1.0 → 0.0（isinstance float 非 int；与 True
  通过对照，bool 是 int 子类而 float 不是）
- forbidden tokens 第二百六十三批
"""

from __future__ import annotations

import inspect

import pytest

from evaluation.metrics import compute_automatic_metrics


def _run(doc, error=None, src="pdf", exp=None):
    return compute_automatic_metrics(doc, error, src, exp, None)


# ---------- 文本保留三空态 ----------

def test_both_empty_equal_true_nulls_batch54():
    o = _run({"elements": [{"type": "paragraph", "content": ""}],
              "chunks": [{"text": ""}]})
    assert o["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert o["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}
    assert o["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected_and_actual"}


def test_empty_actual_precision_null_batch54():
    o = _run({"elements": [{"type": "paragraph", "content": "A"}],
              "chunks": [{"text": ""}]})
    assert o["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert o["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_actual"}
    assert o["text_char_multiset_recall"] == {"value": 0.0,
                                              "reason": None}


def test_empty_expected_recall_null_batch54():
    o = _run({"elements": [{"type": "image", "resource_path": "x"}],
              "chunks": [{"text": "A"}]})
    assert o["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert o["text_char_multiset_precision"] == {"value": 0.0,
                                                 "reason": None}
    assert o["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected"}


# ---------- 非 str 文本崩溃 ----------

def test_content_int_type_error_batch54():
    with pytest.raises(TypeError,
                       match="sequence item 0: expected str"):
        _run({"elements": [{"type": "paragraph", "content": 5}],
              "chunks": [{"text": "5"}]})


def test_chunk_text_int_type_error_batch54():
    with pytest.raises(TypeError,
                       match="sequence item 0: expected str"):
        _run({"elements": [{"type": "paragraph", "content": "5"}],
              "chunks": [{"text": 5}]})


# ---------- 第三 source_type ----------

def test_source_type_txt_dual_null_batch54():
    o = _run({"elements": []}, src="txt")
    assert o["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert o["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


# ---------- bbox 长度与 page 浮点 ----------

def test_bbox_length_three_rejected_batch54():
    o = _run({"elements": [{"type": "paragraph",
                            "source_locator": {"page": 1,
                                               "bbox": [0, 0, 1]}}]})
    assert o["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


def test_page_float_rejected_batch54():
    o = _run({"elements": [{"type": "table",
                            "source_locator": {"page": 1.0}}]})
    assert o["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_empty_branches_batch54():
    src = _src()
    assert '"empty_expected_and_actual"' in src
    assert '"empty_actual"' in src
    assert '"empty_expected"' in src
    assert "if not isinstance(bbox, list) or len(bbox) != 4:" in src


# ---------- forbidden tokens 第二百六十三批 ----------

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
