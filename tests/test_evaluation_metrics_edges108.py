"""evaluation/metrics.py 第三百五十六轮 edges 测试（Round 912）。

补强 edges107 未触及的角度（第二百八十八批，probe 实证）。

新角度：
- document 与 error 同时存在：pipeline_success False（error 非 None
  主导）但 element_count_total / schema_valid 照常计算——下游
  不看 error 只看 document 的不对称锁定
- error 缺 "code" 键 → KeyError('code') 直接冒出
- document_passes_schema 抛异常 → schema_valid
  {value False, reason "schema_check_exception:RuntimeError"}
- _strip_unicode_whitespace：NBSP/全角空格/U+2028/U+2029/制表
  换行全删，零宽空格 U+200B 保留
- image ratio 0.25 四分位：裸文件名靠 image_base_dir 拼接命中；
  零字节文件无效；空串 rp 无效；缺失文件无效
- 纯 image elements + 有字 chunks → precision 0.0、recall null
  empty_expected；反向（expected 非空 actual 空）→ precision
  null empty_actual、recall 0.0
- expectations 真值但 element_count_by_type 空 → null
  no_expectations_element_count（区别于 no_expectations）
- silent_drop = (3-1)+(2-0) = 4（只累计正差）
- pdf header 类型 page-only 无 bbox → 1.0（bbox 仅四个文本类型需要）
- forbidden tokens 第三百八十二批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _strip_unicode_whitespace,
    compute_automatic_metrics,
)


# ---------- document 与 error 并存 ----------

def test_doc_and_error_coexist_batch110():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        doc, {"code": "E_PARSE", "message": "x"}, "pdf", None)
    assert out["pipeline_success"] == {"value": False, "reason": None}
    assert out["error_code"] == {"value": "E_PARSE", "reason": None}
    # document 非 None → 下游照常计算
    assert out["element_count_total"] == {"value": 0, "reason": None}
    assert out["schema_valid"]["value"] is False  # 空 doc 过不了 schema


def test_error_missing_code_raises_keyerror_batch110():
    with pytest.raises(KeyError) as ei:
        compute_automatic_metrics(
            {"elements": [], "chunks": []},
            {"message": "x"}, "pdf", None)
    assert ei.value.args[0] == "code"


# ---------- schema 校验异常路径 ----------

def test_schema_check_exception_reason_batch110():
    with patch(
        "evaluation.schema_validation.document_passes_schema",
        side_effect=RuntimeError("boom"),
    ):
        out = compute_automatic_metrics(
            {"elements": [], "chunks": []}, None, "pdf", None)
    assert out["schema_valid"] == {
        "value": False,
        "reason": "schema_check_exception:RuntimeError"}


# ---------- _strip_unicode_whitespace ----------

def test_strip_unicode_whitespace_variants_batch110():
    s = "a\xa0b　c d e\tf\ng​h"
    assert _strip_unicode_whitespace(s) == "abcdefg​h"


def test_strip_all_whitespace_empty_batch110():
    assert _strip_unicode_whitespace(" \t\n\r\xa0　 ") == ""


# ---------- image_resource_exists_ratio 四分位 ----------

def test_image_ratio_quarter_join_zero_byte_batch110(tmp_path):
    (tmp_path / "img1.png").write_bytes(b"x")
    (tmp_path / "img0.png").write_bytes(b"")
    elems = [
        {"type": "image", "resource_path": "img1.png"},
        {"type": "image", "resource_path": "img0.png"},
        {"type": "image", "resource_path": ""},
        {"type": "image", "resource_path": "nope.png"},
    ]
    out = compute_automatic_metrics(
        {"elements": elems, "chunks": []}, None, "pdf", None,
        image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"] == {"value": 0.25,
                                                  "reason": None}


# ---------- 文本保留空侧不对称 ----------

def test_image_only_elements_text_asymmetry_batch110():
    doc = {"elements": [{"type": "image", "content": "PIC",
                         "resource_path": "x"}],
           "chunks": [{"text": "AB"}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": False,
                                              "reason": None}
    assert out["text_char_multiset_precision"] == {"value": 0.0,
                                                   "reason": None}
    assert out["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected"}


def test_empty_actual_text_asymmetry_batch110():
    doc = {"elements": [{"type": "paragraph", "content": "AB"}],
           "chunks": [{"text": ""}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": False,
                                              "reason": None}
    assert out["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_actual"}
    assert out["text_char_multiset_recall"] == {"value": 0.0,
                                                "reason": None}


# ---------- silent_drop_count ----------

def test_silent_drop_empty_expectation_counts_batch110():
    out = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "pdf",
        {"element_count_by_type": {}})
    assert out["silent_drop_count"] == {
        "value": None, "reason": "no_expectations_element_count"}


def test_silent_drop_positive_diffs_only_batch110():
    doc = {"elements": [{"type": "paragraph", "content": "A"}],
           "chunks": []}
    out = compute_automatic_metrics(
        doc, None, "pdf",
        {"element_count_by_type": {"paragraph": 3, "heading": 2}})
    assert out["silent_drop_count"] == {"value": 4, "reason": None}


def test_silent_drop_actual_exceeds_expected_batch110():
    doc = {"elements": [{"type": "paragraph", "content": "A"},
                        {"type": "paragraph", "content": "B"},
                        {"type": "paragraph", "content": "C"}],
           "chunks": []}
    out = compute_automatic_metrics(
        doc, None, "pdf",
        {"element_count_by_type": {"paragraph": 1}})
    assert out["silent_drop_count"] == {"value": 0, "reason": None}


# ---------- pdf locator：非 bbox 必需类型 ----------

def test_pdf_header_page_only_valid_batch110():
    doc = {"elements": [{"type": "header",
                         "source_locator": {"page": 2}}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0,
                                              "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch110():
    src = _src()
    assert "candidates.append(image_base_dir / Path(rp).name)" in src
    assert "p.is_file() and p.stat().st_size > 0" in src
    assert "drops += (exp - actual)" in src
    assert 'common = sum((c_expected & c_actual).values())' in src


def test_all_exports_batch110():
    assert metrics_mod.__all__ == ["compute_automatic_metrics"]


# ---------- forbidden tokens 第三百八十二批 ----------

def test_source_no_eval_batch110():
    assert "eval(" not in _src()


def test_source_no_exec_batch110():
    assert "exec(" not in _src()


def test_source_no_compile_batch110():
    assert "compile(" not in _src()


def test_source_no_globals_batch110():
    assert "globals(" not in _src()


def test_source_no_locals_batch110():
    assert "locals(" not in _src()


def test_source_no_os_system_batch110():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch110():
    assert "subprocess" not in _src()


def test_source_no_popen_batch110():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch110():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch110():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch110():
    assert "socket" not in _src()


def test_source_no_requests_batch110():
    assert "requests" not in _src()


def test_source_no_urllib_batch110():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch110():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch110():
    assert "yield" not in _src()


def test_source_no_async_await_batch110():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch110():
    assert "open(" not in _src()
