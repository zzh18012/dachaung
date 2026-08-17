"""evaluation/schema.py 第二百二十二轮 edges 测试（Round 778）。

补强 edges76-79 未触及的角度（第一百四十二批）。

新角度：
- annotation 顶层形态：required 恰 2（annotation_version + doc_id）、
  addProps false、7 属性键全集
- figure_caption_pairs 条目锁：required [figure_marker,
  caption_text]、双 minLength 1、addProps false
- heading_order 条目锁：required [level, text]、level integer
  minimum 1、addProps false、level 0 → "less than the minimum of 1"
- annotator 空串放行（脱敏字段可空）vs doc_id/date 空串
  minLength 1 拒（三字段宽松度对照）
- 嵌套 flat 行：anchors[0].marker 传 int → path
  ['chunk_boundary_anchors', 0, 'marker'] + "is not of type
  'string'"
- report provenance max_chars：integer + minimum 1
  （负数/0 拒的基础）；report_version const "1.1" 锁定；
  categories_covered array of string
- document.schema.json 可经 evaluation.schema.load_schema 加载
  （$id / title "KVFS Document Model v0.1" / type object）
- forbidden tokens 第二百四十八批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
)

_BASE = {"annotation_version": "1.0", "doc_id": "d"}


def _ann():
    return load_schema("annotation.schema.json")


def _reject(obj, name="annotation.schema.json"):
    with pytest.raises(EvalSchemaError) as ei:
        validate(obj, name)
    return ei.value


# ---------- annotation 顶层 ----------

def test_annotation_top_level_shape_batch54():
    ann = _ann()
    assert ann["required"] == ["annotation_version", "doc_id"]
    assert ann["additionalProperties"] is False
    assert sorted(ann["properties"]) == [
        "annotation_version", "annotator", "chunk_boundary_anchors",
        "date", "doc_id", "figure_caption_pairs", "heading_order"]


# ---------- figure_caption_pairs 条目 ----------

def test_figure_caption_pair_item_locks_batch54():
    fcp = _ann()["properties"]["figure_caption_pairs"]["items"]
    assert fcp["required"] == ["figure_marker", "caption_text"]
    assert fcp["additionalProperties"] is False
    assert fcp["properties"]["figure_marker"]["minLength"] == 1
    assert fcp["properties"]["caption_text"]["minLength"] == 1


# ---------- heading_order 条目 ----------

def test_heading_order_item_locks_batch54():
    ho = _ann()["properties"]["heading_order"]["items"]
    assert ho["required"] == ["level", "text"]
    assert ho["additionalProperties"] is False
    assert ho["properties"]["level"] == {"type": "integer",
                                         "minimum": 1}


def test_heading_level_zero_rejected_batch54():
    e = _reject({**_BASE, "heading_order": [{"level": 0, "text": "x"}]})
    assert e.errors[0]["path"] == ["heading_order", 0, "level"]
    assert "less than the minimum of 1" in e.errors[0]["message"]


# ---------- 空串宽松度 ----------

def test_annotator_empty_allowed_batch54():
    validate({**_BASE, "annotator": ""}, "annotation.schema.json")


def test_doc_id_and_date_empty_rejected_batch54():
    e = _reject({**_BASE, "doc_id": ""})
    assert e.errors[0]["path"] == ["doc_id"]
    e2 = _reject({**_BASE, "date": ""})
    assert e2.errors[0]["path"] == ["date"]


# ---------- 嵌套 flat 行 ----------

def test_nested_marker_int_flat_row_batch54():
    e = _reject({**_BASE, "chunk_boundary_anchors":
                 [{"marker": 5, "position": "after"}]})
    assert e.errors[0]["path"] == ["chunk_boundary_anchors", 0,
                                   "marker"]
    assert "5 is not of type 'string'" in e.errors[0]["message"]


# ---------- report schema 细节 ----------

def test_provenance_max_chars_constraints_batch54():
    rep = load_schema("evaluation-report.schema.json")
    mc = rep["$defs"]["provenance"]["properties"]["max_chars"]
    assert mc == {"type": "integer", "minimum": 1}


def test_report_version_const_locked_batch54():
    rep = load_schema("evaluation-report.schema.json")
    assert rep["properties"]["report_version"] == {"type": "string",
                                                   "const": "1.1"}


def test_devset_categories_covered_type_batch54():
    rep = load_schema("evaluation-report.schema.json")
    cc = rep["$defs"]["devset"]["properties"]["categories_covered"]
    assert cc == {"type": "array", "items": {"type": "string"}}


# ---------- document.schema.json 经 evaluation.schema 加载 ----------

def test_document_schema_loadable_batch54():
    doc = load_schema("document.schema.json")
    assert doc["$id"] == "https://kvfs.local/schemas/document.schema.json"
    assert doc["type"] == "object"
    assert doc["title"] == "KVFS Document Model v0.1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_load_and_path_batch54():
    src = _src()
    assert "SCHEMAS_DIR / name" in src
    assert 'f"Schema 文件不存在: {p}"' in src
    assert 'encoding="utf-8"' in src


# ---------- forbidden tokens 第二百四十八批 ----------

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
