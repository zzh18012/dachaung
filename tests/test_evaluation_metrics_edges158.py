"""evaluation/metrics.py 第五百七十九轮 edges 测试（Round 1338）。

补强 edges157 未触及的角度（第七百一十批，probe 实证）。

新角度（手工 dict 受控保真分界面）：
- **reorder 分界**——
  chunks 'ba' vs
  elements 'ab' →
  tpe False 但
  tcmp/tcmr 双
  1.0（序列等 vs
  多重集等的分界
  首锁）
- **extra 侧**——
  'abx' vs 'ab' →
  tcmp 2/3、
  tcmr 1.0（precision
  单侧受损）
- **missing 侧**——
  'a' vs 'ab' →
  tcmp 1.0、
  tcmr 0.5（recall
  单侧受损）
- **空白归一**——
  'a b' vs 'ab' →
  tpe True（tpe 前
  空白压缩首锁）
- **手工 dict 面**
  ——schema_valid
  False 但其余指标
  照算（metrics 不
  因 schema 失败而
  短路首锁）
- forbidden tokens 第七百八十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import \
    compute_automatic_metrics


def _mk(chunks_text, elems_content):
    return {
        "schema_version": "1.0",
        "document_id": "d", "source_hash": "x",
        "source_type": "text",
        "source_path": "t.txt",
        "parser_name": "f", "parser_version": "1",
        "relations": [], "warnings": [],
        "errors": [], "metadata": {},
        "elements": [
            {"element_id": "e%d" % i,
             "type": "paragraph",
             "source_locator": {"line": i},
             "parent_id": None, "content": c,
             "resource_path": None,
             "confidence": 0.9, "metadata": {}}
            for i, c in enumerate(elems_content)],
        "chunks": [
            {"chunk_id": "c%d" % i, "text": t,
             "source_element_ids": ["e%d" % i],
             "source_spans": [],
             "metadata": {}}
            for i, t in enumerate(chunks_text)]}


def _m(chunks_text, elems_content):
    return compute_automatic_metrics(
        _mk(chunks_text, elems_content), None,
        "text", None)


# ---------- same 基线 ----------

def test_same_all_green_batch536():
    m = _m(["ab"], ["ab"])
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- reorder 分界 ----------

def test_reorder_tpe_false_batch536():
    assert _m(["ba"], ["ab"])[
        "text_preservation_equal"] == {
        "value": False, "reason": None}


def test_reorder_multiset_one_batch536():
    m = _m(["ba"], ["ab"])
    assert m[
        "text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m[
        "text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- extra 侧 ----------

def test_extra_tcmp_two_thirds_batch536():
    assert _m(["abx"], ["ab"])[
        "text_char_multiset_precision"] == {
        "value": 2 / 3, "reason": None}


def test_extra_tcmr_one_batch536():
    assert _m(["abx"], ["ab"])[
        "text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


def test_extra_tpe_false_batch536():
    assert _m(["abx"], ["ab"])[
        "text_preservation_equal"] == {
        "value": False, "reason": None}


# ---------- missing 侧 ----------

def test_missing_tcmp_one_batch536():
    assert _m(["a"], ["ab"])[
        "text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}


def test_missing_tcmr_half_batch536():
    assert _m(["a"], ["ab"])[
        "text_char_multiset_recall"] == {
        "value": 0.5, "reason": None}


# ---------- 空白归一 ----------

def test_whitespace_normalized_tpe_batch536():
    assert _m(["a b"], ["ab"])[
        "text_preservation_equal"] == {
        "value": True, "reason": None}


def test_whitespace_multiset_one_batch536():
    m = _m(["a b"], ["ab"])
    assert m[
        "text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}


# ---------- 手工 dict 面 ----------

def test_hand_dict_schema_false_batch536():
    m = _m(["ab"], ["ab"])
    assert m["schema_valid"] == {
        "value": False, "reason": None}


def test_hand_dict_crir_one_batch536():
    assert _m(["ab"], ["ab"])[
        "chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_hand_dict_ect_one_batch536():
    assert _m(["ab"], ["ab"])[
        "element_count_total"] == {
        "value": 1, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch536():
    src = _src()
    assert "st_size" in src
    assert "no_image_elements" in src


# ---------- forbidden tokens 第七百八十一批 ----------

def test_source_no_eval_batch536():
    assert "eval(" not in _src()


def test_source_no_exec_batch536():
    assert "exec(" not in _src()


def test_source_no_compile_batch536():
    assert "compile(" not in _src()


def test_source_no_globals_batch536():
    assert "globals(" not in _src()


def test_source_no_locals_batch536():
    assert "locals(" not in _src()


def test_source_no_os_system_batch536():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch536():
    assert "subprocess" not in _src()


def test_source_no_popen_batch536():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch536():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch536():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch536():
    assert "socket" not in _src()


def test_source_no_requests_batch536():
    assert "requests" not in _src()


def test_source_no_urllib_batch536():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch536():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch536():
    assert "yield" not in _src()


def test_source_no_async_await_batch536():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch536():
    assert _src().count("open(") == 0
