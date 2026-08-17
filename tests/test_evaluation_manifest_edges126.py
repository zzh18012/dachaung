"""evaluation/manifest.py 第四百六十二轮 edges 测试（Round 1018）。

补强 edges125 未触及的角度（第三百九十四批，probe 实证）。

新角度（expectations + annotation 双注线同文档回合）：
- 同一文档同时带 expectations 与 annotation_file → 经
  run_evaluation 后 per_doc 同时出 silent_drop_count=1
  （期望 paragraph 3 / 实际 2）与 chunk_boundary P/R 双 1.0
  （marker "second" before 恰落预测边界）；figure_caption
  仍 null parser_does_not_emit_relations——三线共存不互扰
- 邻文档两者皆无 → silent null no_expectations 与
  boundary null no_annotation 同屏（manifest 侧 wiring
  差异在报告侧可见）
- manifest 属性直读：expectations dict 原样、
  annotation_resolved 非 None
- forbidden tokens 第四百八十八批（open 1）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.manifest as manifest_mod
import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest


class _FakeDoc:
    parser_version = "pv1"
    source_hash = "ab12cd34"

    def to_dict(self):
        return {
            "elements": [
                {"element_id": "e1", "type": "paragraph",
                 "content": "first", "parent_id": None,
                 "confidence": 0.9, "metadata": {},
                 "source_locator": {"page": 1,
                                    "bbox": [0, 0, 1, 1]}},
                {"element_id": "e2", "type": "paragraph",
                 "content": "second", "parent_id": None,
                 "confidence": 0.9, "metadata": {},
                 "source_locator": {"page": 1,
                                    "bbox": [0, 0, 1, 1]}}],
            "chunks": [
                {"chunk_id": "c1", "text": "first",
                 "source_element_ids": ["e1"],
                 "char_count": 5},
                {"chunk_id": "c2", "text": "second",
                 "source_element_ids": ["e2"],
                 "char_count": 6}],
            "source_type": "pdf", "document_id": "x",
            "schema_version": "0.1.0", "source_path": "a.pdf",
            "source_hash": "a" * 64, "parser_name": "fallback",
            "parser_version": "pv1", "relations": [],
            "warnings": [], "errors": [], "metadata": {}}


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    for n in ("a.pdf", "b.pdf"):
        (tmp_path / "samples" / n).write_bytes(b"x")
    (tmp_path / "ann").mkdir()
    (tmp_path / "ann" / "d1.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "second", "position": "before"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/d1.json",
             "expectations": {"element_count_by_type":
                              {"paragraph": 3}}},
            {"doc_id": "d2", "path": "samples/b.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(mf, tmp_path)

    def fake_ps(path, stub, **kw):
        return _FakeDoc(), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps):
        rep = runner_mod.run_evaluation(m, tmp_path / "o.json")
    return m, rep


# ---------- manifest 属性直读 ----------

def test_manifest_dual_fields_batch216(tmp_path):
    m, _ = _run(tmp_path)
    d1 = m.documents[0]
    assert d1.expectations == {
        "element_count_by_type": {"paragraph": 3}}
    assert d1.annotation_resolved is not None
    assert d1.annotation_file_str == "ann/d1.json"
    assert m.documents[1].expectations is None
    assert m.documents[1].annotation_resolved is None


# ---------- 双注线同屏 ----------

def test_dual_wired_doc_metrics_batch216(tmp_path):
    _, rep = _run(tmp_path)
    d1 = rep["per_doc"][0]["metrics"]
    assert d1["silent_drop_count"] == {"value": 1,
                                       "reason": None}
    assert d1["chunk_boundary_precision"] == {"value": 1.0,
                                              "reason": None}
    assert d1["chunk_boundary_recall"] == {"value": 1.0,
                                           "reason": None}
    assert d1["figure_caption_f1"] == {
        "value": None,
        "reason": "parser_does_not_emit_relations"}


# ---------- 邻文档双 null ----------

def test_plain_doc_dual_nulls_batch216(tmp_path):
    _, rep = _run(tmp_path)
    d2 = rep["per_doc"][1]["metrics"]
    assert d2["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}
    assert d2["chunk_boundary_recall"] == {
        "value": None, "reason": "no_annotation"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch216():
    src = _src()
    assert 'expectations=d.get("expectations"),' in src
    assert "annotation_resolved = _resolve_relative_path(" in src
    assert 'paired_with=d.get("paired_with"),' in src


# ---------- forbidden tokens 第四百八十八批 ----------

def test_source_no_eval_batch216():
    assert "eval(" not in _src()


def test_source_no_exec_batch216():
    assert "exec(" not in _src()


def test_source_no_compile_batch216():
    assert "compile(" not in _src()


def test_source_no_globals_batch216():
    assert "globals(" not in _src()


def test_source_no_locals_batch216():
    assert "locals(" not in _src()


def test_source_no_os_system_batch216():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch216():
    assert "subprocess" not in _src()


def test_source_no_popen_batch216():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch216():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch216():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch216():
    assert "socket" not in _src()


def test_source_no_requests_batch216():
    assert "requests" not in _src()


def test_source_no_urllib_batch216():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch216():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch216():
    assert "yield" not in _src()


def test_source_no_async_await_batch216():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch216():
    assert _src().count("open(") == 1
