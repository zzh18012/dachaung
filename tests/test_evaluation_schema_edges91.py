"""evaluation/schema.py 第二百九十九轮 edges 测试（Round 855）。

补强 edges90 未触及的角度（第二百二十九批，probe 实证）。

新角度：
- manifest 顶层 required 恰 3 项
- document.schema.json 顶层 required 恰 13 项（业务文档
  模型全字段必填的锁定）
- manifest 的 documents.items 用 $ref 指向 $defs（解释了
  edges89 探针在 items 层看不到 required 的原因）
- SCHEMAS_DIR 是名为 schemas 的目录
- 四个 Schema 全部通过 Draft202012Validator.check_schema
  （Schema 自身的元校验）
- forbidden tokens 第三百二十五批
"""

from __future__ import annotations

import inspect

import pytest
from jsonschema import Draft202012Validator

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    load_schema,
)

_ALL = ["manifest.schema.json", "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json"]


# ---------- manifest 顶层 ----------

def test_manifest_top_required_batch55():
    s = load_schema("manifest.schema.json")
    assert s["required"] == ["manifest_version",
                             "devset_status", "documents"]


# ---------- document 顶层 ----------

def test_document_top_required_thirteen_batch55():
    s = load_schema("document.schema.json")
    assert s["required"] == [
        "schema_version", "document_id", "source_path",
        "source_type", "source_hash", "parser_name",
        "parser_version", "elements", "chunks", "relations",
        "warnings", "errors", "metadata"]


# ---------- documents $ref ----------

def test_documents_items_ref_defs_batch55():
    s = load_schema("manifest.schema.json")
    items = s["properties"]["documents"]["items"]
    assert list(items.keys()) == ["$ref"]
    assert items["$ref"].startswith("#/$defs/")
    assert "$defs" in s
    target = items["$ref"].rsplit("/", 1)[-1]
    assert target in s["$defs"]


# ---------- 目录 ----------

def test_schemas_dir_is_dir_named_schemas_batch55():
    assert SCHEMAS_DIR.is_dir()
    assert SCHEMAS_DIR.name == "schemas"


# ---------- Schema 元校验 ----------

@pytest.mark.parametrize("name", _ALL)
def test_check_schema_all_pass_batch55(name):
    assert Draft202012Validator.check_schema(
        load_schema(name)) is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent / \"schemas\"" in src
    assert "from jsonschema import Draft202012Validator" in src


# ---------- forbidden tokens 第三百二十五批 ----------

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
