"""evaluation/schema.py 第三百六十二轮 edges 测试（Round 918）。

补强 edges99 未触及的角度（第二百九十四批，probe 实证）。

新角度：
- evaluation-report 顶层 required 恰 5 项有序——
  expected_failures 不在 required（可选），但顶层封闭
- $defs 五名：devset / expected_failure_result / per_doc /
  provenance / summary
- per_doc def：required 4 项、封闭、props 4；内联
  wall_time_seconds：required 仅 [total, parse, chunk]
  （reason 可选）、三计时 [number,null] minimum 0、
  两 reason string
- metrics prop 仅 {"type": "object"}——指标值本身不做
  Schema 级约束（宽松现状锁定）
- expected_failure_result def 全形（actual_error_code 双类型、
  matches boolean、封闭、required 4）
- devset def：required 6、封闭、categories_covered string 数组
- 三个 schema 全部声明 draft 2020-12 且顶层封闭
- EvalSchemaError 默认 errors []；自定义 errors 保留
- load_schema 未知名 → FileNotFoundError "Schema 文件不存在"；
  validate_file 缺文件 → "待校验文件不存在"；坏 JSON →
  JSONDecodeError 冒出
- 多错误按 absolute_path 排序，重复路径保留（() 恒首位）
- forbidden tokens 第三百八十八批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- evaluation-report 顶层 ----------

def test_report_top_required_five_batch116():
    r = load_schema("evaluation-report.schema.json")
    assert r["required"] == ["report_version", "provenance",
                             "devset", "summary", "per_doc"]
    assert "expected_failures" not in r["required"]  # 可选键
    assert r["additionalProperties"] is False


def test_report_defs_five_names_batch116():
    r = load_schema("evaluation-report.schema.json")
    assert sorted(r["$defs"]) == [
        "devset", "expected_failure_result", "per_doc",
        "provenance", "summary",
    ]


# ---------- per_doc def ----------

def test_per_doc_def_shape_batch116():
    pd = load_schema("evaluation-report.schema.json")["$defs"][
        "per_doc"]
    assert pd["required"] == ["doc_id", "source_type", "metrics",
                              "wall_time_seconds"]
    assert pd["additionalProperties"] is False
    assert sorted(pd["properties"]) == ["doc_id", "metrics",
                                        "source_type",
                                        "wall_time_seconds"]


def test_wall_time_inline_shape_batch116():
    pd = load_schema("evaluation-report.schema.json")["$defs"][
        "per_doc"]
    w = pd["properties"]["wall_time_seconds"]
    assert w["required"] == ["total", "parse", "chunk"]
    assert w["additionalProperties"] is False
    assert w["properties"]["total"] == {
        "type": ["number", "null"], "minimum": 0}
    assert w["properties"]["parse_reason"] == {"type": "string"}
    assert w["properties"]["chunk_reason"] == {"type": "string"}


def test_metrics_prop_unconstrained_batch116():
    pd = load_schema("evaluation-report.schema.json")["$defs"][
        "per_doc"]
    assert pd["properties"]["metrics"] == {"type": "object"}


# ---------- expected_failure_result def ----------

def test_efr_def_full_shape_batch116():
    efr = load_schema("evaluation-report.schema.json")["$defs"][
        "expected_failure_result"]
    assert efr["required"] == ["doc_id", "expected_error_code",
                               "actual_error_code", "matches"]
    assert efr["additionalProperties"] is False
    props = efr["properties"]
    assert props["doc_id"] == {"type": "string"}
    assert props["expected_error_code"] == {"type": "string"}
    assert props["actual_error_code"] == {"type": ["string", "null"]}
    assert props["matches"] == {"type": "boolean"}


# ---------- devset def ----------

def test_devset_def_shape_batch116():
    ds = load_schema("evaluation-report.schema.json")["$defs"][
        "devset"]
    assert ds["required"] == ["status", "file_count",
                              "content_group_count", "pdf_count",
                              "docx_count", "categories_covered"]
    assert ds["additionalProperties"] is False
    assert ds["properties"]["categories_covered"] == {
        "type": "array", "items": {"type": "string"}}


# ---------- 三 schema 共性 ----------

def test_three_schemas_draft_and_closed_batch116():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"):
        s = load_schema(name)
        assert s["$schema"] == (
            "https://json-schema.org/draft/2020-12/schema"), name
        assert s["additionalProperties"] is False, name


# ---------- EvalSchemaError ----------

def test_error_default_empty_errors_batch116():
    e = EvalSchemaError("m")
    assert e.errors == []
    assert str(e) == "m"


def test_error_custom_errors_preserved_batch116():
    e = EvalSchemaError("m2", errors=[{"a": 1}])
    assert e.errors == [{"a": 1}]


# ---------- 缺文件与坏 JSON ----------

def test_load_schema_missing_file_batch116():
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("nope.schema.json")
    assert str(ei.value).startswith("Schema 文件不存在: ")


def test_validate_file_missing_batch116(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "x.json", "manifest.schema.json")
    assert str(ei.value).startswith("待校验文件不存在: ")


def test_validate_file_bad_json_batch116(tmp_path):
    f = tmp_path / "b.json"
    f.write_text("nope", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


# ---------- 错误排序 ----------

def test_error_paths_sorted_duplicates_kept_batch116():
    with pytest.raises(EvalSchemaError) as ei:
        validate(
            {"manifest_version": 4,
             "documents": [{"doc_id": 1, "path": 2,
                            "source_type": 3}]},
            "manifest.schema.json")
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert paths[0] == ()
    assert paths == sorted(paths)
    assert paths.count(("manifest_version",)) == 2  # type + const


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch116():
    src = _src()
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src
    assert ("errors = sorted(validator.iter_errors(instance), "
            "key=lambda e: list(e.absolute_path))") in src


# ---------- forbidden tokens 第三百八十八批 ----------

def test_source_no_eval_batch116():
    assert "eval(" not in _src()


def test_source_no_exec_batch116():
    assert "exec(" not in _src()


def test_source_no_compile_batch116():
    assert "compile(" not in _src()


def test_source_no_globals_batch116():
    assert "globals(" not in _src()


def test_source_no_locals_batch116():
    assert "locals(" not in _src()


def test_source_no_os_system_batch116():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch116():
    assert "subprocess" not in _src()


def test_source_no_popen_batch116():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch116():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch116():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch116():
    assert "socket" not in _src()


def test_source_no_requests_batch116():
    assert "requests" not in _src()


def test_source_no_urllib_batch116():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch116():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch116():
    assert "yield" not in _src()


def test_source_no_async_await_batch116():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch116():
    assert _src().count("open(") == 2
