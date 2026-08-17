"""evaluation/schema.py 第三百四十八轮 edges 测试（Round 904）。

补强 edges97 未触及的角度（第二百八十批，probe 实证）。

新角度：
- element type enum 八值；属性类型矩阵（parent_id/content 双类型
  [string,null]、confidence number、metadata object）
- chunk.source_element_ids 形状：array minItems 1 +
  items string minLength 1；chunk.text string
- annotation 三数组 items 形状：anchors $ref boundary_anchor；
  figure_caption_pairs 封闭 {figure_marker, caption_text}；
  heading_order 封闭 {level integer min 1, text}
- report_version const "1.1"；顶层 addProps False 拒绝
  evaluator_version（该键只在 provenance 内）
- 最小合法 report（6 键）validate 通过
- 多错误 message 只含首个 + "3 处"；.errors 全 3 条
- forbidden tokens 第三百七十四批
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, load_schema, validate


# ---------- element 类型与属性 ----------

def test_element_type_enum_eight_batch102():
    el = load_schema("document.schema.json")["$defs"][
        "element"]["properties"]
    assert el["type"]["enum"] == [
        "heading", "paragraph", "list_item", "table", "image",
        "caption", "header", "footer",
    ]


def test_element_prop_types_batch102():
    el = load_schema("document.schema.json")["$defs"][
        "element"]["properties"]
    assert el["element_id"]["type"] == "string"
    assert el["parent_id"]["type"] == ["string", "null"]
    assert el["content"]["type"] == ["string", "null"]
    assert el["confidence"]["type"] == "number"
    assert el["metadata"]["type"] == "object"


# ---------- chunk 形状 ----------

def test_chunk_ids_shape_batch102():
    ch = load_schema("document.schema.json")["$defs"]["chunk"][
        "properties"]
    assert ch["text"]["type"] == "string"
    ids = ch["source_element_ids"]
    assert ids["type"] == "array"
    assert ids["minItems"] == 1
    assert ids["items"]["type"] == "string"
    assert ids["items"]["minLength"] == 1


# ---------- annotation 数组 items ----------

def test_annotation_items_shapes_batch102():
    props = load_schema("annotation.schema.json")["properties"]
    assert props["chunk_boundary_anchors"]["type"] == "array"
    assert props["chunk_boundary_anchors"]["items"] == {
        "$ref": "#/$defs/boundary_anchor"}
    pair_items = props["figure_caption_pairs"]["items"]
    assert sorted(pair_items["required"]) == \
        ["caption_text", "figure_marker"]
    assert pair_items["additionalProperties"] is False
    head_items = props["heading_order"]["items"]
    assert sorted(head_items["required"]) == ["level", "text"]
    assert head_items["properties"]["level"] == {
        "type": "integer", "minimum": 1}
    assert head_items["additionalProperties"] is False


# ---------- report 顶层 ----------

def test_report_version_const_batch102():
    r = load_schema("evaluation-report.schema.json")["properties"]
    assert r["report_version"]["const"] == "1.1"
    assert "evaluator_version" not in r


def _minimal_report():
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": True,
            "evaluator_version": "1.1", "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-08-17T00:00:00+08:00"},
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0,
                   "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [{
            "doc_id": "d1", "source_type": "pdf", "metrics": {},
            "wall_time_seconds": {"total": 0.1, "parse": None,
                                  "chunk": None}}],
        "expected_failures": [],
    }


def test_minimal_report_valid_batch102():
    validate(_minimal_report(), "evaluation-report.schema.json")


def test_report_top_rejects_evaluator_version_batch102():
    bad = _minimal_report()
    bad["evaluator_version"] = "1.1"
    try:
        validate(bad, "evaluation-report.schema.json")
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        assert "'evaluator_version' was unexpected" in str(e)


# ---------- 多错误 message ----------

def test_multi_error_message_first_only_batch102():
    try:
        validate(
            {"annotation_version": "1.0", "doc_id": "d",
             "extra": 1,
             "chunk_boundary_anchors": [{"marker": ""}]},
            "annotation.schema.json")
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        msg = str(e)
        assert "3 处" in msg
        assert "Additional properties are not allowed" in msg
        assert len(e.errors) == 3
        paths = [tuple(err["path"]) for err in e.errors]
        assert () in paths  # 顶层 extra（list→tuple 后是 ()）
        assert ("chunk_boundary_anchors", 0, "marker") in paths


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch102():
    src = _src()
    assert "head = errors[0]" in src
    assert "校验失败 ({len(errors)} 处)：" in src
    assert "errors or []" in src


# ---------- forbidden tokens 第三百七十四批 ----------

def test_source_no_eval_batch102():
    assert "eval(" not in _src()


def test_source_no_exec_batch102():
    assert "exec(" not in _src()


def test_source_no_compile_batch102():
    assert "compile(" not in _src()


def test_source_no_globals_batch102():
    assert "globals(" not in _src()


def test_source_no_locals_batch102():
    assert "locals(" not in _src()


def test_source_no_os_system_batch102():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch102():
    assert "subprocess" not in _src()


def test_source_no_popen_batch102():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch102():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch102():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch102():
    assert "socket" not in _src()


def test_source_no_requests_batch102():
    assert "requests" not in _src()


def test_source_no_urllib_batch102():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch102():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch102():
    assert "yield" not in _src()


def test_source_no_async_await_batch102():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch102():
    assert _src().count("open(") == 2
