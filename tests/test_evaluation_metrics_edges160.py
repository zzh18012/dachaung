"""evaluation/metrics.py 第五百八十一轮 edges 测试（Round 1349）。

补强 edges159 未触及的角度（第七百二十一批，probe 实证）。

新角度（schema_valid 细粒度触发 / 指标独立性）：
- **基板全绿**——
  source_type 'text'
  + line 1 + sv
  0.1.0 + sha64 →
  schema_valid
  {True, None}
  （metrics 级
  text 型合法
  首锁）
- **单字段触发**
  ——line 0 / line
  -5 / sv 9.9 /
  sha 'x' 各自
  翻 False
- **独立性**——
  变异板 vs 基板
  diff keys ==
  ['schema_valid']
  （13 项指标与
  schema 合法性
  解耦首锁）
- **14 键直调**
  ——直调输出恰
  14 键（runner
  级 20 键含
  annotation）
- forbidden tokens 第七百九十批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import \
    compute_automatic_metrics

SHA = "a" * 64

KEYS_14 = [
    "chunk_reference_intact_ratio",
    "docx_locator_valid_ratio",
    "element_count_by_type",
    "element_count_total",
    "error_code",
    "heading_boundary_compliance",
    "image_resource_exists_ratio",
    "pdf_locator_valid_ratio",
    "pipeline_success",
    "schema_valid",
    "silent_drop_count",
    "text_char_multiset_precision",
    "text_char_multiset_recall",
    "text_preservation_equal"]


def _doc(line=1, sv="0.1.0", sha=SHA):
    return {
        "schema_version": sv, "document_id": "d",
        "source_hash": sha, "source_type": "text",
        "source_path": "t.txt", "parser_name": "f",
        "parser_version": "1", "relations": [],
        "warnings": [], "errors": [], "metadata": {},
        "elements": [{
            "element_id": "e0", "type": "paragraph",
            "source_locator": {"line": line},
            "parent_id": None, "content": "ab",
            "resource_path": None, "confidence": 0.9,
            "metadata": {}}],
        "chunks": [{
            "chunk_id": "c0", "text": "ab",
            "source_element_ids": ["e0"],
            "source_spans": [], "metadata": {}}]}


def _m(**kw):
    return compute_automatic_metrics(
        _doc(**kw), None, "text", None)


# ---------- 基板全绿 ----------

def test_base_schema_valid_true_batch547():
    assert _m()["schema_valid"] == {
        "value": True, "reason": None}


def test_base_tpe_true_batch547():
    assert _m()["text_preservation_equal"] == {
        "value": True, "reason": None}


def test_base_multiset_one_batch547():
    m = _m()
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


def test_base_counts_batch547():
    m = _m()
    assert m["element_count_total"] == {
        "value": 1, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 1}, "reason": None}


def test_base_crir_one_batch547():
    assert _m()["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_base_sdt_no_expectations_batch547():
    assert _m()["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


# ---------- 单字段触发 ----------

def test_line_zero_false_batch547():
    assert _m(line=0)["schema_valid"] == {
        "value": False, "reason": None}


def test_line_negative_false_batch547():
    assert _m(line=-5)["schema_valid"] == {
        "value": False, "reason": None}


def test_bad_version_false_batch547():
    assert _m(sv="9.9")["schema_valid"] == {
        "value": False, "reason": None}


def test_bad_sha_false_batch547():
    assert _m(sha="x")["schema_valid"] == {
        "value": False, "reason": None}


# ---------- 独立性 ----------

def test_line_flip_only_schema_valid_batch547():
    base = _m(line=1)
    bad = _m(line=0)
    diff = [k for k in base if base[k] != bad[k]]
    assert diff == ["schema_valid"]


def test_each_mutation_only_schema_batch547():
    base = _m()
    for kw in ({"line": 0}, {"line": -5},
               {"sv": "9.9"}, {"sha": "x"}):
        bad = _m(**kw)
        diff = [k for k in base
                if base[k] != bad[k]]
        assert diff == ["schema_valid"], kw


def test_bad_schema_metrics_alive_batch547():
    m = _m(line=0)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["element_count_total"] == {
        "value": 1, "reason": None}
    assert m["pipeline_success"] == {
        "value": True, "reason": None}


# ---------- 14 键直调 ----------

def test_output_key_set_batch547():
    assert sorted(_m().keys()) == KEYS_14


def test_output_key_count_batch547():
    assert len(_m()) == 14


def test_mutation_key_set_stable_batch547():
    assert sorted(_m(line=0).keys()) == KEYS_14


# ---------- 无 chunks 面 ----------

def _doc_nochunks():
    d = _doc()
    del d["chunks"]
    return d


def test_nochunks_schema_false_batch547():
    m = compute_automatic_metrics(
        _doc_nochunks(), None, "text", None)
    assert m["schema_valid"] == {
        "value": False, "reason": None}


def test_nochunks_crir_no_chunks_batch547():
    m = compute_automatic_metrics(
        _doc_nochunks(), None, "text", None)
    assert m["chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"}


def test_nochunks_tpe_false_batch547():
    m = compute_automatic_metrics(
        _doc_nochunks(), None, "text", None)
    assert m["text_preservation_equal"] == {
        "value": False, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_delayed_schema_import_batch547():
    src = _src()
    assert ("from evaluation.schema_validation "
            "import document_passes_schema") in src
    assert "schema_check_exception:{type(e).__name__}" \
        in src


def test_source_pdf_bbox_tuple_batch547():
    assert '_PDF_BBOX_REQUIRED_TYPES = (' in _src()


# ---------- forbidden tokens 第七百九十批 ----------

def test_source_no_eval_batch547():
    assert "eval(" not in _src()


def test_source_no_exec_batch547():
    assert "exec(" not in _src()


def test_source_no_compile_batch547():
    assert "compile(" not in _src()


def test_source_no_globals_batch547():
    assert "globals(" not in _src()


def test_source_no_locals_batch547():
    assert "locals(" not in _src()


def test_source_no_os_system_batch547():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch547():
    assert "subprocess" not in _src()


def test_source_no_popen_batch547():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch547():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch547():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch547():
    assert "socket" not in _src()


def test_source_no_requests_batch547():
    assert "requests" not in _src()


def test_source_no_urllib_batch547():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch547():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch547():
    assert "yield" not in _src()


def test_source_no_async_await_batch547():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch547():
    assert _src().count("open(") == 0
