"""evaluation/schema.py 第二百一十五轮 edges 测试（Round 771）。

补强 edges76-78 未触及的角度（第一百三十五批）。

新角度：
- 三错误排序（list 前缀序）：['documents',0] < ['documents',0,
  'source_type'] < ['documents',1] —— 短前缀先、同前缀按子路径；
  head 取排序后第一条（addProps），消息 "(3 处)"
- required 缺失的 flat 行：schema_path == ['required']、
  path == []（顶层）
- SCHEMAS_DIR 恰 4 个 schema 文件（annotation / document /
  evaluation-report / manifest，document 是业务输出 schema 同居）
- validate_file 接受 str 路径 → 合法清单返回 None
- evaluation-report 顶层：required 恰 5 键（expected_failures
  不在 required 中，可选）、additionalProperties False
- wall_time_seconds.properties 5 键：chunk_reason / parse_reason
  是纯 string（非 [string,null]，reason 必填字符串），
  total/parse/chunk 是 [number,null]
- per_doc additionalProperties False；metrics 定义仅 {"type":
  "object"}（自由形，不锁每个 metric 的结构 —— 与 $defs 的
  精确锁对照）
- forbidden tokens 第二百四十一批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


def _rep():
    return load_schema("evaluation-report.schema.json")


# ---------- 三错误前缀排序 ----------

def test_three_errors_prefix_ordering_batch54():
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d", "path": "samples/a.pdf",
                 "source_type": "bogus", "extra_key": 1},
                "not-an-object"]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    paths = [r["path"] for r in ei.value.errors]
    assert paths == [["documents", 0],
                     ["documents", 0, "source_type"],
                     ["documents", 1]]
    assert "(3 处)" in str(ei.value)
    assert "Additional properties are not allowed" in str(ei.value)


def test_required_miss_flat_row_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0", "documents": []},
                 "manifest.schema.json")
    row = ei.value.errors[0]
    assert row["path"] == []
    assert row["schema_path"] == ["required"]
    assert "is a required property" in row["message"]


# ---------- SCHEMAS_DIR 文件集 ----------

def test_schemas_dir_exactly_four_files_batch54():
    assert sorted(p.name for p in SCHEMAS_DIR.glob("*.json")) == [
        "annotation.schema.json", "document.schema.json",
        "evaluation-report.schema.json", "manifest.schema.json"]


# ---------- validate_file str 路径 ----------

def test_validate_file_str_path_ok_batch54():
    tmp = Path(tempfile.mkdtemp())
    mf = tmp / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    assert validate_file(str(mf), "manifest.schema.json") is None


# ---------- evaluation-report 顶层 ----------

def test_report_top_required_five_batch54():
    rep = _rep()
    assert rep["required"] == ["report_version", "provenance", "devset",
                               "summary", "per_doc"]
    assert rep["additionalProperties"] is False
    assert "expected_failures" in rep["properties"]


def test_wall_time_properties_five_keys_batch54():
    wt = _rep()["$defs"]["per_doc"]["properties"]["wall_time_seconds"]
    assert sorted(wt["properties"]) == ["chunk", "chunk_reason", "parse",
                                        "parse_reason", "total"]
    assert wt["properties"]["chunk_reason"]["type"] == "string"
    assert wt["properties"]["parse_reason"]["type"] == "string"
    for k in ("total", "parse", "chunk"):
        assert wt["properties"][k]["type"] == ["number", "null"]


def test_per_doc_addprops_and_metrics_freeform_batch54():
    rep = _rep()
    pd = rep["$defs"]["per_doc"]
    assert pd["additionalProperties"] is False
    md = pd["properties"]["metrics"]
    assert sorted(md) == ["type"]
    assert md["type"] == "object"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_sort_and_flat_batch54():
    src = _src()
    assert "sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert '"schema_path": list(err.absolute_schema_path)' in src
    assert "Draft202012Validator(schema)" in src


# ---------- forbidden tokens 第二百四十一批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch54():
    assert _src().count("open(") == 2
