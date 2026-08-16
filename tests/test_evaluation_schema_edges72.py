"""evaluation/schema.py 第一百零四轮 edges 测试（Round 722）。

补强 edges70/edges71 未触及的角度（第八十七批）。

新角度：
- 最小合法报告（全 schema 通过）validate 返回 None
- 三错误按 absolute_path 字典序排序（devset < per_doc < summary），head 取最浅
- 单错误完整 message 格式（含 (1 处) 与 @ path=[]）
- flat 条目 schema_path 记录（["properties", ...] 前缀）
- EvalSchemaError 默认 errors=[] / 保留传入 / str(e)==message / args
- load_schema 每次返回新 dict（无缓存）
- 路径遍历无守卫（../target.json 可加载，现状记录）
- BOM / 非法 JSON → JSONDecodeError 直接冒泡（非 EvalSchemaError）
- validate_file 接受 str 路径 / 目录 FileNotFoundError / 非法 JSON
- 三个 schema 均为 draft 2020-12；SCHEMAS_DIR 位置
- AST（_schema_path If1·Raise1 / load_schema With1·Return1 / validate If1·For1·Lambda1 /
  validate_file If1·Raise1·Return0 / 类 Call2 / 模块 Raise3）
- 源码补强（Draft202012Validator 导入行 / sorted lambda 行 / flat 三键行）
- forbidden tokens 第一百九十二批
"""

from __future__ import annotations

import ast
import inspect
import json
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


def _valid_report() -> dict:
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": False, "evaluator_version": "1.1",
            "report_version": "1.1", "parser_name": "fallback",
            "parser_version": None, "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-08-17T00:00:00",
        },
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0, "docx_count": 0,
                   "categories_covered": []},
        "summary": {},
        "per_doc": [],
    }


# ---------- 合法实例 ----------

def test_minimal_valid_report_passes_batch53():
    assert validate(_valid_report(), "evaluation-report.schema.json") is None


# ---------- 多错误排序 ----------

def test_three_errors_sorted_by_path_batch53():
    bad = _valid_report()
    bad["summary"] = None  # 类型错误 @ ["summary"]
    del bad["devset"]["status"]  # 缺必填 @ ["devset"]
    bad["per_doc"] = [{
        "doc_id": "d", "source_type": "txt",  # 枚举外 @ ["per_doc", 0, ...]
        "metrics": {},
        "wall_time_seconds": {"total": None, "parse": None, "chunk": None},
    }]
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "evaluation-report.schema.json")
    paths = [fe["path"] for fe in ei.value.errors]
    assert paths == [["devset"], ["per_doc", 0, "source_type"], ["summary"]]
    assert paths == sorted(paths, key=lambda p: json.dumps(p))


def test_single_error_message_format_batch53():
    bad = _valid_report()
    del bad["summary"]
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "evaluation-report.schema.json")
    assert len(ei.value.errors) == 1
    assert str(ei.value) == ("Schema 'evaluation-report.schema.json' "
                             "校验失败 (1 处)："
                             "'summary' is a required property @ path=[]")


def test_flat_entries_record_schema_path_batch53():
    bad = _valid_report()
    bad["summary"] = None
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "evaluation-report.schema.json")
    fe = ei.value.errors[0]
    assert set(fe.keys()) == {"path", "message", "schema_path"}
    assert fe["path"] == ["summary"]
    assert fe["schema_path"][:2] == ["properties", "summary"]
    assert "None is not of type 'object'" in fe["message"]


# ---------- EvalSchemaError ----------

def test_eval_schema_error_defaults_batch53():
    e = EvalSchemaError("m")
    assert e.errors == []
    assert str(e) == "m"
    assert e.args == ("m",)


def test_eval_schema_error_preserves_errors_batch53():
    errs = [{"path": [], "message": "x", "schema_path": []}]
    e = EvalSchemaError("m", errors=errs)
    assert e.errors is errs
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_empty_list_stays_empty_batch53():
    assert EvalSchemaError("m", errors=[]).errors == []


# ---------- load_schema ----------

def test_load_schema_returns_fresh_dict_batch53():
    a = load_schema("annotation.schema.json")
    b = load_schema("annotation.schema.json")
    assert a == b
    a["mutated"] = True
    assert "mutated" not in load_schema("annotation.schema.json")


