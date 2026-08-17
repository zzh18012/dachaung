"""evaluation/metrics.py 第三百九十一轮 edges 测试（Round 947）。

补强 edges112 未触及的角度（第三百二十三批，probe 实证）。

新角度：
- element_count_by_type 插入序 = 类型首次出现序
  （[paragraph, heading, paragraph, table] → 键序
  [paragraph, heading, table]，值 {2,1,1}）
- 失败文档（error 非 None）仍输出 14 键完整骨架；error_
  code 为 {"value": "E_PARSE", "reason": None}——reason
  恒 None 是构造怪癖（即便有错误也不写 reason）
- 仅 image 元素（无 content）+ 空 chunks → equal True +
  P/R null empty_expected_and_actual
- docx locator 含 page 键 → 立即无效（即使 section 也在）
- pdf table 类型免 bbox：仅 page 3 → 1.0
- resource_path 指向目录 → is_file False → 0.0
- forbidden tokens 第四百一十七批
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _run(doc, st="pdf", exp=None, base=None):
    return compute_automatic_metrics(doc, None, st, exp,
                                     image_base_dir=base)


# ---------- by_type 插入序 ----------

def test_by_type_insertion_order_batch145():
    doc = {"elements": [
        {"type": "paragraph", "content": "A"},
        {"type": "heading", "content": "B"},
        {"type": "paragraph", "content": "C"},
        {"type": "table", "content": "D"}],
        "chunks": []}
    m = _run(doc)
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2, "heading": 1, "table": 1},
        "reason": None}
    assert list(m["element_count_by_type"]["value"]) == [
        "paragraph", "heading", "table"]


# ---------- 失败文档骨架 ----------

def test_failed_doc_fourteen_keys_batch145():
    m = compute_automatic_metrics(
        None, {"code": "E_PARSE", "message": "x"}, "pdf", None)
    assert len(m) == 14
    assert list(m)[:4] == [
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total"]
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}


def test_error_code_reason_none_quirk_batch145():
    m = compute_automatic_metrics(
        None, {"code": "E_PARSE", "message": "x"}, "pdf", None)
    # 有错误时 reason 仍是 None（不写 reason 的构造怪癖）
    assert m["error_code"] == {"value": "E_PARSE",
                               "reason": None}
    assert m["schema_valid"]["reason"] == "pipeline_failed"
    assert m["silent_drop_count"]["reason"] == \
        "pipeline_failed"


# ---------- image-only 空双侧 ----------

def test_image_only_empty_both_batch145():
    doc = {"elements": [{"type": "image",
                         "resource_path": "x"}],
           "chunks": []}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}


# ---------- docx page 键 ----------

def test_docx_page_key_invalid_batch145():
    doc = {"elements": [{
        "type": "paragraph", "content": "A",
        "source_locator": {"section": 1, "page": 2}}],
        "chunks": []}
    assert _run(doc, "docx")["docx_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- pdf table 免 bbox ----------

def test_pdf_table_page_only_batch145():
    doc = {"elements": [{
        "type": "table", "content": "A",
        "source_locator": {"page": 3}}],
        "chunks": []}
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- resource_path 目录 ----------

def test_resource_path_directory_batch145(tmp_path):
    doc = {"elements": [{"type": "image",
                         "resource_path": str(tmp_path)}],
           "chunks": []}
    assert _run(doc, base=tmp_path)[
        "image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch145():
    src = _src()
    assert 'metrics["error_code"] = (' in src
    assert 'by_type[t] = by_type.get(t, 0) + 1' in src
    assert 'for t, exp in expected_counts.items():' in src
    assert 'if not rp:' in src


# ---------- forbidden tokens 第四百一十七批 ----------

def test_source_no_eval_batch145():
    assert "eval(" not in _src()


def test_source_no_exec_batch145():
    assert "exec(" not in _src()


def test_source_no_compile_batch145():
    assert "compile(" not in _src()


def test_source_no_globals_batch145():
    assert "globals(" not in _src()


def test_source_no_locals_batch145():
    assert "locals(" not in _src()


def test_source_no_os_system_batch145():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch145():
    assert "subprocess" not in _src()


def test_source_no_popen_batch145():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch145():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch145():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch145():
    assert "socket" not in _src()


def test_source_no_requests_batch145():
    assert "requests" not in _src()


def test_source_no_urllib_batch145():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch145():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch145():
    assert "yield" not in _src()


def test_source_no_async_await_batch145():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch145():
    assert "open(" not in _src()
