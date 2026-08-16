"""evaluation/schema.py 第一百零六轮 edges 测试（Round 736）。

补强 edges72/edges73 未触及的角度（第一百零一批）。

新角度：
- manifest schema 结构锁：devset_status 枚举 / sha256 pattern（大写、短、
  合法 64 位小写）/ document 元素 additionalProperties false /
  document source_type 仅 pdf·docx 而 expected_failure 允许 txt·other /
  expectations.element_count_by_type 值必须 integer≥0（字符串、负数拒）/
  expectations additionalProperties false / required_markers minLength /
  paired_with 空串合法
- report schema 结构锁：report_version const "1.1" / provenance
  additionalProperties false / max_chars minimum 1（0 拒）/
  dependencies 值 string|null（int 拒）/ devset 计数 minimum 0（-1 拒）/
  summary additionalProperties true（额外键放行 —— 与根 false 对照）/
  wall_time_seconds additionalProperties false + total minimum 0 /
  per_doc additionalProperties false + doc_id minLength /
  ef matches 必须 boolean（int 1 拒 —— bool ⊂ int 在 jsonschema 不成立）/
  per_doc 缺 wall_time_seconds → 错误路径精确 ["per_doc", 0]
- evaluation/__init__ 版本常量锁（1.0 / 1.1 / 1.1 / 1.0）+ __all__ 四元素
- forbidden tokens 第二百零六批
"""

from __future__ import annotations

import copy
import inspect

import pytest

import evaluation
from evaluation.schema import EvalSchemaError, validate

MAN = "manifest.schema.json"
REP = "evaluation-report.schema.json"


def _check(data, name):
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, name)
    return ei.value


def _man(**over):
    d = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": []}
    d.update(over)
    return d


def _doc(**over):
    d = {"doc_id": "d", "path": "a.pdf", "source_type": "pdf"}
    d.update(over)
    return d


_BASE_REP = {
    "report_version": "1.1",
    "provenance": {
        "git_commit": None, "git_dirty": False, "evaluator_version": "1.1",
        "report_version": "1.1", "parser_name": "fallback",
        "parser_version": None, "dependencies": {}, "max_chars": 800,
        "run_timestamp_iso": "t",
    },
    "devset": {"status": "incomplete", "file_count": 0,
               "content_group_count": 0, "pdf_count": 0, "docx_count": 0,
               "categories_covered": []},
    "summary": {},
    "per_doc": [],
}


def _rep(**over):
    d = copy.deepcopy(_BASE_REP)
    d.update(over)
    return d


_PD = {"doc_id": "d", "source_type": "pdf", "metrics": {},
       "wall_time_seconds": {"total": 1.0, "parse": None, "chunk": None}}


# ---------- manifest schema 结构锁 ----------

def test_manifest_minimal_valid_batch54():
    assert validate(_man(), MAN) is None


def test_manifest_devset_status_enum_batch54():
    e = _check(_man(devset_status="bogus"), MAN)
    assert e.errors[0]["path"] == ["devset_status"]
    assert "is not one of" in e.errors[0]["message"]


@pytest.mark.parametrize("sha", ["AB" * 32, "ab" * 31])
def test_manifest_sha256_pattern_rejects_batch54(sha):
    e = _check(_man(documents=[_doc(sha256=sha)]), MAN)
    assert e.errors[0]["path"] == ["documents", 0, "sha256"]


def test_manifest_sha256_lowercase_64_ok_batch54():
    assert validate(_man(documents=[_doc(sha256="ab" * 32)]), MAN) is None


def test_manifest_document_extra_key_rejected_batch54():
    e = _check(_man(documents=[_doc(bogus=1)]), MAN)
    assert e.errors[0]["path"] == ["documents", 0]


def test_manifest_document_source_type_pdf_docx_only_batch54():
    _check(_man(documents=[_doc(source_type="txt")]), MAN)
    assert validate(_man(documents=[_doc(source_type="docx")]), MAN) is None


def test_manifest_ef_source_type_allows_txt_other_batch54():
    # expected_failure 的 source_type 枚举宽于 document 的
    for st in ("txt", "other", "pdf", "docx"):
        assert validate(_man(expected_failures=[
            {"doc_id": "e", "path": "x.txt",
             "expected_error_code": "c", "source_type": st}]), MAN) is None


def test_manifest_expectations_count_must_be_integer_batch54():
    e = _check(_man(documents=[_doc(expectations={
        "element_count_by_type": {"p": "3"}})]), MAN)
    assert e.errors[0]["path"] == \
        ["documents", 0, "expectations", "element_count_by_type", "p"]
    assert "is not of type 'integer'" in e.errors[0]["message"]


def test_manifest_expectations_count_minimum_zero_batch54():
    e = _check(_man(documents=[_doc(expectations={
        "element_count_by_type": {"p": -1}})]), MAN)
    assert "less than the minimum of 0" in e.errors[0]["message"]


def test_manifest_expectations_extra_key_rejected_batch54():
    e = _check(_man(documents=[_doc(expectations={"bogus": 1})]), MAN)
    assert e.errors[0]["path"] == ["documents", 0, "expectations"]


