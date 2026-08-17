"""evaluation/schema.py 第二百八十五轮 edges 测试（Round 841）。

补强 edges88 未触及的角度（第二百一十五批）。

新角度（probe 实证）：
- document.schema.json 的 $id（edges87 只测了三个评测 Schema）
- annotation 最小合法形恰为 annotation_version + doc_id；
  additionalProperties=false → 未知顶层键在**父路径**报
  "Additional properties ('zz_extra') were not allowed"
- anchor items 必有 position（marker 反而不 required）→
  缺 position 报 path=["chunk_boundary_anchors", 0]
- 同一 document 内多字段错误按路径排序：
  doc_id(minLength) → path(minLength) → source_type(enum)
- 两个 document 都错 → doc 0 的错误先于 doc 1
- validate 成功显式返回 None
- forbidden tokens 第三百一十一批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- document $id ----------

def test_document_schema_id_batch55():
    s = load_schema("document.schema.json")
    assert s["$id"] == \
        "https://kvfs.local/schemas/document.schema.json"


# ---------- annotation 形态 ----------

def test_annotation_roundtrip_batch55(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "A", "position": "after"}]}),
        encoding="utf-8")
    validate_file(f, "annotation.schema.json")


def test_annotation_missing_doc_id_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"annotation_version": "1.0"},
                 "annotation.schema.json")
    first = ei.value.errors[0]
    assert first["path"] == []
    assert first["message"] == "'doc_id' is a required property"


def test_annotation_extra_top_key_rejected_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"annotation_version": "1.0", "doc_id": "d1",
                  "zz_extra": 1},
                 "annotation.schema.json")
    first = ei.value.errors[0]
    assert first["path"] == []
    assert first["message"] == \
        "Additional properties ('zz_extra') were not allowed"


def test_annotation_anchor_requires_position_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"annotation_version": "1.0", "doc_id": "d1",
                  "chunk_boundary_anchors": [{"marker": "A"}]},
                 "annotation.schema.json")
    first = ei.value.errors[0]
    assert first["path"] == ["chunk_boundary_anchors", 0]
    assert first["message"] == \
        "'position' is a required property"


# ---------- 多字段排序 ----------

def test_same_doc_field_error_order_batch55():
    bad = {"manifest_version": "1.0",
           "devset_status": "incomplete",
           "documents": [{"doc_id": "", "path": "",
                          "source_type": "bogus"}]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    got = [(er["path"], er["schema_path"][-1])
           for er in ei.value.errors]
    assert got == [
        (["documents", 0, "doc_id"], "minLength"),
        (["documents", 0, "path"], "minLength"),
        (["documents", 0, "source_type"], "enum"),
    ]


def test_two_docs_error_order_batch55():
    bad = {"manifest_version": "1.0",
           "devset_status": "incomplete",
           "documents": [
               {"doc_id": "a", "path": "x",
                "source_type": "bogus"},
               {"doc_id": "b", "path": "y",
                "source_type": "bogus"}]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    assert [er["path"] for er in ei.value.errors] == [
        ["documents", 0, "source_type"],
        ["documents", 1, "source_type"]]


# ---------- 返回值 ----------

def test_validate_success_returns_none_batch55():
    r = validate({"manifest_version": "1.0",
                  "devset_status": "incomplete",
                  "documents": []},
                 "manifest.schema.json")
    assert r is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent / \"schemas\"" in src
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src


# ---------- forbidden tokens 第三百一十一批 ----------

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
