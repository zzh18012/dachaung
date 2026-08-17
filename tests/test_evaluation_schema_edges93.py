"""evaluation/schema.py 第三百一十三轮 edges 测试（Round 869）。

补强 edges92 未触及的角度（第二百四十四批，probe 实证）。

新角度：
- document $defs/element required 恰 6 项（content 不在
  required —— 有意锁定的业务文档模型事实）
- chunk / relation / warning / error / pdf_locator 的
  required 集合
- manifest documents 条目缺 path → 错误落在父路径
  ["documents", 0]
- EvalSchemaError.errors 保留传入列表的同一对象（or []
  只对 falsy 生效）
- SCHEMAS_DIR 目录内容恰 4 个 schema 文件
- validate 未知 Schema 名 → FileNotFoundError
- validate_file 传目录 → FileNotFoundError
- forbidden tokens 第三百三十九批
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
    validate_file,
)


def _doc_defs():
    return load_schema("document.schema.json")["$defs"]


# ---------- document $defs ----------

def test_element_def_required_six_batch67():
    assert _doc_defs()["element"]["required"] == [
        "element_id", "type", "parent_id", "source_locator",
        "confidence", "metadata"]


def test_chunk_def_required_four_batch67():
    assert _doc_defs()["chunk"]["required"] == [
        "chunk_id", "text", "source_element_ids", "metadata"]


def test_relation_warning_error_defs_batch67():
    d = _doc_defs()
    assert d["relation"]["required"] == ["type", "from_id",
                                         "to_id"]
    assert d["warning"]["required"] == ["code", "reason"]
    assert d["error"]["required"] == ["code", "message"]


def test_pdf_locator_required_page_only_batch67():
    assert _doc_defs()["pdf_locator"]["required"] == ["page"]


# ---------- 深层错误路径 ----------

def test_documents_item_missing_path_parent_path_batch67():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0",
                  "devset_status": "incomplete",
                  "documents": [{"doc_id": "d1",
                                 "source_type": "pdf"}]},
                 "manifest.schema.json")
    e = ei.value.errors[0]
    assert e["path"] == ["documents", 0]
    assert "'path' is a required property" in e["message"]


# ---------- errors 身份保持 ----------

def test_errors_list_identity_preserved_batch67():
    errs = [{"path": ["a"], "message": "m",
             "schema_path": []}]
    e = EvalSchemaError("msg", errs)
    assert e.errors is errs
    assert str(e) == "msg"


# ---------- 目录内容 ----------

def test_schemas_dir_exactly_four_files_batch67():
    names = sorted(p.name for p in SCHEMAS_DIR.iterdir()
                   if p.suffix == ".json")
    assert names == ["annotation.schema.json",
                     "document.schema.json",
                     "evaluation-report.schema.json",
                     "manifest.schema.json"]


# ---------- 未知 Schema / 目录输入 ----------

def test_validate_unknown_schema_fnf_batch67():
    with pytest.raises(FileNotFoundError):
        validate({}, "no-such.schema.json")


def test_validate_file_directory_fnf_batch67(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path, "manifest.schema.json")
    assert "待校验文件不存在" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch67():
    src = _src()
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src
    assert "head = errors[0]" in src


# ---------- forbidden tokens 第三百三十九批 ----------

def test_source_no_eval_batch67():
    assert "eval(" not in _src()


def test_source_no_exec_batch67():
    assert "exec(" not in _src()


def test_source_no_compile_batch67():
    assert "compile(" not in _src()


def test_source_no_globals_batch67():
    assert "globals(" not in _src()


def test_source_no_locals_batch67():
    assert "locals(" not in _src()


def test_source_no_os_system_batch67():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch67():
    assert "subprocess" not in _src()


def test_source_no_popen_batch67():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch67():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch67():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch67():
    assert "socket" not in _src()


def test_source_no_requests_batch67():
    assert "requests" not in _src()


def test_source_no_urllib_batch67():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch67():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch67():
    assert "yield" not in _src()


def test_source_no_async_await_batch67():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch67():
    assert _src().count("open(") == 2
