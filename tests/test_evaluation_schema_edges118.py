"""evaluation/schema.py 第四百八十一轮 edges 测试（Round 1037）。

补强 edges117 未触及的角度（第四百一十三批，probe 实证）。

新角度（3×3 跨 schema 矩阵收尾）：
- edges117 锁过 annotation 行（PASS / 4 / 6），本批
  补齐其余四格：report→manifest 4 错（3 req+1 addl）、
  report→annotation 3 错（2 req+1 addl）、
  manifest→report 6 错（5 req+1 addl）、
  manifest→annotation 3 错（2 req+1 addl）
- 由此锁 annotation required 集恰 2 键
  （annotation_version / doc_id）；annotation RS 的
  闭集性：manifest 的 documents/devset_status 等键
  全被 additionalProperties 点名
- 全矩阵规律：对角线 PASS、非对角线必 1 个 addl 错、
  required 错数 = 目标 schema 的 required 数（3/5/2）
- forbidden tokens 第五百零八批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate

_REPORT = {"report_version": "1.1", "provenance": {},
           "devset": {}, "summary": {}, "per_doc": [],
           "expected_failures": []}
_MANIFEST = {"manifest_version": "1.0",
             "devset_status": "complete", "documents": [],
             "expected_failures": []}
_ANN = {"annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": []}

_RS = "evaluation-report.schema.json"
_MS = "manifest.schema.json"
_AS = "annotation.schema.json"


def _counts(payload, target):
    with pytest.raises(EvalSchemaError) as ei:
        validate(payload, target)
    errs = ei.value.errors
    req = sum(1 for x in errs if "required" in x["message"])
    addl = sum(1 for x in errs
               if "Additional" in x["message"])
    return len(errs), req, addl


# ---------- 矩阵四格 ----------

def test_report_into_manifest_batch235():
    assert _counts(_REPORT, _MS) == (4, 3, 1)


def test_report_into_annotation_batch235():
    assert _counts(_REPORT, _AS) == (3, 2, 1)


def test_manifest_into_report_batch235():
    assert _counts(_MANIFEST, _RS) == (6, 5, 1)


def test_manifest_into_annotation_batch235():
    assert _counts(_MANIFEST, _AS) == (3, 2, 1)


# ---------- 对角线全 PASS ----------

def test_diagonal_all_pass_batch235():
    validate({
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None, "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-17T00:00:00+08:00"},
        "devset": {"status": "complete", "file_count": 1,
                   "content_group_count": 1, "pdf_count": 1,
                   "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {},
                    "ratio_macro_averages": {},
                    "silent_drop_total": None},
        "per_doc": [], "expected_failures": []}, _RS)
    validate(_MANIFEST, _MS)
    validate(_ANN, _AS)


# ---------- annotation required 恰两键 ----------

def test_annotation_required_two_keys_batch235():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_MANIFEST, _AS)
    req = [x["message"] for x in ei.value.errors
           if "required" in x["message"]]
    assert req == [
        "'annotation_version' is a required property",
        "'doc_id' is a required property"]


def test_annotation_closed_names_manifest_keys_batch235():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_MANIFEST, _AS)
    addl = [x["message"] for x in ei.value.errors
            if "Additional" in x["message"]][0]
    for key in ("manifest_version", "devset_status",
                "documents"):
        assert f"'{key}'" in addl


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch235():
    src = _src()
    assert "def validate(instance" in src
    assert "def validate_file(path" in src
    assert "head = errors[0]" in src


# ---------- forbidden tokens 第五百零八批 ----------

def test_source_no_eval_batch235():
    assert "eval(" not in _src()


def test_source_no_exec_batch235():
    assert "exec(" not in _src()


def test_source_no_compile_batch235():
    assert "compile(" not in _src()


def test_source_no_globals_batch235():
    assert "globals(" not in _src()


def test_source_no_locals_batch235():
    assert "locals(" not in _src()


def test_source_no_os_system_batch235():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch235():
    assert "subprocess" not in _src()


def test_source_no_popen_batch235():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch235():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch235():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch235():
    assert "socket" not in _src()


def test_source_no_requests_batch235():
    assert "requests" not in _src()


def test_source_no_urllib_batch235():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch235():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch235():
    assert "yield" not in _src()


def test_source_no_async_await_batch235():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch235():
    assert _src().count("open(") == 2
