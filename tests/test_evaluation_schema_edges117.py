"""evaluation/schema.py 第四百七十四轮 edges 测试（Round 1030）。

补强 edges116 未触及的角度（第四百零六批，probe 实证）。

新角度（同一载荷三 schema 判定矩阵）：
- 合法 annotation 实例：annotation RS 通过；manifest RS
  恰 4 错（3 个 required：manifest_version/
  devset_status/documents + 1 个 additionalProperties）；
  evaluation-report RS 恰 6 错（5 个 required：
  report_version/provenance/devset/summary/per_doc +
  1 个 additionalProperties）
- 两边的 additionalProperties 错误都点名标注专属键
  （annotation_version/doc_id/chunk_boundary_anchors）
- 由此锁 required 集合：manifest 只 3 必填、report 只
  5 必填——expected_failures 在两个 schema 都是可选
- 全部错误 path 都是 []（顶层缺键不产生下钻路径）
- forbidden tokens 第五百零一批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (EvalSchemaError, validate)

_ANN = {
    "annotation_version": "1.0", "doc_id": "d1",
    "chunk_boundary_anchors": [
        {"marker": "AB", "position": "after"}]}


# ---------- 判定矩阵 ----------

def test_annotation_payload_three_verdicts_batch228():
    validate(_ANN, "annotation.schema.json")
    with pytest.raises(EvalSchemaError) as mi:
        validate(_ANN, "manifest.schema.json")
    assert len(mi.value.errors) == 4
    with pytest.raises(EvalSchemaError) as ri:
        validate(_ANN, "evaluation-report.schema.json")
    assert len(ri.value.errors) == 6


def test_manifest_required_set_is_three_batch228():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_ANN, "manifest.schema.json")
    required = [e["message"] for e in ei.value.errors
                if "required property" in e["message"]]
    assert required == [
        "'manifest_version' is a required property",
        "'devset_status' is a required property",
        "'documents' is a required property"]


def test_report_required_set_is_five_batch228():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_ANN, "evaluation-report.schema.json")
    required = [e["message"] for e in ei.value.errors
                if "required property" in e["message"]]
    assert required == [
        "'report_version' is a required property",
        "'provenance' is a required property",
        "'devset' is a required property",
        "'summary' is a required property",
        "'per_doc' is a required property"]


def test_both_closed_schemas_name_annotation_keys_batch228():
    with pytest.raises(EvalSchemaError) as mi:
        validate(_ANN, "manifest.schema.json")
    addl = [e["message"] for e in mi.value.errors
            if "Additional properties" in e["message"]]
    assert len(addl) == 1
    for key in ("annotation_version", "doc_id",
                "chunk_boundary_anchors"):
        assert f"'{key}'" in addl[0]
    with pytest.raises(EvalSchemaError) as ri:
        validate(_ANN, "evaluation-report.schema.json")
    addl_r = [e["message"] for e in ri.value.errors
              if "Additional properties" in e["message"]]
    assert len(addl_r) == 1
    assert "annotation_version" in addl_r[0]


def test_all_error_paths_top_level_batch228():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_ANN, "manifest.schema.json")
    assert all(e["path"] == [] for e in ei.value.errors)
    with pytest.raises(EvalSchemaError) as ri:
        validate(_ANN, "evaluation-report.schema.json")
    assert all(e["path"] == [] for e in ri.value.errors)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch228():
    src = _src()
    assert ("errors = sorted(validator.iter_errors(instance)"
            in src)
    assert '"schema_path": list(err.absolute_schema_path),' \
        in src
    assert "if not errors:" in src


# ---------- forbidden tokens 第五百零一批 ----------

def test_source_no_eval_batch228():
    assert "eval(" not in _src()


def test_source_no_exec_batch228():
    assert "exec(" not in _src()


def test_source_no_compile_batch228():
    assert "compile(" not in _src()


def test_source_no_globals_batch228():
    assert "globals(" not in _src()


def test_source_no_locals_batch228():
    assert "locals(" not in _src()


def test_source_no_os_system_batch228():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch228():
    assert "subprocess" not in _src()


def test_source_no_popen_batch228():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch228():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch228():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch228():
    assert "socket" not in _src()


def test_source_no_requests_batch228():
    assert "requests" not in _src()


def test_source_no_urllib_batch228():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch228():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch228():
    assert "yield" not in _src()


def test_source_no_async_await_batch228():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch228():
    assert _src().count("open(") == 2
