"""evaluation/metrics.py 第五百三十七轮 edges 测试（Round 1093）。

补强 edges131-133 未触及的角度（第四百六十九批，probe 实证）。

新角度（真实文档变异四联：引用鬼影 / 定位失格 / 双侧文本镜像）：
- **chunk 引用鬼影**：chunks[0].source_element_ids 改
  ["ghost-id"] → chunk_reference_intact_ratio 直接
  0.0——单 chunk 全坏即全坏（all-or-nothing，非按
  引用数摊薄）；edges110 的 ghost 是 expectations 侧，
  引用侧首锁
- **element 定位失格**：elements[0].source_locator 置
  {} → docx_locator_valid_ratio 0.5——按元素摊薄
  （1/2 失格），与引用侧的 all-or-nothing 形成粒度
  对照
- **插入镜像**：chunk text 尾接 "EXTRA" →
  text_preservation_equal False + multiset
  **P 0.9 / R 1.0**（chunk 多出字符只伤 precision）
- **删除镜像**：chunk text 改 "short" → equal False +
  **P 1.0 / R 0.1111111111111111**——插入/删除恰好
  互换 P 与 R 的伤侧
- forbidden tokens 第五百六十四批（open 0）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
import pathlib

from docx import Document

import evaluation.metrics as metrics_mod
from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics


def _doc(tmp_path):
    p = tmp_path / "a.docx"
    d = Document()
    for t in ("AAA first paragraph body.",
              "BBB second paragraph body."):
        d.add_paragraph(t)
    d.save(str(p))
    doc, errors = process_single(
        p, tmp_path / "s.json", parser_name="fallback",
        max_chars=200, write_json=False)
    assert errors == []
    return doc.to_dict()


def _m(tmp_path, mut):
    r = copy.deepcopy(_doc(tmp_path))
    mut(r)
    return compute_automatic_metrics(r, None, "docx", None)


# ---------- chunk 引用鬼影 ----------

def test_ghost_chunk_ref_zeroes_batch292(tmp_path):
    out = _m(tmp_path, lambda r: r["chunks"][0].__setitem__(
        "source_element_ids", ["ghost-id"]))
    assert out["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- element 定位失格按元素摊薄 ----------

def test_empty_locator_halves_batch292(tmp_path):
    out = _m(tmp_path, lambda r: r["elements"][0].__setitem__(
        "source_locator", {}))
    assert out["docx_locator_valid_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- 插入镜像：只伤 precision ----------

def test_insertion_mirror_batch292(tmp_path):
    out = _m(tmp_path, lambda r: r["chunks"][0].__setitem__(
        "text", r["chunks"][0]["text"] + "EXTRA"))
    assert out["text_preservation_equal"] == {
        "value": False, "reason": None}
    assert out["text_char_multiset_precision"] == {
        "value": 0.9, "reason": None}
    assert out["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 删除镜像：只伤 recall ----------

def test_deletion_mirror_batch292(tmp_path):
    out = _m(tmp_path, lambda r: r["chunks"][0].__setitem__(
        "text", "short"))
    assert out["text_preservation_equal"] == {
        "value": False, "reason": None}
    assert out["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert out["text_char_multiset_recall"] == {
        "value": 0.1111111111111111, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch292():
    src = _src()
    assert "def _chunk_reference_ratio(" in src
    assert "def _docx_locator_ratio(" in src


# ---------- forbidden tokens 第五百六十四批 ----------

def test_source_no_eval_batch292():
    assert "eval(" not in _src()


def test_source_no_exec_batch292():
    assert "exec(" not in _src()


def test_source_no_compile_batch292():
    assert "compile(" not in _src()


def test_source_no_globals_batch292():
    assert "globals(" not in _src()


def test_source_no_locals_batch292():
    assert "locals(" not in _src()


def test_source_no_os_system_batch292():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch292():
    assert "subprocess" not in _src()


def test_source_no_popen_batch292():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch292():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch292():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch292():
    assert "socket" not in _src()


def test_source_no_requests_batch292():
    assert "requests" not in _src()


def test_source_no_urllib_batch292():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch292():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch292():
    assert "yield" not in _src()


def test_source_no_async_await_batch292():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch292():
    assert "open(" not in _src()
