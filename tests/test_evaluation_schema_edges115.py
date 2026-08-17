"""evaluation/schema.py 第四百六十轮 edges 测试（Round 1016）。

补强 edges114 未触及的角度（第三百九十二批，probe 实证）。

新角度：
- 错误按 absolute_path 数值排序：12 个坏 doc 的错误路径
  ('documents', 0..11) 严格数值序 —— 索引 2 排在 10 前
  （字符串排序会得到 "10" < "2"，此处锁数值语义）
- annotation 锚点三态张力（schema 侧）：
  空 marker → "'' should be non-empty"（算法侧 R1015 只是
  防御性吞掉；schema 直接拒绝）
  缺 position → required（算法侧 a.get("position", "after")
  的默认值对合法标注不可达）
  position "middle" → enum "is not one of ['before', 'after']"
- 双空格 marker schema 合法但算法找不到（跨模块合成）：
  validate PASS + chunk_boundary_prf missing_markers 同锁
- annotation 全字段 kitchen-sink 通过
- forbidden tokens 第四百八十六批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.annotation_metrics import chunk_boundary_prf
from evaluation.schema import EvalSchemaError, validate


# ---------- 数值路径排序 ----------

def test_numeric_path_sort_batch214():
    m = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": [{"path": f"samples/d{i}.pdf",
                        "source_type": "pdf"}
                       for i in range(12)]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert len(paths) == 12
    assert paths[:4] == [("documents", 0), ("documents", 1),
                         ("documents", 2), ("documents", 3)]
    assert paths == sorted(paths)
    assert paths[2][1] == 2 and paths[10][1] == 10


# ---------- annotation 锚点张力 ----------

def _ann(anchors):
    return {"annotation_version": "1.0", "doc_id": "d",
            "chunk_boundary_anchors": anchors}


def test_annotation_empty_marker_rejected_batch214():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_ann([{"marker": "", "position": "after"}]),
                 "annotation.schema.json")
    err = ei.value.errors[0]
    assert err["message"] == "'' should be non-empty"
    assert err["path"] == ["chunk_boundary_anchors", 0, "marker"]


def test_annotation_position_required_batch214():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_ann([{"marker": "x"}]),
                 "annotation.schema.json")
    assert ei.value.errors[0]["message"] == \
        "'position' is a required property"


def test_annotation_position_enum_batch214():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_ann([{"marker": "x", "position": "middle"}]),
                 "annotation.schema.json")
    assert ei.value.errors[0]["message"] == \
        "'middle' is not one of ['before', 'after']"
    assert ei.value.errors[0]["path"] == \
        ["chunk_boundary_anchors", 0, "position"]


# ---------- 双空格 marker：schema 合法 + 算法缺失 ----------

def test_double_space_marker_legal_but_missing_batch214():
    ann = _ann([{"marker": "hello  world", "position": "after"}])
    validate(ann, "annotation.schema.json")
    doc = {"chunks": [{"text": "hello  world"}, {"text": "x"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert r["_missing_markers"] == {"value": ["hello  world"],
                                     "reason": None}
    assert r["chunk_boundary_recall"]["value"] is None


# ---------- kitchen-sink ----------

def test_annotation_kitchen_sink_valid_batch214():
    ann = {
        "annotation_version": "1.0", "doc_id": "d",
        "annotator": "reviewer_a", "date": "2026-08-17",
        "figure_caption_pairs": [{"figure_marker": "f",
                                  "caption_text": "c"}],
        "heading_order": [{"level": 1, "text": "h"}],
        "chunk_boundary_anchors": [{"marker": "x",
                                    "position": "before",
                                    "reason": "r"}]}
    validate(ann, "annotation.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch214():
    src = _src()
    assert "key=lambda e: list(e.absolute_path)" in src
    assert '"schema_path": list(err.absolute_schema_path),' in src
    assert "校验失败 ({len(errors)} 处)：" in src


# ---------- forbidden tokens 第四百八十六批 ----------

def test_source_no_eval_batch214():
    assert "eval(" not in _src()


def test_source_no_exec_batch214():
    assert "exec(" not in _src()


def test_source_no_compile_batch214():
    assert "compile(" not in _src()


def test_source_no_globals_batch214():
    assert "globals(" not in _src()


def test_source_no_locals_batch214():
    assert "locals(" not in _src()


def test_source_no_os_system_batch214():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch214():
    assert "subprocess" not in _src()


def test_source_no_popen_batch214():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch214():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch214():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch214():
    assert "socket" not in _src()


def test_source_no_requests_batch214():
    assert "requests" not in _src()


def test_source_no_urllib_batch214():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch214():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch214():
    assert "yield" not in _src()


def test_source_no_async_await_batch214():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch214():
    assert _src().count("open(") == 2
