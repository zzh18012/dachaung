"""evaluation/schema.py 第一百轮 edges 测试（Round 701）。

补强 edges68 未触及的角度（第六十六批）：annotation / evaluation-report 的
**内容级校验矩阵**（edges67 覆盖了 manifest 内容，694 覆盖了三 schema 结构）。

新角度：
- annotation 最小合法 / annotation_version const 1.0 / doc_id 空串 / 顶层多余键 / annotator 空串合法（无 minLength）/ date 空串拒
- figure_caption_pairs 项（合法 / 缺 caption_text / 多余键 / 空 marker）
- heading_order 项（合法 / level 0 拒 / level 1.5 拒 / 多余键 / 空 text 拒）
- boundary_anchor（before 合法 / position "left" 拒 / 空 marker 拒 / 多余键 / reason 可选 / 缺 position 拒）
- annotation 全字段合法
- evaluation-report 最小合法 / report_version const 1.1（"1.0" 拒）
- provenance（多余键拒 / git_dirty 必须布尔 / max_chars 0 与 1.5 拒 / dependencies 数值拒 null 可 / 时间戳空串拒 / git_commit 字符串可）
- devset（status 坏值拒 / file_count 负数拒 / pdf_count 浮点拒 / categories 数字项拒）
- per_doc（空 doc_id 拒 / source_type txt 拒 / wall_time 缺 chunk 拒 / 多余键拒 / total 负数拒 / 全 5 键合法）
- expected_failures（matches 非布尔拒 / actual_error_code null 可 / 多余键拒）
- summary additionalProperties true（多余键可）
- forbidden tokens 第一百七十一批（schema.py 源）
"""

from __future__ import annotations

import copy
import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate

ANN = "annotation.schema.json"
REP = "evaluation-report.schema.json"


def _ann(**over) -> dict:
    base = {"annotation_version": "1.0", "doc_id": "d1"}
    base.update(over)
    return base


def _valid_report() -> dict:
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {"pdfplumber": "1.0"},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-17T10:00:00+08:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {},
        "per_doc": [],
    }


def _rep(**mutate) -> dict:
    """深拷贝合法报告后按 (dotted_path, value) 突变。"""
    obj = _valid_report()
    for dotted, value in mutate.items():
        cur = obj
        keys = dotted.split("__")
        for k in keys[:-1]:
            cur = cur[k]
        cur[keys[-1]] = value
    return obj


# ---------- annotation 基础 ----------

def test_annotation_minimal_valid_batch52():
    validate(_ann(), ANN)


def test_annotation_version_const_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(annotation_version="2.0"), ANN)


def test_annotation_doc_id_empty_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(doc_id=""), ANN)


def test_annotation_top_extra_key_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(surprise=1), ANN)


def test_annotation_annotator_empty_string_ok_batch52():
    """annotator 无 minLength —— 空串合法。"""
    validate(_ann(annotator=""), ANN)


def test_annotation_date_empty_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(date=""), ANN)


# ---------- figure_caption_pairs ----------

def test_pair_valid_batch52():
    validate(_ann(figure_caption_pairs=[
        {"figure_marker": "图1", "caption_text": "说明文字"},
    ]), ANN)


def test_pair_missing_caption_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(figure_caption_pairs=[{"figure_marker": "图1"}]), ANN)


def test_pair_extra_key_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(figure_caption_pairs=[
            {"figure_marker": "f", "caption_text": "c", "extra": 1},
        ]), ANN)


def test_pair_empty_marker_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(figure_caption_pairs=[
            {"figure_marker": "", "caption_text": "c"},
        ]), ANN)


# ---------- heading_order ----------

def test_heading_valid_batch52():
    validate(_ann(heading_order=[{"level": 1, "text": "标题"}]), ANN)


def test_heading_level_zero_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": 0, "text": "t"}]), ANN)


def test_heading_level_float_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": 1.5, "text": "t"}]), ANN)


def test_heading_extra_key_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": 1, "text": "t", "x": 1}]), ANN)


def test_heading_empty_text_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": 1, "text": ""}]), ANN)


# ---------- boundary_anchor ----------

def test_anchor_before_valid_batch52():
    validate(_ann(chunk_boundary_anchors=[
        {"marker": "第一章", "position": "before"},
    ]), ANN)


def test_anchor_position_left_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[
            {"marker": "m", "position": "left"},
        ]), ANN)


def test_anchor_empty_marker_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[
            {"marker": "", "position": "after"},
        ]), ANN)


def test_anchor_extra_key_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[
            {"marker": "m", "position": "after", "note": "x"},
        ]), ANN)


def test_anchor_reason_optional_ok_batch52():
    validate(_ann(chunk_boundary_anchors=[
        {"marker": "m", "position": "after", "reason": "章节边界"},
    ]), ANN)


def test_anchor_missing_position_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[{"marker": "m"}]), ANN)


