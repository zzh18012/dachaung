"""evaluation/schema.py 第二百二十九轮 edges 测试（Round 785）。

补强 edges78-80 未触及的角度（第一百四十九批）。

新角度：
- 混合路径排序 head：错 anchor（path
  ['chunk_boundary_anchors', 0]）排在错 doc_id（['doc_id']）前
  —— 列表比较 "c" < "d"，共 3 处错误
- 空 path 行：instance 传 list → flat 行 path []、
  schema_path ['type']、message "[] is not of type 'object'"
- load_schema 未知名 → FileNotFoundError 带完整绝对路径
- EvalSchemaError 默认 errors == []（单参构造）
- validate_file 坏 JSON / UTF-8 BOM → json.JSONDecodeError 原样
  传播（不包装成 EvalSchemaError）
- devset_status 枚举拒绝信息精确：
  "'unfinished' is not one of ['complete', 'incomplete']"
- 完整报告 fixture 首次锁定：合法通过；report_version "1.2" →
  flat 行 path ['report_version']、schema_path
  ['properties', 'report_version', 'const']、"'1.1' was expected"
- 顶层额外键：additionalProperties 拒 "'zzz' was unexpected"；
  两处错误 → 消息含 "(2 处)"
- load_schema 两次：值相等、对象独立（无缓存）
- forbidden tokens 第二百五十五批
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

_BASE_ANN = {"annotation_version": "1.0", "doc_id": ""}


def _tmp():
    return Path(tempfile.mkdtemp())


_FULL_REPORT = {
    "report_version": "1.1",
    "provenance": {
        "run_timestamp_iso": "2026-08-17T00:00:00+00:00",
        "git_commit": None,
        "git_dirty": False,
        "evaluator_version": "1.1",
        "report_version": "1.1",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "dependencies": {},
        "max_chars": 800,
    },
    "devset": {
        "status": "incomplete",
        "file_count": 0,
        "content_group_count": 0,
        "pdf_count": 0,
        "docx_count": 0,
        "categories_covered": [],
    },
    "summary": {
        "counts": {},
        "success_rates": {},
        "ratio_macro_averages": {},
        "silent_drop_count": 0,
    },
    "per_doc": [],
}


# ---------- 混合路径排序 ----------

def test_mixed_path_sort_head_batch54():
    ann = dict(_BASE_ANN,
               chunk_boundary_anchors=[{"marker": 5}])
    with pytest.raises(EvalSchemaError) as ei:
        validate(ann, "annotation.schema.json")
    assert ei.value.errors[0]["path"] == ["chunk_boundary_anchors", 0]
    assert len(ei.value.errors) == 3


# ---------- 空 path 行 ----------

def test_list_instance_empty_path_row_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate([], "manifest.schema.json")
    row = ei.value.errors[0]
    assert row["path"] == []
    assert row["schema_path"] == ["type"]
    assert row["message"] == "[] is not of type 'object'"


# ---------- load_schema 未知名 ----------

def test_load_schema_missing_file_error_batch54():
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("nope.schema.json")
    assert str(ei.value) == (
        f"Schema 文件不存在: {SCHEMAS_DIR / 'nope.schema.json'}")


# ---------- EvalSchemaError 默认 ----------

def test_schema_error_default_errors_batch54():
    e = EvalSchemaError("m")
    assert e.errors == []
    assert str(e) == "m"


# ---------- 坏 JSON / BOM ----------

def test_validate_file_bad_json_raises_batch54():
    f = _tmp() / "bad.json"
    f.write_text("{bad", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_bom_raises_batch54():
    f = _tmp() / "bom.json"
    f.write_bytes(b"\xef\xbb\xbf{}")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


# ---------- devset_status 枚举 ----------

def test_devset_status_enum_message_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0",
                  "devset_status": "unfinished", "documents": []},
                 "manifest.schema.json")
    assert ei.value.errors[0]["message"] == \
        "'unfinished' is not one of ['complete', 'incomplete']"


# ---------- 完整报告 const flat 行 ----------

def test_full_report_valid_batch54():
    validate(_FULL_REPORT, "evaluation-report.schema.json")


def test_report_version_const_flat_row_batch54():
    bad = dict(_FULL_REPORT)
    bad["report_version"] = "1.2"
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "evaluation-report.schema.json")
    row = ei.value.errors[0]
    assert row["path"] == ["report_version"]
    assert row["schema_path"] == ["properties", "report_version", "const"]
    assert row["message"] == "'1.1' was expected"


# ---------- 额外键与错误计数 ----------

def test_additional_top_property_rejected_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0",
                  "devset_status": "incomplete",
                  "documents": [], "zzz": 1},
                 "manifest.schema.json")
    assert ei.value.errors[0]["message"] == \
        "Additional properties are not allowed ('zzz' was unexpected)"


def test_two_errors_count_in_message_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0",
                  "devset_status": "unfinished",
                  "documents": [], "zzz": 1},
                 "manifest.schema.json")
    assert "(2 处)" in str(ei.value)
    assert len(ei.value.errors) == 2


# ---------- 无缓存 ----------

def test_load_schema_no_cache_batch54():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b
    assert a is not b


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_validator_lines_batch54():
    src = _src()
    assert "Draft202012Validator" in src
    assert "key=lambda e: list(e.absolute_path)" in src


# ---------- forbidden tokens 第二百五十五批 ----------

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