def test_load_schema_traversal_no_guard_batch53(tmp_path, monkeypatch):
    sub = tmp_path / "schemas"
    sub.mkdir()
    (tmp_path / "target.json").write_text('{"ok": 1}', encoding="utf-8")
    monkeypatch.setattr(schema_mod, "SCHEMAS_DIR", sub)
    assert load_schema("../target.json") == {"ok": 1}  # 现状：无路径逃逸守卫


def test_load_schema_bom_raises_jsondecode_batch53(tmp_path, monkeypatch):
    sub = tmp_path / "schemas"
    sub.mkdir()
    p = sub / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf{}")
    monkeypatch.setattr(schema_mod, "SCHEMAS_DIR", sub)
    with pytest.raises(json.JSONDecodeError):
        load_schema("bom.json")


def test_load_schema_invalid_json_batch53(tmp_path, monkeypatch):
    sub = tmp_path / "schemas"
    sub.mkdir()
    (sub / "bad.json").write_text("not json", encoding="utf-8")
    monkeypatch.setattr(schema_mod, "SCHEMAS_DIR", sub)
    with pytest.raises(json.JSONDecodeError):
        load_schema("bad.json")


def test_schema_path_missing_file_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(schema_mod, "SCHEMAS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("ghost.schema.json")
    assert "Schema 文件不存在" in str(ei.value)
    assert "ghost.schema.json" in str(ei.value)


# ---------- validate_file ----------

def test_validate_file_accepts_str_path_batch53(tmp_path):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(_valid_report()), encoding="utf-8")
    assert validate_file(str(f), "evaluation-report.schema.json") is None


def test_validate_file_directory_batch53(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path, "manifest.schema.json")
    assert "待校验文件不存在" in str(ei.value)


def test_validate_file_invalid_json_batch53(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("nope", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_schema_error_propagates_batch53(tmp_path):
    f = tmp_path / "r.json"
    bad = _valid_report()
    bad["report_version"] = "9.9"
    f.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        validate_file(f, "evaluation-report.schema.json")
    assert "report_version" in str(ei.value)


# ---------- Schema 目录 ----------

def test_all_schemas_are_draft2020_batch53():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"):
        assert "2020-12" in load_schema(name)["$schema"], name


def test_schemas_dir_location_batch53():
    assert SCHEMAS_DIR.name == "schemas"
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_import_and_sort_lines_batch53():
    src = _src()
    assert "from jsonschema import Draft202012Validator" in src
    assert ("errors = sorted(validator.iter_errors(instance), "
            "key=lambda e: list(e.absolute_path))" in src)


def test_source_flat_keys_batch53():
    src = _src()
    assert '"path": list(err.absolute_path),' in src
    assert '"message": err.message,' in src
    assert '"schema_path": list(err.absolute_schema_path),' in src
    assert "self.errors = errors or []" in src
    assert "f\"Schema '{schema_name}' 校验失败 ({len(errors)} 处)：\"" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(schema_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_schema_path_structure_batch53():
    c = _counts(_func("_schema_path"))
    assert (c["If"], c["Return"], c["Raise"], c["JoinedStr"]) == (1, 1, 1, 1)


def test_ast_load_schema_structure_batch53():
    c = _counts(_func("load_schema"))
    assert (c["If"], c["Return"], c["Raise"], c["With"], c["Subscript"]) == \
        (0, 1, 0, 1, 1)


def test_ast_validate_structure_batch53():
    c = _counts(_func("validate"))
    assert (c["If"], c["For"], c["Return"], c["Raise"], c["Lambda"],
            c["AnnAssign"], c["Subscript"], c["JoinedStr"]) == \
        (1, 1, 1, 1, 1, 1, 4, 1)


def test_ast_validate_file_structure_batch53():
    c = _counts(_func("validate_file"))
    assert (c["If"], c["Raise"], c["With"], c["Return"]) == (1, 1, 1, 0)


def test_ast_class_and_module_raises_batch53():
    import collections
    cls = next(n for n in _tree().body if isinstance(n, ast.ClassDef))
    c = collections.Counter(type(n).__name__ for n in ast.walk(cls))
    assert (c["FunctionDef"], c["Call"]) == (1, 2)
    mod = collections.Counter(type(n).__name__ for n in ast.walk(_tree()))
    assert mod["Raise"] == 3


# ---------- forbidden tokens 第一百九十二批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch53():
    assert _src().count("open(") == 2
