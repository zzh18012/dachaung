"""evaluation/schema.py 第五百六十四轮 edges 测试（Round 1120）。

补强 edges129 未触及的角度（第四百九十六批，probe 实证）。

新角度（Schema 元校验 / 引用完整性清点）：
- **check_schema 元校验全过**：四个 Schema 全部通过
  Draft202012Validator.check_schema——Schema 本身是合法的
  2020-12 文档（首锁；旧锁只测过 instance 侧校验）
- **check_schema 负对照**：{"type": 123} 抛 SchemaError——
  证明元校验真会咬人，四连过不是空转
- **$ref 完整性清点**：annotation 1 处 / document 12 处 /
  evaluation-report 5 处 / manifest 2 处引用，全部解析到
  本 Schema 的 $defs 键，零悬空（首锁）
- forbidden tokens 第五百九十二批（open 2）
"""

from __future__ import annotations

import inspect

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

import evaluation.schema as schema_mod
from evaluation.schema import load_schema

_NAMES = ["annotation.schema.json", "document.schema.json",
          "evaluation-report.schema.json",
          "manifest.schema.json"]


# ---------- check_schema 元校验全过 ----------

def test_check_schema_all_four_pass_batch319():
    for name in _NAMES:
        Draft202012Validator.check_schema(load_schema(name))


# ---------- check_schema 负对照 ----------

def test_check_schema_rejects_broken_batch319():
    with pytest.raises(SchemaError):
        Draft202012Validator.check_schema({"type": 123})


# ---------- $ref 完整性清点 ----------

def _collect_refs(node, refs):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                refs.append(v)
            else:
                _collect_refs(v, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, refs)


def test_ref_inventory_and_resolution_batch319():
    expected = {
        "annotation.schema.json": 1,
        "document.schema.json": 12,
        "evaluation-report.schema.json": 5,
        "manifest.schema.json": 2,
    }
    for name, want in expected.items():
        schema = load_schema(name)
        refs: list[str] = []
        _collect_refs(schema, refs)
        assert len(refs) == want
        defs = schema.get("$defs", {})
        for r in refs:
            assert r.startswith("#/$defs/")
            assert r.split("/")[-1] in defs


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch319():
    src = _src()
    assert "errors 给程序看，message 给人看" in src
    assert "分开更清晰" in src


# ---------- forbidden tokens 第五百九十二批 ----------

def test_source_no_eval_batch319():
    assert "eval(" not in _src()


def test_source_no_exec_batch319():
    assert "exec(" not in _src()


def test_source_no_compile_batch319():
    assert "compile(" not in _src()


def test_source_no_globals_batch319():
    assert "globals(" not in _src()


def test_source_no_locals_batch319():
    assert "locals(" not in _src()


def test_source_no_os_system_batch319():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch319():
    assert "subprocess" not in _src()


def test_source_no_popen_batch319():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch319():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch319():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch319():
    assert "socket" not in _src()


def test_source_no_requests_batch319():
    assert "requests" not in _src()


def test_source_no_urllib_batch319():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch319():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch319():
    assert "yield" not in _src()


def test_source_no_async_await_batch319():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch319():
    assert _src().count("open(") == 2