# ---------- annotation 全字段 ----------

def test_annotation_all_fields_valid_batch52():
    full = _ann(
        annotator="reviewer_a",
        date="2026-08-17",
        figure_caption_pairs=[{"figure_marker": "f", "caption_text": "c"}],
        heading_order=[{"level": 2, "text": "t"}],
        chunk_boundary_anchors=[{"marker": "m", "position": "after", "reason": "r"}],
    )
    validate(full, ANN)


# ---------- evaluation-report 基础 ----------

def test_report_minimal_valid_batch52():
    validate(_rep(), REP)


def test_report_version_const_1_1_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(report_version="1.0"), REP)


def test_report_top_extra_key_batch52():
    obj = _rep()
    obj["extra"] = 1
    with pytest.raises(EvalSchemaError):
        validate(obj, REP)


# ---------- provenance ----------

def test_provenance_extra_key_batch52():
    obj = _rep()
    obj["provenance"]["extra"] = 1
    with pytest.raises(EvalSchemaError):
        validate(obj, REP)


def test_git_dirty_must_be_bool_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(provenance__git_dirty="true"), REP)


def test_max_chars_zero_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(provenance__max_chars=0), REP)


def test_max_chars_float_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(provenance__max_chars=1.5), REP)


def test_dependencies_number_value_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(provenance__dependencies={"pdfplumber": 1.0}), REP)


def test_dependencies_null_value_ok_batch52():
    validate(_rep(provenance__dependencies={"pypdfium2": None}), REP)


def test_run_timestamp_empty_rejected_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(provenance__run_timestamp_iso=""), REP)


def test_git_commit_string_ok_batch52():
    validate(_rep(provenance__git_commit="c" * 40), REP)


# ---------- devset ----------

def test_devset_bad_status_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(devset__status="maybe"), REP)


def test_devset_negative_file_count_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(devset__file_count=-1), REP)


def test_devset_float_pdf_count_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(devset__pdf_count=0.5), REP)


def test_devset_categories_number_item_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(devset__categories_covered=[1]), REP)


# ---------- per_doc ----------

def _full_pd() -> dict:
    return {
        "doc_id": "d1",
        "source_type": "pdf",
        "metrics": {},
        "wall_time_seconds": {
            "total": 1.5, "parse": None, "chunk": None,
            "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented",
        },
    }


def test_per_doc_full_valid_batch52():
    validate(_rep(per_doc=[_full_pd()]), REP)


def test_per_doc_empty_doc_id_batch52():
    pd = _full_pd()
    pd["doc_id"] = ""
    with pytest.raises(EvalSchemaError):
        validate(_rep(per_doc=[pd]), REP)


def test_per_doc_source_type_txt_batch52():
    pd = _full_pd()
    pd["source_type"] = "txt"
    with pytest.raises(EvalSchemaError):
        validate(_rep(per_doc=[pd]), REP)


def test_per_doc_wall_time_missing_chunk_batch52():
    pd = _full_pd()
    del pd["wall_time_seconds"]["chunk"]
    with pytest.raises(EvalSchemaError):
        validate(_rep(per_doc=[pd]), REP)


def test_per_doc_wall_time_extra_key_batch52():
    pd = _full_pd()
    pd["wall_time_seconds"]["extra"] = 1
    with pytest.raises(EvalSchemaError):
        validate(_rep(per_doc=[pd]), REP)


def test_per_doc_total_negative_batch52():
    pd = _full_pd()
    pd["wall_time_seconds"]["total"] = -0.5
    with pytest.raises(EvalSchemaError):
        validate(_rep(per_doc=[pd]), REP)


def test_per_doc_metrics_any_object_batch52():
    pd = _full_pd()
    pd["metrics"] = {"anything": {"value": None, "reason": "r"}}
    validate(_rep(per_doc=[pd]), REP)


# ---------- expected_failures ----------

def test_ef_valid_batch52():
    validate(_rep(expected_failures=[
        {"doc_id": "ef1", "expected_error_code": "x",
         "actual_error_code": None, "matches": False},
    ]), REP)


def test_ef_matches_not_bool_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(expected_failures=[
            {"doc_id": "e", "expected_error_code": "x",
             "actual_error_code": "x", "matches": "yes"},
        ]), REP)


def test_ef_extra_key_batch52():
    with pytest.raises(EvalSchemaError):
        validate(_rep(expected_failures=[
            {"doc_id": "e", "expected_error_code": "x",
             "actual_error_code": None, "matches": True, "extra": 1},
        ]), REP)


# ---------- summary 宽松 ----------

def test_summary_extra_key_ok_batch52():
    obj = _rep()
    obj["summary"]["custom_aggregate"] = {"x": 1}
    validate(obj, REP)


# ---------- forbidden tokens 第一百七十一批 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch52():
    assert _src().count("open(") == 2
