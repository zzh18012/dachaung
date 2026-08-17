"""evaluation/schema.py 第四百一十八轮 edges 测试（Round 974）。

补强 edges108 未触及的角度（第三百五十批，probe 实证）。

新角度：
- 三张 Schema 的 $id 统一为
  https://kvfs.local/schemas/<文件名>（第一次整表锁定）
- boundary_anchor def 细节全家福：
  - position "middle" → enum 拒绝（与
    annotation_metrics 把 middle 当 after 形成张力）
  - 缺 position → "'position' is a required property" @
    ['chunk_boundary_anchors', 0]
  - 额外键 weight → additionalProperties 拒绝
  - marker "" → "'' should be non-empty"
  - reason ""（无 minLength）→ 合法
- doc_id "" → 恰 1 处错误
- forbidden tokens 第四百四十四批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, load_schema, validate


def _base():
    return {"annotation_version": "1.0", "doc_id": "d1"}


# ---------- $id 统一 ----------

def test_schema_id_uri_pattern_batch172():
    for name in ("annotation.schema.json", "manifest.schema.json",
                 "evaluation-report.schema.json"):
        s = load_schema(name)
        assert s["$id"] == "https://kvfs.local/schemas/" + name


# ---------- boundary_anchor def 细节 ----------

def test_anchor_position_enum_rejects_middle_batch172():
    with pytest.raises(EvalSchemaError) as ei:
        validate({**_base(), "chunk_boundary_anchors": [
            {"marker": "AB", "position": "middle"}]},
            "annotation.schema.json")
    assert "'middle' is not one of ['before', 'after']" in \
        str(ei.value)


def test_anchor_position_required_batch172():
    with pytest.raises(EvalSchemaError) as ei:
        validate({**_base(), "chunk_boundary_anchors": [
            {"marker": "AB"}]}, "annotation.schema.json")
    flat = ei.value.errors[0]
    assert flat["message"] == "'position' is a required property"
    assert flat["path"] == ["chunk_boundary_anchors", 0]


def test_anchor_closed_additional_properties_batch172():
    with pytest.raises(EvalSchemaError) as ei:
        validate({**_base(), "chunk_boundary_anchors": [
            {"marker": "AB", "position": "after", "weight": 3}]},
            "annotation.schema.json")
    assert "Additional properties are not allowed " \
        "('weight' was unexpected)" in str(ei.value)


def test_anchor_marker_min_length_batch172():
    with pytest.raises(EvalSchemaError) as ei:
        validate({**_base(), "chunk_boundary_anchors": [
            {"marker": "", "position": "after"}]},
            "annotation.schema.json")
    assert "'' should be non-empty" in str(ei.value)


def test_anchor_empty_reason_valid_batch172():
    validate({**_base(), "chunk_boundary_anchors": [
        {"marker": "AB", "position": "after", "reason": ""}]},
        "annotation.schema.json")


# ---------- doc_id minLength ----------

def test_doc_id_empty_single_error_batch172():
    with pytest.raises(EvalSchemaError) as ei:
        validate({**_base(), "doc_id": ""},
                 "annotation.schema.json")
    assert len(ei.value.errors) == 1
    assert "'' should be non-empty" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch172():
    src = _src()
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert "raise FileNotFoundError(f\"Schema 文件不存在: {p}\")" in src
    assert "self.errors = errors or []" in src
    assert "f\"Schema '{schema_name}' 校验失败 ({len(errors)} 处)：\"" in src


# ---------- forbidden tokens 第四百四十四批 ----------

def test_source_no_eval_batch172():
    assert "eval(" not in _src()


def test_source_no_exec_batch172():
    assert "exec(" not in _src()


def test_source_no_compile_batch172():
    assert "compile(" not in _src()


def test_source_no_globals_batch172():
    assert "globals(" not in _src()


def test_source_no_locals_batch172():
    assert "locals(" not in _src()


def test_source_no_os_system_batch172():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch172():
    assert "subprocess" not in _src()


def test_source_no_popen_batch172():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch172():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch172():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch172():
    assert "socket" not in _src()


def test_source_no_requests_batch172():
    assert "requests" not in _src()


def test_source_no_urllib_batch172():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch172():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch172():
    assert "yield" not in _src()


def test_source_no_async_await_batch172():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch172():
    assert _src().count("open(") == 2
