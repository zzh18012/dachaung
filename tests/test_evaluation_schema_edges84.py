"""evaluation/schema.py 第二百五十轮 edges 测试（Round 806）。

补强 edges83 未触及的角度（第一百七十批）。

新角度（全部针对 evaluation-report.schema.json 行为面）：
- 极简报告（无 expected_failures 键）合法；expected_failures
  空数组合法（键可选 + 空容器双放行）
- summary additionalProperties true：任意额外键放行
- per_doc metrics 自由形态：值可以是列表
- wall_time_seconds 封闭形状：额外键 rejected（schema_path 止于
  additionalProperties，不含 $defs）；total 负数 minimum 拒绝
- per_doc doc_id "" → minLength；source_type "txt" → enum
- provenance.dependencies 值类型：int 拒绝 / null 放行
- devset file_count -1 → minimum；categories_covered [1] → items
- expected_failure_result 额外键 → additionalProperties
- forbidden tokens 第二百七十六批
"""

from __future__ import annotations

import copy
import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate

REP = {
    "report_version": "1.1",
    "provenance": {
        "git_commit": None, "git_dirty": False,
        "evaluator_version": "1.1", "report_version": "1.1",
        "parser_name": "fallback", "parser_version": "1.0",
        "dependencies": {}, "max_chars": 800,
        "run_timestamp_iso": "t",
    },
    "devset": {
        "status": "incomplete", "file_count": 0,
        "content_group_count": 0, "pdf_count": 0, "docx_count": 0,
        "categories_covered": [],
    },
    "summary": {},
    "per_doc": [],
}


def _pd(**over):
    d = {"doc_id": "d1", "source_type": "pdf", "metrics": {},
         "wall_time_seconds": {"total": 1.0, "parse": None,
                               "chunk": None}}
    d.update(over)
    return d


def _err(rep):
    with pytest.raises(EvalSchemaError) as ei:
        validate(rep, "evaluation-report.schema.json")
    return ei.value


# ---------- 极简 / 双放行 ----------

def test_minimal_report_without_ef_valid_batch55():
    validate(copy.deepcopy(REP), "evaluation-report.schema.json")


def test_expected_failures_empty_valid_batch55():
    r = copy.deepcopy(REP)
    r["expected_failures"] = []
    validate(r, "evaluation-report.schema.json")


# ---------- summary 开放 ----------

def test_summary_extra_key_allowed_batch55():
    r = copy.deepcopy(REP)
    r["summary"] = {"counts": {}, "zzz": 1}
    validate(r, "evaluation-report.schema.json")


# ---------- metrics 自由形态 ----------

def test_metrics_list_value_allowed_batch55():
    r = copy.deepcopy(REP)
    r["per_doc"] = [_pd(metrics={"x": [1, 2, 3]})]
    validate(r, "evaluation-report.schema.json")


# ---------- wall_time_seconds 封闭 ----------

def test_wall_time_extra_key_rejected_batch55():
    r = copy.deepcopy(REP)
    r["per_doc"] = [_pd(wall_time_seconds={
        "total": 1.0, "parse": None, "chunk": None, "bogus": 1})]
    er = _err(r).errors[0]
    assert er["path"] == ["per_doc", 0, "wall_time_seconds"]
    assert er["schema_path"] == [
        "properties", "per_doc", "items", "properties",
        "wall_time_seconds", "additionalProperties"]
    assert "Additional properties are not allowed" in er["message"]


def test_wall_time_negative_total_rejected_batch55():
    r = copy.deepcopy(REP)
    r["per_doc"] = [_pd(wall_time_seconds={
        "total": -1.0, "parse": None, "chunk": None})]
    er = _err(r).errors[0]
    assert er["path"] == ["per_doc", 0, "wall_time_seconds", "total"]
    assert er["schema_path"][-1] == "minimum"
    assert "-1.0 is less than the minimum of 0" == er["message"]


# ---------- per_doc 字段约束 ----------

def test_doc_id_empty_rejected_batch55():
    r = copy.deepcopy(REP)
    r["per_doc"] = [_pd(doc_id="")]
    er = _err(r).errors[0]
    assert er["path"] == ["per_doc", 0, "doc_id"]
    assert er["schema_path"][-1] == "minLength"
    assert "'' should be non-empty" == er["message"]


def test_source_type_txt_rejected_batch55():
    r = copy.deepcopy(REP)
    r["per_doc"] = [_pd(source_type="txt")]
    er = _err(r).errors[0]
    assert er["path"] == ["per_doc", 0, "source_type"]
    assert "'txt' is not one of ['pdf', 'docx']" == er["message"]


# ---------- dependencies 值类型 ----------

def test_dependencies_int_rejected_batch55():
    r = copy.deepcopy(REP)
    r["provenance"]["dependencies"] = {"pkg": 5}
    er = _err(r).errors[0]
    assert er["path"] == ["provenance", "dependencies", "pkg"]
    assert "5 is not of type 'string', 'null'" == er["message"]


def test_dependencies_null_value_valid_batch55():
    r = copy.deepcopy(REP)
    r["provenance"]["dependencies"] = {"pkg": None}
    validate(r, "evaluation-report.schema.json")


# ---------- devset 约束 ----------

def test_devset_negative_file_count_rejected_batch55():
    r = copy.deepcopy(REP)
    r["devset"]["file_count"] = -1
    er = _err(r).errors[0]
    assert er["path"] == ["devset", "file_count"]
    assert er["schema_path"][-1] == "minimum"


def test_devset_categories_int_item_rejected_batch55():
    r = copy.deepcopy(REP)
    r["devset"]["categories_covered"] = [1]
    er = _err(r).errors[0]
    assert er["path"] == ["devset", "categories_covered", 0]
    assert "1 is not of type 'string'" == er["message"]


# ---------- ef 条目封闭 ----------

def test_ef_item_extra_key_rejected_batch55():
    r = copy.deepcopy(REP)
    r["expected_failures"] = [{"doc_id": "d",
                               "expected_error_code": "x",
                               "actual_error_code": None,
                               "matches": True, "extra": 1}]
    er = _err(r).errors[0]
    assert er["path"] == ["expected_failures", 0]
    assert er["schema_path"][-1] == "additionalProperties"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_sort_and_count_lines_batch55():
    src = _src()
    assert ("errors = sorted(validator.iter_errors(instance), "
            "key=lambda e: list(e.absolute_path))") in src
    assert "校验失败 ({len(errors)} 处)：" in src


def test_source_path_wrapping_batch55():
    assert "p = Path(path)" in _src()


# ---------- forbidden tokens 第二百七十六批 ----------

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
