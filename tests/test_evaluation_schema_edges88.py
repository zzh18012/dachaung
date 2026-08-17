"""evaluation/schema.py 第二百七十八轮 edges 测试（Round 834）。

补强 edges87 未触及的角度（第二百零八批）。

新角度：
- load_schema 未知名称 → FileNotFoundError「Schema 文件不存在」；
  validate 对未知 schema 同样穿透
- EvalSchemaError 默认 errors == []
- 多错误按 absolute_path 排序：devset_status 排在
  manifest_version 之前（与 dict 书写序无关）
- 异常 message 头部「Schema '...' 校验失败 (N 处)：」
- validate(None) → "None is not of type 'object'"
- load_schema 每次调用读盘返回新 dict（is not / ==）
- validate_file 垃圾文本 → json.JSONDecodeError 穿透
- const 错误的 schema_path 全路径三段
- forbidden tokens 第三百零四批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- 未知 Schema ----------

def test_load_schema_missing_fnf_batch55():
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("nope.schema.json")
    assert "Schema 文件不存在" in str(ei.value)


def test_validate_unknown_schema_fnf_batch55():
    with pytest.raises(FileNotFoundError):
        validate({}, "nope.schema.json")


# ---------- EvalSchemaError 默认 ----------

def test_eval_schema_error_default_errors_batch55():
    e = EvalSchemaError("m")
    assert e.errors == []


# ---------- 多错误排序 ----------

def test_multi_error_sorted_by_path_batch55():
    bad = {"manifest_version": "9", "devset_status": "bogus",
           "documents": []}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    assert len(ei.value.errors) == 2
    assert ei.value.errors[0]["path"] == ["devset_status"]
    assert ei.value.errors[1]["path"] == ["manifest_version"]
    assert str(ei.value).startswith(
        "Schema 'manifest.schema.json' 校验失败 (2 处)：")


# ---------- None instance ----------

def test_validate_none_instance_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate(None, "manifest.schema.json")  # type: ignore[arg-type]
    assert ei.value.errors[0]["path"] == []
    assert ei.value.errors[0]["message"] == \
        "None is not of type 'object'"


# ---------- load_schema 新 dict ----------

def test_load_schema_fresh_dict_batch55():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b
    assert "properties" in a


# ---------- 垃圾 JSON ----------

def test_validate_file_garbage_json_batch55(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json at all", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


# ---------- const schema_path 三段 ----------

def test_const_error_schema_path_batch55():
    bad = {"manifest_version": "9", "devset_status": "incomplete",
           "documents": []}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    er = ei.value.errors[0]
    assert er["schema_path"] == ["properties",
                                 "manifest_version", "const"]
    assert er["message"] == "'1.0' was expected"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert "校验失败 ({len(errors)} 处)：" in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src


# ---------- forbidden tokens 第三百零四批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch55():
    assert _src().count("open(") == 2
