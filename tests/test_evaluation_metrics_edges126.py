"""evaluation/metrics.py 第四百八十二轮 edges 测试（Round 1038）。

补强 edges125 未触及的角度（第四百一十四批，probe 实证）。

新角度（docx 混合定位板 + schema-指标张力）：
- 四元素 docx 板（idx 0 / idx 2 / heading idx 5 /
  table page-only）单次调用：docx_locator 0.75——
  paragraph_index 0 失分（指标要求 >= 1）、page-only
  table 在 docx 侧合法
- schema-指标张力：同一份 doc schema_valid True
  （document.schema.json 不约束 index 下限）而
  docx_locator 已把 idx 0 计为无效——schema 宽、
  指标严，同屏并存
- heading 0.0（first-id 规则 docx 侧：h1 在 ids[1]）
  与 pdf_locator null not_pdf_document 镜像同屏
- ecbt 三键 {paragraph 2, heading 1, table 1}、
  intact 1.0、text_preservation False、image null
  no_image_elements 全量同屏
- forbidden tokens 第五百零九批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _e(t, eid, loc):
    return {"type": t, "element_id": eid, "content": "x",
            "parent_id": None, "confidence": 0.9,
            "metadata": {}, "source_locator": loc}


_DOCX_BOARD = {
    "elements": [
        _e("paragraph", "p1", {"paragraph_index": 0}),
        _e("paragraph", "p2", {"paragraph_index": 2}),
        _e("heading", "h1", {"paragraph_index": 5}),
        _e("table", "t1", {"page": 1})],
    "chunks": [{"chunk_id": "c", "text": "x",
                "source_element_ids": ["p1", "p2", "h1",
                                       "t1"],
                "metadata": {}}],
    "source_type": "docx", "document_id": "x",
    "schema_version": "0.1.0", "source_path": "a.docx",
    "source_hash": "a" * 64, "parser_name": "fb",
    "parser_version": "1", "relations": [],
    "warnings": [], "errors": [], "metadata": {}}


def _m():
    return compute_automatic_metrics(_DOCX_BOARD, None,
                                     "docx", None)


# ---------- docx 定位板 ----------

def test_docx_board_locator_batch236():
    m = _m()
    assert m["docx_locator_valid_ratio"] == {"value": 0.75,
                                             "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}


# ---------- schema-指标张力 ----------

def test_schema_lenient_metric_strict_batch236():
    m = _m()
    assert m["schema_valid"] == {"value": True,
                                 "reason": None}
    assert m["docx_locator_valid_ratio"]["value"] == 0.75


# ---------- heading first-id docx 侧 ----------

def test_heading_first_id_docx_batch236():
    assert _m()["heading_boundary_compliance"] == {
        "value": 0.0, "reason": None}


# ---------- 全量同屏 ----------

def test_board_remaining_metrics_batch236():
    m = _m()
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2, "heading": 1,
                  "table": 1}, "reason": None}
    assert m["element_count_total"] == {"value": 4,
                                        "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch236():
    src = _src()
    assert "paragraph_index" in src
    assert "not_pdf_document" in src
    assert "not_docx_document" in src


# ---------- forbidden tokens 第五百零九批 ----------

def test_source_no_eval_batch236():
    assert "eval(" not in _src()


def test_source_no_exec_batch236():
    assert "exec(" not in _src()


def test_source_no_compile_batch236():
    assert "compile(" not in _src()


def test_source_no_globals_batch236():
    assert "globals(" not in _src()


def test_source_no_locals_batch236():
    assert "locals(" not in _src()


def test_source_no_os_system_batch236():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch236():
    assert "subprocess" not in _src()


def test_source_no_popen_batch236():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch236():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch236():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch236():
    assert "socket" not in _src()


def test_source_no_requests_batch236():
    assert "requests" not in _src()


def test_source_no_urllib_batch236():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch236():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch236():
    assert "yield" not in _src()


def test_source_no_async_await_batch236():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch236():
    assert "open(" not in _src()
