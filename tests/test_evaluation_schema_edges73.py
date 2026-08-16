"""evaluation/schema.py 第一百零五轮 edges 测试（Round 729）。

补强 edges70/edges71/edges72 未触及的角度（第九十四批）。

新角度：
- validate 非 dict 实例（字符串）→ 根路径 [] 单错误
- 空 dict vs manifest → 3 错误全在 []、message 含 "(3 处)"
- annotation.schema.json 结构锁：最小合法 / annotation_version const "1.0" /
  anchor 必填 marker+position（与 metrics 的缺省补偿跨模块对照）/
  position 枚举 before·after / heading_order level minimum 1 /
  figure_caption_pairs 双 minLength / 根 additionalProperties false
- flat errors 可 json.dumps（含 int path 元素）
- 三个 $id 均含 kvfs.local
- _schema_path 直查 == SCHEMAS_DIR / name；SCHEMAS_DIR 绝对路径
- __all__ 五元素精确；EvalSchemaError.__init__ AST（1 Assign·2 Call·1 默认参数）
- forbidden tokens 第一百九十九批
"""

from __future__ import annotations

import ast
import inspect
import json

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
)


def _ann(**over) -> dict:
    payload = {"annotation_version": "1.0", "doc_id": "d"}
    payload.update(over)
    return payload


# ---------- 非 dict 实例 / 多错误 ----------

def test_validate_string_instance_root_error_batch53():
    with pytest.raises(EvalSchemaError) as ei:
        validate("x", "annotation.schema.json")
    assert len(ei.value.errors) == 1
    assert ei.value.errors[0]["path"] == []
    assert "'x' is not of type 'object'" in str(ei.value)


def test_empty_dict_manifest_three_root_errors_batch53():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert len(ei.value.errors) == 3
    assert [fe["path"] for fe in ei.value.errors] == [[], [], []]
    assert "(3 处)" in str(ei.value)


def test_flat_errors_json_dumpable_batch53():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"report_version": "1.1"}, "evaluation-report.schema.json")
    dumped = json.dumps(ei.value.errors)
    assert isinstance(dumped, str) and len(dumped) > 0


# ---------- annotation schema 结构锁 ----------

def test_annotation_minimal_valid_batch53():
    assert validate(_ann(), "annotation.schema.json") is None


def test_annotation_version_const_batch53():
    with pytest.raises(EvalSchemaError):
        validate(_ann(annotation_version="2.0"), "annotation.schema.json")


def test_annotation_doc_id_min_length_batch53():
    with pytest.raises(EvalSchemaError):
        validate(_ann(doc_id=""), "annotation.schema.json")


def test_annotation_annotator_empty_ok_date_empty_rejected_batch53():
    assert validate(_ann(annotator=""), "annotation.schema.json") is None
    with pytest.raises(EvalSchemaError):
        validate(_ann(date=""), "annotation.schema.json")


def test_anchor_requires_marker_and_position_batch53():
    # schema 层：marker+position 双必填 —— 而 metrics 的 .get 缺省
    # （marker ""/position "after"）只对未经 schema 校验的标注兜底
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[{"marker": "x"}]),
                 "annotation.schema.json")
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[{"position": "before"}]),
                 "annotation.schema.json")


def test_anchor_position_enum_batch53():
    assert validate(_ann(chunk_boundary_anchors=[
        {"marker": "x", "position": "before"}]), "annotation.schema.json") is None
    assert validate(_ann(chunk_boundary_anchors=[
        {"marker": "x", "position": "after"}]), "annotation.schema.json") is None
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[
            {"marker": "x", "position": "middle"}]), "annotation.schema.json")


def test_heading_order_level_minimum_batch53():
    ok = _ann(heading_order=[{"level": 1, "text": "t"}])
    assert validate(ok, "annotation.schema.json") is None
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": 0, "text": "t"}]),
                 "annotation.schema.json")


def test_heading_order_extra_key_rejected_batch53():
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": 1, "text": "t", "page": 2}]),
                 "annotation.schema.json")


def test_figure_caption_pairs_min_lengths_batch53():
    assert validate(_ann(figure_caption_pairs=[
        {"figure_marker": "f", "caption_text": "c"}]),
        "annotation.schema.json") is None
    with pytest.raises(EvalSchemaError):
        validate(_ann(figure_caption_pairs=[
            {"figure_marker": "", "caption_text": "c"}]),
            "annotation.schema.json")
    with pytest.raises(EvalSchemaError):
        validate(_ann(figure_caption_pairs=[{"figure_marker": "f"}]),
                 "annotation.schema.json")


def test_annotation_root_extra_key_rejected_batch53():
    with pytest.raises(EvalSchemaError):
        validate(_ann(bogus=1), "annotation.schema.json")


# ---------- 元数据 ----------

def test_schema_path_direct_batch53():
    assert _schema_path("manifest.schema.json") == \
        SCHEMAS_DIR / "manifest.schema.json"
    assert SCHEMAS_DIR.is_absolute()


def test_all_ids_contain_kvfs_batch53():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"):
        assert "kvfs.local" in load_schema(name)["$id"], name


def test_all_export_list_exact_batch53():
    assert schema_mod.__all__ == ["SCHEMAS_DIR", "EvalSchemaError",
                                  "load_schema", "validate", "validate_file"]
    tree = ast.parse(inspect.getsource(schema_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__")
    assert [e.value for e in all_assign.value.elts] == schema_mod.__all__


# ---------- AST 补强 ----------

def test_ast_eval_error_init_batch53():
    import collections
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef))
    c = collections.Counter(type(n).__name__ for n in ast.walk(init))
    assert (c["Assign"], c["Call"], c["BoolOp"]) == (1, 2, 1)
    assert [a.arg for a in init.args.args] == ["self", "message", "errors"]
    assert len(init.args.defaults) == 1  # errors=None


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_error_class_docstring_batch53():
    src = _src()
    assert "errors 给程序看，message 给人看" in src
    assert "不与 app/schema.py 复用" in src


# ---------- forbidden tokens 第一百九十九批 ----------

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
