"""evaluation/schema.py 第三百零六轮 edges 测试（Round 862）。

补强 edges91 未触及的角度（第二百三十七批，probe 实证）。

新角度：
- annotation 顶层 required 恰 2 项 + additionalProperties False
- boundary_anchor $defs：required [marker, position]、
  props 恰 {marker, position, reason}、addProps False
- report per_doc $defs：required 4 项、addProps False
- wall_time_seconds required 恰 [total, parse, chunk]
- 两个 Schema 的 $defs 名称集合
- annotation 顶层多余键 → path=[] + Additional properties
- devset_status 枚举错：message + schema_path 尾段 "enum"
- validate_file 收 str 路径；不存在 → FileNotFoundError
- forbidden tokens 第三百三十二批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- annotation 顶层 ----------

def test_annotation_top_required_two_batch60():
    s = load_schema("annotation.schema.json")
    assert s["required"] == ["annotation_version", "doc_id"]
    assert s["additionalProperties"] is False


def test_annotation_top_extra_key_rejected_batch60():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"annotation_version": "1.0",
                  "doc_id": "d", "zz": 1},
                 "annotation.schema.json")
    e = ei.value.errors[0]
    assert e["path"] == []
    assert "Additional properties are not allowed" in e["message"]


# ---------- boundary_anchor ----------

def test_boundary_anchor_def_shape_batch60():
    s = load_schema("annotation.schema.json")
    ba = s["$defs"]["boundary_anchor"]
    assert ba["required"] == ["marker", "position"]
    assert ba["additionalProperties"] is False
    assert sorted(ba["properties"]) == ["marker", "position",
                                        "reason"]


def test_annotation_defs_only_boundary_anchor_batch60():
    s = load_schema("annotation.schema.json")
    assert list(s["$defs"]) == ["boundary_anchor"]


# ---------- report per_doc ----------

def test_report_per_doc_def_shape_batch60():
    s = load_schema("evaluation-report.schema.json")
    d = s["$defs"]["per_doc"]
    assert d["required"] == ["doc_id", "source_type",
                             "metrics", "wall_time_seconds"]
    assert d["additionalProperties"] is False


def test_wall_time_required_three_batch60():
    s = load_schema("evaluation-report.schema.json")
    wt = s["$defs"]["per_doc"]["properties"]["wall_time_seconds"]
    assert wt["required"] == ["total", "parse", "chunk"]


def test_report_defs_five_named_batch60():
    s = load_schema("evaluation-report.schema.json")
    assert sorted(s["$defs"]) == [
        "devset", "expected_failure_result", "per_doc",
        "provenance", "summary"]


# ---------- 枚举错 ----------

def test_devset_status_enum_error_batch60():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0",
                  "devset_status": "x", "documents": []},
                 "manifest.schema.json")
    e = ei.value.errors[0]
    assert e["path"] == ["devset_status"]
    assert "'x' is not one of ['complete', 'incomplete']" \
        in e["message"]
    assert e["schema_path"][-1] == "enum"
    assert "校验失败 (1 处)：" in str(ei.value)
    assert "@ path=['devset_status']" in str(ei.value)


# ---------- validate_file ----------

def test_validate_file_str_path_batch60(tmp_path):
    f = tmp_path / "m.json"
    f.write_text('{"manifest_version": "1.0", '
                 '"devset_status": "incomplete", '
                 '"documents": []}', encoding="utf-8")
    assert validate_file(str(f), "manifest.schema.json") is None


def test_validate_file_missing_fnf_batch60(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "nope.json",
                      "manifest.schema.json")
    assert "待校验文件不存在" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch60():
    src = _src()
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src
    assert "self.errors = errors or []" in src


# ---------- forbidden tokens 第三百三十二批 ----------

def test_source_no_eval_batch60():
    assert "eval(" not in _src()


def test_source_no_exec_batch60():
    assert "exec(" not in _src()


def test_source_no_compile_batch60():
    assert "compile(" not in _src()


def test_source_no_globals_batch60():
    assert "globals(" not in _src()


def test_source_no_locals_batch60():
    assert "locals(" not in _src()


def test_source_no_os_system_batch60():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch60():
    assert "subprocess" not in _src()


def test_source_no_popen_batch60():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch60():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch60():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch60():
    assert "socket" not in _src()


def test_source_no_requests_batch60():
    assert "requests" not in _src()


def test_source_no_urllib_batch60():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch60():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch60():
    assert "yield" not in _src()


def test_source_no_async_await_batch60():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch60():
    assert _src().count("open(") == 2
