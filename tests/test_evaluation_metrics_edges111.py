"""evaluation/metrics.py 第三百七十七轮 edges 测试（Round 933）。

补强 edges110 未触及的角度（第三百零九批，probe 实证）。

新角度：
- 成功文档 metrics 恰 14 键且全序锁定（pipeline_success →
  error_code → schema_valid → element_count_total → … →
  silent_drop_count）
- page=True（bool 是 int 子类）通过 isinstance 检查 → 1.0；
  page=1.0（float）不通过 → 0.0
- docx locator 结构键只查在场不查值：{"section": None} →
  1.0；元素无 source_locator 键 → 0.0
- image resource：0 字节文件不算存在；同目录文件名经
  image_base_dir 第二候选命中 → 2 图各 0.5
- 纯空白双侧：strip 后都空 → equal True 但 P/R null
  empty_expected_and_actual
- AAB vs ABB：equal False、P=R=2/3（Counter 交集
  min(A:1, B:1)）
- chunk ids [] 与 None 都判无效（ids 真值短路），1/3
- 元素缺 type 键 → "unknown" 桶
- silent_drop：actual > expected 不计负（值 0）；
  expectations {} → no_expectations；
  element_count_by_type 缺键/空 dict → 同一
  no_expectations_element_count
- forbidden tokens 第四百零三批
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from evaluation.metrics import compute_automatic_metrics


def _run(doc, st="pdf", exp=None, base=None):
    return compute_automatic_metrics(doc, None, st, exp, base)


# ---------- 14 键全序 ----------

def test_full_key_order_fourteen_batch131():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "AB",
                         "source_locator": {"page": 1,
                                            "bbox": [0, 0, 1, 1]}}],
           "chunks": [{"text": "AB",
                       "source_element_ids": ["e1"]}]}
    m = _run(doc)
    assert list(m) == [
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance", "silent_drop_count"]
    assert len(m) == 14


# ---------- page 类型怪癖 ----------

def test_bool_page_passes_batch131():
    doc = {"elements": [{"element_id": "e1", "type": "image",
                         "resource_path": "x",
                         "source_locator": {"page": True}}],
           "chunks": []}
    # bool 是 int 子类：True 通过 isinstance 且 True >= 1
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_float_page_rejected_batch131():
    doc = {"elements": [{"element_id": "e1", "type": "image",
                         "resource_path": "x",
                         "source_locator": {"page": 1.0}}],
           "chunks": []}
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- docx 结构键只查在场 ----------

def test_docx_structural_key_none_value_batch131():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "A",
                         "source_locator": {"section": None}}],
           "chunks": []}
    assert _run(doc, "docx")["docx_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_docx_missing_locator_zero_batch131():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "A"}],
           "chunks": []}
    assert _run(doc, "docx")["docx_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- image 文件实存 ----------

def test_image_empty_file_and_base_dir_batch131(tmp_path):
    (tmp_path / "empty.png").write_bytes(b"")
    (tmp_path / "full.png").write_bytes(b"x")
    doc = {"elements": [
        {"element_id": "i1", "type": "image",
         "resource_path": str(tmp_path / "empty.png")},
        {"element_id": "i2", "type": "image",
         "resource_path": "full.png"}],
        "chunks": []}
    # 空文件 st_size 0 不算；文件名经 base_dir 第二候选命中
    assert _run(doc, base=tmp_path)[
        "image_resource_exists_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- 纯空白双侧 ----------

def test_whitespace_only_equal_true_batch131():
    doc = {"elements": [{"type": "paragraph", "content": " "}],
           "chunks": [{"text": "\t\n"}]}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}
    assert m["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected_and_actual"}


# ---------- AAB vs ABB ----------

def test_multiset_intersection_two_thirds_batch131():
    doc = {"elements": [{"type": "paragraph", "content": "AAB"}],
           "chunks": [{"text": "ABB"}]}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"]["value"] == \
        pytest.approx(2 / 3)
    assert m["text_char_multiset_recall"]["value"] == \
        pytest.approx(2 / 3)


# ---------- chunk ids 真值短路 ----------

def test_chunk_empty_or_none_ids_batch131():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "A"}],
           "chunks": [{"text": "A", "source_element_ids": []},
                      {"text": "B", "source_element_ids": None},
                      {"text": "C",
                       "source_element_ids": ["e1"]}]}
    assert _run(doc)["chunk_reference_intact_ratio"] == {
        "value": pytest.approx(1 / 3), "reason": None}


# ---------- unknown 桶 ----------

def test_missing_type_unknown_bucket_batch131():
    doc = {"elements": [{"element_id": "e1", "content": "A"}],
           "chunks": []}
    assert _run(doc)["element_count_by_type"] == {
        "value": {"unknown": 1}, "reason": None}


# ---------- silent_drop 方向与空 expectations ----------

def test_silent_drop_negative_direction_batch131():
    doc = {"elements": [
        {"element_id": "e1", "type": "paragraph", "content": "A"},
        {"element_id": "e2", "type": "paragraph", "content": "B"},
        {"element_id": "e3", "type": "paragraph", "content": "C"}],
        "chunks": []}
    # actual 3 > expected 1 → max(0, -2) 不计 → 0
    assert _run(doc, exp={"element_count_by_type": {
        "paragraph": 1}})["silent_drop_count"] == {
        "value": 0, "reason": None}


def test_silent_drop_empty_expectations_matrix_batch131():
    doc = {"elements": [{"element_id": "e1", "content": "A"}],
           "chunks": []}
    ect_null = {"value": None,
                "reason": "no_expectations_element_count"}
    assert _run(doc, exp={"element_count_by_type": {}})[
        "silent_drop_count"] == ect_null
    assert _run(doc, exp={"other": 1})["silent_drop_count"] == \
        ect_null
    assert _run(doc, exp={})["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_key_lines_batch131():
    src = _src()
    assert "pipeline_success = error is None and document is not None" in src
    assert 't = e.get("type", "unknown")' in src
    assert "if not isinstance(page, int) or page < 1:" in src
    assert 'if "page" in loc or "bbox" in loc:' in src
    assert "if p.is_file() and p.stat().st_size > 0:" in src
    assert "common = sum((c_expected & c_actual).values())" in src
    assert "drops += (exp - actual)" in src


# ---------- forbidden tokens 第四百零三批 ----------

def test_source_no_eval_batch131():
    assert "eval(" not in _src()


def test_source_no_exec_batch131():
    assert "exec(" not in _src()


def test_source_no_compile_batch131():
    assert "compile(" not in _src()


def test_source_no_globals_batch131():
    assert "globals(" not in _src()


def test_source_no_locals_batch131():
    assert "locals(" not in _src()


def test_source_no_os_system_batch131():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch131():
    assert "subprocess" not in _src()


def test_source_no_popen_batch131():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch131():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch131():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch131():
    assert "socket" not in _src()


def test_source_no_requests_batch131():
    assert "requests" not in _src()


def test_source_no_urllib_batch131():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch131():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch131():
    assert "yield" not in _src()


def test_source_no_async_await_batch131():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch131():
    assert "open(" not in _src()
