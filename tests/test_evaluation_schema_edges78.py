"""evaluation/schema.py 第一百零九轮 edges 测试（Round 764）。

补强 edges74-77 未触及的角度（第一百二十八批）。

新角度：
- report schema defs 精确结构：per_doc required 4 键、wall_time
  required [total, parse, chunk] + 值 type [number,null] minimum 0、
  provenance required 9 键 addProps false、expected_failure_result
  required 4 键、summary 无 required（四聚合键全可选）
- 顶层非对象实例（[] / None / 42）→ "is not of type 'object'" 拒
- load_schema 名字未消毒："../app/schema.py" 通过 is_file 检查
  （目录穿越可达），死在 json 解析 JSONDecodeError 而非
  FileNotFoundError —— 越界名的行为是解析错不是存在错（现状记录）
- EvalSchemaError errors 参数传真值字符串 "x" → 原样存为 "x"
  （errors or [] 只防 falsy，不防非 list）
- evaluation/__init__ 公开名恰 5 个（四版本常量 + schema 子模块引用）
- forbidden tokens 第二百三十四批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation
import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
)


def _rep():
    return load_schema("evaluation-report.schema.json")


# ---------- report defs 精确结构 ----------

def test_per_doc_def_required_four_batch54():
    pd = _rep()["$defs"]["per_doc"]
    assert pd["required"] == ["doc_id", "source_type", "metrics",
                              "wall_time_seconds"]
    assert sorted(pd["properties"]) == ["doc_id", "metrics", "source_type",
                                        "wall_time_seconds"]


def test_wall_time_def_shape_batch54():
    wt = _rep()["$defs"]["per_doc"]["properties"]["wall_time_seconds"]
    assert wt["required"] == ["total", "parse", "chunk"]
    assert wt["additionalProperties"] is False
    total = wt["properties"]["total"]
    assert total["type"] == ["number", "null"]
    assert total["minimum"] == 0


def test_provenance_def_nine_required_batch54():
    prov = _rep()["$defs"]["provenance"]
    assert prov["required"] == [
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso"]
    assert prov["additionalProperties"] is False


def test_ef_result_def_required_four_batch54():
    efr = _rep()["$defs"]["expected_failure_result"]
    assert efr["required"] == ["doc_id", "expected_error_code",
                               "actual_error_code", "matches"]


def test_summary_def_no_required_batch54():
    s = _rep()["$defs"]["summary"]
    assert "required" not in s
    assert sorted(s["properties"]) == ["counts", "ratio_macro_averages",
                                       "silent_drop_total",
                                       "success_rates"]


def test_devset_def_required_six_batch54():
    d = _rep()["$defs"]["devset"]
    assert d["required"] == ["status", "file_count", "content_group_count",
                             "pdf_count", "docx_count",
                             "categories_covered"]


# ---------- 顶层非对象 ----------

@pytest.mark.parametrize("inst", [[], None, 42])
def test_non_object_instance_rejected_batch54(inst):
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    assert "is not of type 'object'" in str(ei.value)


# ---------- 名字未消毒 ----------

def test_load_schema_traversal_json_decode_error_batch54():
    # 目录穿越通过 is_file；死在 json 解析而非存在性检查
    with pytest.raises(Exception) as ei:
        load_schema("../app/schema.py")
    assert type(ei.value).__name__ == "JSONDecodeError"


# ---------- errors 参数非 list ----------

def test_error_class_truthy_string_errors_batch54():
    assert EvalSchemaError("m", "x").errors == "x"


# ---------- evaluation/__init__ 公开名 ----------

def test_evaluation_init_public_names_batch54():
    assert [n for n in dir(evaluation) if not n.startswith("_")] == [
        "ANNOTATION_VERSION", "EVALUATOR_VERSION", "MANIFEST_VERSION",
        "REPORT_VERSION", "schema"]


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_no_name_sanitization_batch54():
    src = _src()
    assert "SCHEMAS_DIR / name" in src
    assert 'p.is_file()' in src


# ---------- forbidden tokens 第二百三十四批 ----------

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
