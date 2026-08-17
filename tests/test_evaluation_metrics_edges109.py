"""evaluation/metrics.py 第三百六十三轮 edges 测试（Round 919）。

补强 edges108 未触及的角度（第二百九十五批，probe 实证）。

新角度：
- _PDF_BBOX_REQUIRED_TYPES 边界：caption / list_item 无 bbox →
  0.0；table 不需要 → 1.0（与 header 对照样）
- docx locator：仅 run_index 也算结构键 → 1.0；出现 bbox
  即无效（即使带 paragraph_index）→ 0.0
- chunk ids [None] 撞上 element_id None → None in 集合 →
  计 1.0（None==None 假命中怪癖）；chunk 缺 ids 键 → 0.0
- heading element_id None + chunk 首 id None → 合规 1.0
  （与 R905 单侧 None → 0.0 形成对照）
- resource_path 传 int → TypeError 冒出；绝对路径存在 →
  1.0（base_dir None 也行）
- 元素缺 content 键 + chunk 空 text → equal True 但
  precision/recall null empty_expected_and_actual（相等却
  "无内容可比"的拧巴组合）
- source_type "markdown" → 双 locator 各自 not_pdf/not_docx
  null；docx 空 elements → docx no_elements + pdf
  not_pdf_document
- forbidden tokens 第三百八十九批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _run(doc, st="pdf"):
    return compute_automatic_metrics(doc, None, st, None)


# ---------- pdf bbox 必需类型 ----------

@pytest.mark.parametrize("t,expected", [
    ("caption", 0.0), ("list_item", 0.0), ("table", 1.0),
])
def test_pdf_bbox_required_types_batch117(t, expected):
    doc = {"elements": [{"type": t,
                         "source_locator": {"page": 1}}],
           "chunks": []}
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": expected, "reason": None}


# ---------- docx locator ----------

def test_docx_run_index_only_valid_batch117():
    doc = {"elements": [{"type": "paragraph",
                         "source_locator": {"run_index": 0}}],
           "chunks": []}
    assert _run(doc, "docx")["docx_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_docx_bbox_key_invalidates_batch117():
    doc = {"elements": [{"type": "paragraph",
                         "source_locator": {
                             "bbox": [1, 2, 3, 4],
                             "paragraph_index": 1}}],
           "chunks": []}
    assert _run(doc, "docx")["docx_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- chunk 引用 None 怪癖 ----------

def test_none_id_reference_false_hit_batch117():
    doc = {"elements": [{"element_id": None, "type": "paragraph",
                         "content": "A"}],
           "chunks": [{"text": "A",
                       "source_element_ids": [None]}]}
    assert _run(doc)["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_chunk_missing_ids_key_zero_batch117():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "A"}],
           "chunks": [{"text": "A"}]}
    assert _run(doc)["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- heading None 怪癖 ----------

def test_none_heading_id_matched_by_none_first_batch117():
    doc = {"elements": [{"element_id": None, "type": "heading",
                         "content": "H"}],
           "chunks": [{"text": "H",
                       "source_element_ids": [None]}]}
    assert _run(doc)["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- image resource_path ----------

def test_image_resource_path_int_typeerror_batch117():
    doc = {"elements": [{"type": "image", "resource_path": 5}],
           "chunks": []}
    with pytest.raises(TypeError):
        _run(doc)


def test_image_absolute_path_no_base_batch117(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"x")
    doc = {"elements": [{"type": "image",
                         "resource_path": str(f)}],
           "chunks": []}
    assert _run(doc)["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 缺 content 键 ----------

def test_missing_content_equal_but_pr_null_batch117():
    doc = {"elements": [{"element_id": "e1",
                         "type": "paragraph"}],
           "chunks": [{"text": ""}]}
    out = _run(doc)
    assert out["text_preservation_equal"] == {"value": True,
                                              "reason": None}
    assert out["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}
    assert out["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected_and_actual"}


# ---------- source_type 非法/空 elements ----------

def test_markdown_source_type_dual_null_batch117():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "A"}],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1"]}]}
    out = _run(doc, "markdown")
    assert out["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert out["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


def test_docx_empty_elements_cross_null_batch117():
    out = _run({"elements": [], "chunks": []}, "docx")
    assert out["docx_locator_valid_ratio"] == {
        "value": None, "reason": "no_elements"}
    assert out["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch117():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src
    assert 'if "page" in loc or "bbox" in loc:' in src
    assert "candidates: list[Path] = [Path(rp)]" in src
    assert 't = e.get("type", "unknown")' in src


# ---------- forbidden tokens 第三百八十九批 ----------

def test_source_no_eval_batch117():
    assert "eval(" not in _src()


def test_source_no_exec_batch117():
    assert "exec(" not in _src()


def test_source_no_compile_batch117():
    assert "compile(" not in _src()


def test_source_no_globals_batch117():
    assert "globals(" not in _src()


def test_source_no_locals_batch117():
    assert "locals(" not in _src()


def test_source_no_os_system_batch117():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch117():
    assert "subprocess" not in _src()


def test_source_no_popen_batch117():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch117():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch117():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch117():
    assert "socket" not in _src()


def test_source_no_requests_batch117():
    assert "requests" not in _src()


def test_source_no_urllib_batch117():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch117():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch117():
    assert "yield" not in _src()


def test_source_no_async_await_batch117():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch117():
    assert "open(" not in _src()
