"""evaluation/metrics.py 第三百零七轮 edges 测试（Round 863）。

补强 edges101 未触及的角度（第二百三十八批）。

新角度：
- 成功路径指标键恰 14 项（精确集合）
- docx 结构键 7 种逐一有效（parametrize）
- PDF 非 bbox 必需类型（header/image）仅 page 即有效
- resource_path 裸文件名 + image_base_dir 兜底命中/未命中
- image 元素 content 不参与文本保留
- paragraph content None + chunk 空文本 → 双空
- bbox 传 tuple / 5 元素 → 无效
- expectations.element_count_by_type 为空 dict →
  no_expectations_element_count
- CJK 文本保留
- forbidden tokens 第三百三十三批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam

_STRUCTURAL = ["section", "paragraph_index", "run_index",
               "table_index", "row_index", "col_index",
               "relationship_id"]

_ALL_KEYS = sorted([
    "pipeline_success", "error_code", "schema_valid",
    "element_count_total", "element_count_by_type",
    "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
    "image_resource_exists_ratio",
    "chunk_reference_intact_ratio",
    "text_preservation_equal",
    "text_char_multiset_precision",
    "text_char_multiset_recall",
    "heading_boundary_compliance", "silent_drop_count",
])


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, st="pdf", exp=None, base=None):
    with patch.object(sv, "document_passes_schema",
                      lambda d: True):
        return cam(document, None, st, exp, base)


# ---------- 键集合 ----------

def test_metrics_keys_exactly_fourteen_batch61():
    m = _cam(_doc([_el("e1", "paragraph")]))
    assert sorted(m) == _ALL_KEYS


# ---------- docx 结构键表 ----------

@pytest.mark.parametrize("key", _STRUCTURAL)
def test_docx_structural_key_table_batch61(key):
    els = [_el("e1", "paragraph",
               source_locator={key: 1})]
    m = _cam(_doc(els), st="docx")
    assert m["docx_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- PDF 非 bbox 类型 ----------

def test_pdf_non_bbox_types_page_only_batch61():
    els = [_el("e1", "header",
               source_locator={"page": 1}),
           _el("e2", "image",
               source_locator={"page": 2})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 裸文件名 + base_dir ----------

def test_image_filename_base_dir_fallback_batch61(tmp_path):
    els = [_el("e1", "image", resource_path="pic.png")]
    (tmp_path / "pic.png").write_bytes(b"xx")
    m = _cam(_doc(els), base=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_image_filename_base_dir_miss_batch61(tmp_path):
    els = [_el("e1", "image", resource_path="pic.png")]
    m = _cam(_doc(els), base=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- 文本保留 ----------

def test_image_content_excluded_batch61():
    els = [_el("e1", "paragraph", content="AB"),
           _el("e2", "image", content="XYZ")]
    m = _cam(_doc(els, [{"text": "AB",
                         "source_element_ids": ["e1"]}]))
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}


def test_none_content_and_empty_text_both_empty_batch61():
    els = [_el("e1", "paragraph", content=None)]
    m = _cam(_doc(els, [{"text": "",
                         "source_element_ids": ["e1"]}]))
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"]["reason"] == \
        "empty_expected_and_actual"


def test_cjk_text_preservation_batch61():
    els = [_el("e1", "paragraph", content="你好世界")]
    m = _cam(_doc(els, [{"text": "你好世界",
                         "source_element_ids": ["e1"]}]))
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- bbox 形状 ----------

def test_bbox_tuple_invalid_batch61():
    els = [_el("e1", "paragraph",
               source_locator={"page": 1,
                               "bbox": (0, 0, 1, 1)})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


def test_bbox_five_items_invalid_batch61():
    els = [_el("e1", "paragraph",
               source_locator={"page": 1,
                               "bbox": [0, 0, 1, 1, 2]})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- silent_drop 空 counts ----------

def test_silent_drop_empty_counts_dict_batch61():
    m = _cam(_doc([_el("e1", "paragraph")]),
             exp={"element_count_by_type": {}})
    assert m["silent_drop_count"] == {
        "value": None,
        "reason": "no_expectations_element_count"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch61():
    src = _src()
    assert "if not isinstance(bbox, list) or len(bbox) != 4:" in src
    assert 'images = [e for e in elements if e.get("type") == "image"]' in src
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


# ---------- forbidden tokens 第三百三十三批 ----------

def test_source_no_eval_batch61():
    assert "eval(" not in _src()


def test_source_no_exec_batch61():
    assert "exec(" not in _src()


def test_source_no_compile_batch61():
    assert "compile(" not in _src()


def test_source_no_globals_batch61():
    assert "globals(" not in _src()


def test_source_no_locals_batch61():
    assert "locals(" not in _src()


def test_source_no_os_system_batch61():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch61():
    assert "subprocess" not in _src()


def test_source_no_popen_batch61():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch61():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch61():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch61():
    assert "socket" not in _src()


def test_source_no_requests_batch61():
    assert "requests" not in _src()


def test_source_no_urllib_batch61():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch61():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch61():
    assert "yield" not in _src()


def test_source_no_async_await_batch61():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch61():
    assert "open(" not in _src()
