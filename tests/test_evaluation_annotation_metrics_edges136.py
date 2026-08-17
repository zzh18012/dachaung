"""evaluation/annotation_metrics.py 第五百二十八轮 edges 测试（Round 1084）。

补强 edges133-135 未触及的角度（第四百六十批，probe 实证）。

新角度（annotation 身份键不设防 + 锚序支配出现分配）：
- **doc_id 不交叉校验**：annotation doc_id "other" 对
  document_id "d" 照常生效（P 0.5 / R 1.0）；连 doc_id
  键整个缺失也照常——标注与文档的身份对齐完全交给
  上游 manifest
- **锚序支配 marker 出现位置分配**：[CCC, BBB, BBB]
  三锚——CCC 先消费中段，第一个 BBB 从 search_from
  之后找到**第三 chunk 的 BBB**（第一 chunk 的 BBB
  在已越过的窗口里、未被消费也被跳过），第二个 BBB
  耗尽进 missing ['BBB']——P 2/3 / R 1.0 / F1 0.8
- **anchor 非 dict 直接崩**：anchors 列表塞字符串
  "BBB" → AttributeError 'str' object has no
  attribute 'get'——上游 schema 守门、此处不兜底
- forbidden tokens 第五百五十五批（open 0）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(chunks):
    els = [{"element_id": f"e{i}", "type": "paragraph",
            "content": {"text": t}}
           for i, t in enumerate(chunks)]
    chs = [{"chunk_id": f"c{i}", "text": t,
            "source_element_ids": [f"e{i}"]}
           for i, t in enumerate(chunks)]
    return {"document_id": "d", "elements": els,
            "chunks": chs}


_BOARD3 = ["AAA first paragraph body one.",
           "BBB mid paragraph body two.",
           "CCC third paragraph body three."]
_BOARD4 = ["AAA first paragraph body one.",
           "BBB mid paragraph body two.",
           "CCC third paragraph body three.",
           "BBB mid paragraph body four."]


# ---------- doc_id 不交叉校验 ----------

def test_doc_id_mismatch_ignored_batch283():
    ann = {"annotation_version": "1.0", "doc_id": "other",
           "chunk_boundary_anchors": [
               {"marker": "BBB", "position": "before"}]}
    out = chunk_boundary_prf(_doc(_BOARD3), ann,
                             tolerance_chars=30)
    assert out["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- doc_id 键整个缺失 ----------

def test_doc_id_absent_batch283():
    ann = {"annotation_version": "1.0",
           "chunk_boundary_anchors": [
               {"marker": "BBB", "position": "before"}]}
    out = chunk_boundary_prf(_doc(_BOARD3), ann,
                             tolerance_chars=30)
    assert out["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 锚序支配出现分配 ----------

def test_anchor_order_skips_early_batch283():
    ann = {"annotation_version": "1.0", "doc_id": "d",
           "chunk_boundary_anchors": [
               {"marker": "CCC", "position": "before"},
               {"marker": "BBB", "position": "before"},
               {"marker": "BBB", "position": "before"}]}
    out = chunk_boundary_prf(_doc(_BOARD4), ann,
                             tolerance_chars=30)
    assert out["chunk_boundary_precision"] == {
        "value": 0.6666666666666666, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": 0.8, "reason": None}
    assert out["_missing_markers"] == {
        "value": ["BBB"], "reason": None}


# ---------- anchor 非 dict 直接崩 ----------

def test_string_anchor_crashes_batch283():
    ann = {"annotation_version": "1.0", "doc_id": "d",
           "chunk_boundary_anchors": ["BBB"]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(_doc(_BOARD3), ann,
                           tolerance_chars=30)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch283():
    src = _src()
    assert ("find_pos = stream.find(marker, search_from)"
            " if marker else -1") in src
    assert "search_from = find_pos + len(marker)" in src


# ---------- forbidden tokens 第五百五十五批 ----------

def test_source_no_eval_batch283():
    assert "eval(" not in _src()


def test_source_no_exec_batch283():
    assert "exec(" not in _src()


def test_source_no_compile_batch283():
    assert "compile(" not in _src()


def test_source_no_globals_batch283():
    assert "globals(" not in _src()


def test_source_no_locals_batch283():
    assert "locals(" not in _src()


def test_source_no_os_system_batch283():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch283():
    assert "subprocess" not in _src()


def test_source_no_popen_batch283():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch283():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch283():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch283():
    assert "socket" not in _src()


def test_source_no_requests_batch283():
    assert "requests" not in _src()


def test_source_no_urllib_batch283():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch283():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch283():
    assert "yield" not in _src()


def test_source_no_async_await_batch283():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch283():
    assert "open(" not in _src()
