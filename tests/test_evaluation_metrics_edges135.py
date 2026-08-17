"""evaluation/metrics.py 第五百四十四轮 edges 测试（Round 1100）。

补强 edges133-134 未触及的角度（第四百七十六批，probe 实证）。

新角度（source_type 参数门控 + 引用存在性语义 + 零期望原谅）：
- **跨型门控全闭**：docx 产物 + source_type 参数
  "pdf" → pdf_locator_valid_ratio 0.0（docx 形
  locator 无 "page" 键、2/2 失格）+ docx_locator
  null not_docx_document——度量按**参数**分型，
  与 R1099 的 schema if/then 翻转互为表里
- **混合 pdf 比例 0.5**：一个 element 换 {page,
  bbox} → 0.5——跨型视角下按元素摊薄
- **重复引用照 intact 1.0**：chunk source_element_ids
  改 [id0, id0] → 1.0——引用检查是**存在性**而非
  唯一性（R1093 ghost-id 是存在性失败，重复是
  存在性满足的孪生）
- **零期望原谅**：expectations {paragraph 2,
  table 0} → silent_drop 0——从未出现但期望也
  为 0 的类型 max(0, 0-0)=0（R1080 锁过非零
  期望的 silent，零期望是原谅侧）
- forbidden tokens 第五百七十一批（open 0）
"""

from __future__ import annotations

import copy
import inspect
import pathlib
import tempfile

from docx import Document

import evaluation.metrics as metrics_mod
from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics


def _doc(tmp_path):
    p = tmp_path / "a.docx"
    d = Document()
    for t in ("AAA first body.",
              "BBB second body."):
        d.add_paragraph(t)
    d.save(str(p))
    doc, errors = process_single(
        p, tmp_path / "s.json", parser_name="fallback",
        max_chars=200, write_json=False)
    assert errors == []
    return doc.to_dict()


def _m(tmp_path, mut=None, source_type="docx",
       expectations=None):
    r = copy.deepcopy(_doc(tmp_path))
    if mut:
        mut(r)
    return compute_automatic_metrics(
        r, None, source_type, expectations)


# ---------- 跨型门控全闭 ----------

def test_pdf_gate_on_docx_doc_batch299(tmp_path):
    out = _m(tmp_path, source_type="pdf")
    assert out["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}
    assert out["docx_locator_valid_ratio"] == {
        "value": None,
        "reason": "not_docx_document"}


# ---------- 混合 pdf 比例 0.5 ----------

def test_mixed_pdf_ratio_halves_batch299(tmp_path):
    def mut(r):
        r["elements"][0]["source_locator"] = {
            "page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}
    out = _m(tmp_path, mut=mut, source_type="pdf")
    assert out["pdf_locator_valid_ratio"] == {
        "value": 0.5, "reason": None}
    assert out["docx_locator_valid_ratio"] == {
        "value": None,
        "reason": "not_docx_document"}


# ---------- 重复引用照 intact ----------

def test_duplicate_ids_still_intact_batch299(tmp_path):
    def mut(r):
        ids = [e["element_id"] for e in r["elements"]]
        r["chunks"][0]["source_element_ids"] = [
            ids[0], ids[0]]
    out = _m(tmp_path, mut=mut)
    assert out["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 零期望原谅 ----------

def test_zero_expectation_forgiven_batch299(tmp_path):
    out = _m(
        tmp_path,
        expectations={"element_count_by_type": {
            "paragraph": 2, "table": 0}})
    assert out["silent_drop_count"] == {
        "value": 0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch299():
    src = _src()
    assert "def _pdf_locator_ratio(" in src
    assert "def _silent_drop_count(" in src


# ---------- forbidden tokens 第五百七十一批 ----------

def test_source_no_eval_batch299():
    assert "eval(" not in _src()


def test_source_no_exec_batch299():
    assert "exec(" not in _src()


def test_source_no_compile_batch299():
    assert "compile(" not in _src()


def test_source_no_globals_batch299():
    assert "globals(" not in _src()


def test_source_no_locals_batch299():
    assert "locals(" not in _src()


def test_source_no_os_system_batch299():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch299():
    assert "subprocess" not in _src()


def test_source_no_popen_batch299():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch299():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch299():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch299():
    assert "socket" not in _src()


def test_source_no_requests_batch299():
    assert "requests" not in _src()


def test_source_no_urllib_batch299():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch299():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch299():
    assert "yield" not in _src()


def test_source_no_async_await_batch299():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch299():
    assert "open(" not in _src()
