"""evaluation/schema.py 第二百七十一轮 edges 测试（Round 827）。

补强 edges86 未触及的角度（第二百零一批）。

新角度：
- SCHEMAS_DIR 文件清单恰为 4 个（annotation / document /
  evaluation-report / manifest）
- 三个评测 Schema 的 $id 均为
  https://kvfs.local/schemas/<name>
- report_version 传 float 1.1：**同 path 双错**（type + const
  各报一次，共 2 处 —— jsonschema 对非字符串先打 type 再打
  const）
- validate_file 收 str 路径（Path(path) 包装）
- forbidden tokens 第二百九十七批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (SCHEMAS_DIR, EvalSchemaError,
                               load_schema, validate,
                               validate_file)

REP = {
    "report_version": "1.1",
    "provenance": {"git_commit": None, "git_dirty": False,
                   "evaluator_version": "1.1",
                   "report_version": "1.1",
                   "parser_name": "fallback",
                   "parser_version": "1.0", "dependencies": {},
                   "max_chars": 800,
                   "run_timestamp_iso": "t"},
    "devset": {"status": "incomplete", "file_count": 0,
               "content_group_count": 0, "pdf_count": 0,
               "docx_count": 0, "categories_covered": []},
    "summary": {}, "per_doc": []}


# ---------- 目录清单 ----------

def test_schemas_dir_inventory_batch55():
    assert sorted(p.name for p in SCHEMAS_DIR.iterdir()) == [
        "annotation.schema.json", "document.schema.json",
        "evaluation-report.schema.json",
        "manifest.schema.json"]


# ---------- $id ----------

@pytest.mark.parametrize("name", [
    "manifest.schema.json", "annotation.schema.json",
    "evaluation-report.schema.json"])
def test_schema_id_urls_batch55(name):
    s = load_schema(name)
    assert s["$id"] == f"https://kvfs.local/schemas/{name}"


# ---------- float 版本双错 ----------

def test_report_version_float_double_error_batch55():
    r = json.loads(json.dumps(REP))
    r["report_version"] = 1.1
    with pytest.raises(EvalSchemaError) as ei:
        validate(r, "evaluation-report.schema.json")
    assert len(ei.value.errors) == 2
    kinds = [er["schema_path"][-1]
             for er in ei.value.errors]
    assert kinds == ["type", "const"]
    assert all(er["path"] == ["report_version"]
               for er in ei.value.errors)


# ---------- str 路径 ----------

def test_validate_file_str_path_batch55(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete",
                             "documents": []}),
                 encoding="utf-8")
    validate_file(str(f), "manifest.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent / \"schemas\"" in src
    assert "if not p.is_file():" in src


# ---------- forbidden tokens 第二百九十七批 ----------

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
