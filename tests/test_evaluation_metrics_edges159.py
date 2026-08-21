"""evaluation/metrics.py 第五百八十轮 edges 测试（Round 1344）。

补强 edges158 未触及的角度（第七百一十六批，probe 实证）。

新角度（空板 / 空文本 / 假图片资源 / 跨文档引用）：
- **空 doc 面**——
  无元素无 chunk →
  ecbt {}、ect 0、
  tpe True（空真）、
  crir {None,
  no_chunks}
  （新 reason 首锁）
- **空文本分母**——
  双空字符串 →
  tcmp/tcmr 均
  {None,
  empty_expected_
  and_actual}
  （新 reason 首锁）
- **图片无资源**——
  image 元素
  resource_path
  null → irer 0.0
- **图片坏路径**——
  不存在文件 →
  irer 0.0（存在性
  硬核验复核）
- **跨文档引用**——
  sei 指向其他
  document id →
  crir 0.0
- forbidden tokens 第七百八十六批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import \
    compute_automatic_metrics


def _mk(elements, chunks):
    return {
        "schema_version": "1.0",
        "document_id": "d", "source_hash": "x",
        "source_type": "text",
        "source_path": "t.txt",
        "parser_name": "f", "parser_version": "1",
        "relations": [], "warnings": [],
        "errors": [], "metadata": {},
        "elements": elements, "chunks": chunks}


def _el(i, type_="paragraph", content="ab",
        rp=None):
    return {"element_id": "e%d" % i, "type": type_,
            "source_locator": {"line": i},
            "parent_id": None, "content": content,
            "resource_path": rp,
            "confidence": 0.9, "metadata": {}}


def _ch(i, text="ab", sei=None):
    return {"chunk_id": "c%d" % i, "text": text,
            "source_element_ids":
                sei if sei is not None
                else ["e%d" % i],
            "source_spans": [],
            "metadata": {}}


def _m(elements, chunks):
    return compute_automatic_metrics(
        _mk(elements, chunks), None, "text", None)


# ---------- 空 doc 面 ----------

def test_empty_doc_ecbt_empty_dict_batch542():
    assert _m([], [])[
        "element_count_by_type"] == {
        "value": {}, "reason": None}


def test_empty_doc_ect_zero_batch542():
    assert _m([], [])["element_count_total"] == {
        "value": 0, "reason": None}


def test_empty_doc_tpe_true_batch542():
    assert _m([], [])[
        "text_preservation_equal"] == {
        "value": True, "reason": None}


def test_empty_doc_crir_no_chunks_batch542():
    assert _m([], [])[
        "chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"}


# ---------- 空文本分母 ----------

def test_empty_text_tcmp_null_batch542():
    m = _m([_el(0, content="")],
           [_ch(0, text="")])
    assert m["text_char_multiset_precision"] == {
        "value": None,
        "reason": "empty_expected_and_actual"}


def test_empty_text_tcmr_null_batch542():
    m = _m([_el(0, content="")],
           [_ch(0, text="")])
    assert m["text_char_multiset_recall"] == {
        "value": None,
        "reason": "empty_expected_and_actual"}


def test_empty_text_tpe_true_batch542():
    m = _m([_el(0, content="")],
           [_ch(0, text="")])
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}


# ---------- 图片无资源 ----------

def test_image_null_rp_irer_zero_batch542():
    m = _m([_el(0, "image", None, None)],
           [_ch(0, text="", sei=["e0"])])
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- 图片坏路径 ----------

def test_image_bad_path_irer_zero_batch542():
    m = _m([_el(0, "image", None,
                "no/such/file.png")],
           [_ch(0, text="", sei=["e0"])])
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


def test_image_bad_path_not_null_batch542():
    m = _m([_el(0, "image", None,
                "no/such/file.png")],
           [_ch(0, text="", sei=["e0"])])
    assert m[
        "image_resource_exists_ratio"][
        "reason"] is None


# ---------- 跨文档引用 ----------

def test_cross_doc_ref_crir_zero_batch542():
    m = _m([_el(0)],
           [_ch(0, text="ab",
                sei=["other-doc::e9"])])
    assert m["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


def test_cross_doc_ref_vs_good_batch542():
    bad = _m([_el(0)],
             [_ch(0, text="ab",
                  sei=["other-doc::e9"])])
    good = _m([_el(0)], [_ch(0, text="ab")])
    assert bad["chunk_reference_intact_ratio"][
        "value"] == 0.0
    assert good["chunk_reference_intact_ratio"][
        "value"] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_new_reasons_batch542():
    src = _src()
    assert '"no_chunks"' in src
    assert '"empty_expected_and_actual"' in src


# ---------- forbidden tokens 第七百八十六批 ----------

def test_source_no_eval_batch542():
    assert "eval(" not in _src()


def test_source_no_exec_batch542():
    assert "exec(" not in _src()


def test_source_no_compile_batch542():
    assert "compile(" not in _src()


def test_source_no_globals_batch542():
    assert "globals(" not in _src()


def test_source_no_locals_batch542():
    assert "locals(" not in _src()


def test_source_no_os_system_batch542():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch542():
    assert "subprocess" not in _src()


def test_source_no_popen_batch542():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch542():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch542():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch542():
    assert "socket" not in _src()


def test_source_no_requests_batch542():
    assert "requests" not in _src()


def test_source_no_urllib_batch542():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch542():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch542():
    assert "yield" not in _src()


def test_source_no_async_await_batch542():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch542():
    assert _src().count("open(") == 0
