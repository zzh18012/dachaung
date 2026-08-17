"""evaluation/schema.py 第二百三十六轮 edges 测试（Round 792）。

补强 edges81 未触及的角度（第一百五十六批）。

新角度：
- document.schema.json 顶层 required 全 13 键锁定（schema_version …
  metadata）；annotation 合法正例（marker + position）通过且
  validate 显式返回 None
- 未知 schema 名经 validate → load_schema 的 FileNotFoundError
  原样传播（validate 不捕获加载错误）
- 三个评测 schema 顶层 type 恒 "object"
- SCHEMAS_DIR：绝对路径、目录名 "schemas"
- EvalSchemaError 是 Exception 子类
- forbidden tokens 第二百六十二批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
)

_DOC_REQUIRED = [
    "schema_version", "document_id", "source_path", "source_type",
    "source_hash", "parser_name", "parser_version", "elements",
    "chunks", "relations", "warnings", "errors", "metadata",
]


# ---------- document.schema.json required ----------

def test_document_schema_required_locked_batch54():
    doc = load_schema("document.schema.json")
    assert doc["required"] == _DOC_REQUIRED


# ---------- 正例与返回值 ----------

def test_valid_annotation_returns_none_batch54():
    r = validate({"annotation_version": "1.0", "doc_id": "d",
                  "chunk_boundary_anchors": [{"marker": "X",
                                              "position": "after"}]},
                 "annotation.schema.json")
    assert r is None


# ---------- 未知 schema 名传播 ----------

def test_validate_unknown_schema_propagates_batch54():
    with pytest.raises(FileNotFoundError):
        validate({}, "nope.schema.json")


# ---------- 顶层 type ----------

@pytest.mark.parametrize("name", [
    "manifest.schema.json",
    "annotation.schema.json",
    "evaluation-report.schema.json",
])
def test_eval_schemas_top_type_object_batch54(name):
    assert load_schema(name)["type"] == "object"


# ---------- SCHEMAS_DIR ----------

def test_schemas_dir_absolute_named_schemas_batch54():
    assert SCHEMAS_DIR.is_absolute()
    assert SCHEMAS_DIR.name == "schemas"


# ---------- 异常继承 ----------

def test_schema_error_is_exception_batch54():
    assert issubclass(EvalSchemaError, Exception)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_no_wrap_of_load_batch54():
    src = _src()
    assert "schema = load_schema(schema_name)" in src
    assert "if not errors:" in src
    assert "return" in src


# ---------- forbidden tokens 第二百六十二批 ----------

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