def test_manifest_required_markers_min_length_batch54():
    e = _check(_man(documents=[_doc(expectations={
        "required_markers": [""]})]), MAN)
    assert e.errors[0]["path"] == \
        ["documents", 0, "expectations", "required_markers", 0]


def test_manifest_paired_with_empty_ok_batch54():
    assert validate(_man(documents=[_doc(paired_with="")]), MAN) is None


# ---------- report schema 结构锁 ----------

def test_report_base_valid_batch54():
    assert validate(_rep(), REP) is None


def test_report_version_const_batch54():
    e = _check(_rep(report_version="1.2"), REP)
    assert "'1.1' was expected" in e.errors[0]["message"]


def test_report_provenance_extra_key_rejected_batch54():
    e = _check(_rep(provenance={**_BASE_REP["provenance"], "bogus": 1}), REP)
    assert e.errors[0]["path"] == ["provenance"]


def test_report_max_chars_minimum_one_batch54():
    e = _check(_rep(provenance={**_BASE_REP["provenance"], "max_chars": 0}),
               REP)
    assert e.errors[0]["path"] == ["provenance", "max_chars"]
    assert "minimum of 1" in e.errors[0]["message"]


def test_report_dependencies_value_union_type_batch54():
    e = _check(_rep(provenance={**_BASE_REP["provenance"],
                               "dependencies": {"x": 1}}), REP)
    assert "is not of type 'string', 'null'" in e.errors[0]["message"]


def test_report_devset_count_negative_rejected_batch54():
    e = _check(_rep(devset={**_BASE_REP["devset"], "pdf_count": -1}), REP)
    assert e.errors[0]["path"] == ["devset", "pdf_count"]


def test_report_summary_additional_properties_true_batch54():
    # 与根 additionalProperties false 对照：summary 额外键放行
    assert validate(_rep(summary={"anything": 1}), REP) is None


def test_report_per_doc_minimal_valid_batch54():
    assert validate(_rep(per_doc=[copy.deepcopy(_PD)]), REP) is None


def test_report_wall_time_extra_key_rejected_batch54():
    pd = copy.deepcopy(_PD)
    pd["wall_time_seconds"]["bogus"] = 1
    e = _check(_rep(per_doc=[pd]), REP)
    assert e.errors[0]["path"] == ["per_doc", 0, "wall_time_seconds"]


def test_report_wall_time_negative_rejected_batch54():
    pd = copy.deepcopy(_PD)
    pd["wall_time_seconds"]["total"] = -1
    e = _check(_rep(per_doc=[pd]), REP)
    assert e.errors[0]["path"] == \
        ["per_doc", 0, "wall_time_seconds", "total"]


def test_report_per_doc_extra_key_rejected_batch54():
    e = _check(_rep(per_doc=[{**copy.deepcopy(_PD), "bogus": 1}]), REP)
    assert e.errors[0]["path"] == ["per_doc", 0]


def test_report_per_doc_doc_id_min_length_batch54():
    e = _check(_rep(per_doc=[{**copy.deepcopy(_PD), "doc_id": ""}]), REP)
    assert e.errors[0]["path"] == ["per_doc", 0, "doc_id"]
    assert "should be non-empty" in e.errors[0]["message"]


def test_report_ef_matches_must_be_boolean_batch54():
    # jsonschema 的 boolean 类型不接受 int（bool ⊂ int 在这里不成立）
    ef = {"doc_id": "e", "expected_error_code": "c",
          "actual_error_code": None, "matches": 1}
    e = _check(_rep(expected_failures=[ef]), REP)
    assert e.errors[0]["path"] == ["expected_failures", 0, "matches"]
    assert "is not of type 'boolean'" in e.errors[0]["message"]


def test_report_root_extra_key_path_empty_batch54():
    e = _check(_rep(bogus=1), REP)
    assert e.errors[0]["path"] == []


def test_report_per_doc_missing_wall_time_path_batch54():
    e = _check(_rep(per_doc=[{"doc_id": "d", "source_type": "pdf",
                              "metrics": {}}]), REP)
    assert e.errors[0]["path"] == ["per_doc", 0]
    assert "wall_time_seconds' is a required property" \
        in e.errors[0]["message"]


# ---------- evaluation/__init__ 版本常量 ----------

def test_init_version_constants_batch54():
    assert evaluation.MANIFEST_VERSION == "1.0"
    assert evaluation.EVALUATOR_VERSION == "1.1"
    assert evaluation.REPORT_VERSION == "1.1"
    assert evaluation.ANNOTATION_VERSION == "1.0"


def test_init_all_four_names_batch54():
    assert evaluation.__all__ == [
        "EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION",
        "MANIFEST_VERSION"]


# ---------- 源码补强 ----------

def _src() -> str:
    import evaluation.schema as schema_mod
    return inspect.getsource(schema_mod)


def test_source_flat_keys_and_raw_paths_batch54():
    # 现状记录：flat 保留原始 absolute_path（int 数组索引不转 str，
    # 依赖 json.dumps 对 int 的原生支持）
    src = _src()
    assert '"path": list(err.absolute_path)' in src
    assert '"schema_path": list(err.absolute_schema_path)' in src
    assert "key=lambda e: list(e.absolute_path)" in src


# ---------- forbidden tokens 第二百零六批 ----------

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
