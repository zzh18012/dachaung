"""evaluation/runner.py 第四百四十三轮 edges 测试（Round 999）。

补强 edges122 未触及的角度（第三百七十五批，probe 实证）。

新角度（混合成功/失败集成流）：
- 一份清单 1 成功（带标注）+ 1 失败 + 1 ef 命中 → per_doc
  顺序保持清单序 ["d-ok", "d-fail"]
- 成功文档 2 chunk + marker "hello" after → 边界 P/R 1.0
  （标注端到端进入公开 metrics）
- 失败文档 error_code "E_X" + boundary P null "pipeline_failed"
- wall_time_seconds 恰 5 键：total float ≥0、parse/chunk
  None、双 reason "not_instrumented"
- ef expected E_X == actual E_X → matches True（真实 code 流）
- summary success 1/2 → rate 0.5
- _per_doc 目录留存但无 .json；输出 JSON 原文无任何下划线
  私有字段（_annotation_present/_tolerance_chars/
  _missing_markers）
- provenance.parser_version 来自首个成功文档 "pv-1"
- forbidden tokens 第四百六十九批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "pv-1"
    source_hash = "ab12cd34ef56"

    def to_dict(self):
        return {
            "schema_version": "0.1.0", "document_id": "x",
            "source_path": "a.pdf", "source_type": "pdf",
            "source_hash": "a" * 64, "parser_name": "fallback",
            "parser_version": "pv-1",
            "elements": [
                {"element_id": "e1", "type": "paragraph",
                 "content": "hello world", "parent_id": None,
                 "confidence": 0.9, "metadata": {},
                 "source_locator": {"page": 1,
                                    "bbox": [1, 2, 3, 4]}}],
            "chunks": [
                {"chunk_id": "c1", "text": "hello",
                 "source_element_ids": ["e1"], "char_count": 5},
                {"chunk_id": "c2", "text": "world",
                 "source_element_ids": ["e1"], "char_count": 5}],
            "relations": [], "warnings": [], "errors": [],
            "metadata": {}}


class _FakeErr:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _fake_ps(path, out_stub, **kw):
    if "bad" in str(path):
        return None, [_FakeErr("E_X")]
    return _FakeDoc(), []


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    for n in ("a.pdf", "bad.pdf"):
        (tmp_path / "samples" / n).write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d-ok", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "samples/ann.json"},
            {"doc_id": "d-fail", "path": "samples/bad.pdf",
             "source_type": "pdf"}],
        "expected_failures": [
            {"doc_id": "ef1", "path": "samples/bad.pdf",
             "expected_error_code": "E_X"}]}), encoding="utf-8")
    (tmp_path / "samples" / "ann.json").write_text(json.dumps({
        "doc_id": "d-ok",
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"}]}),
        encoding="utf-8")
    from evaluation.manifest import load_manifest
    m = load_manifest(mf, tmp_path)
    with patch.object(runner_mod, "process_single",
                      side_effect=_fake_ps):
        return run_evaluation(m, tmp_path / "o" / "r.json")


# ---------- 顺序保持 ----------

def test_mixed_run_order_preserved_batch197(tmp_path):
    rep = _run(tmp_path)
    assert [p["doc_id"] for p in rep["per_doc"]] == \
        ["d-ok", "d-fail"]


# ---------- 成功文档标注端到端 ----------

def test_success_doc_boundary_hit_batch197(tmp_path):
    rep = _run(tmp_path)
    m = rep["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {"value": 1.0,
                                             "reason": None}
    assert m["chunk_boundary_recall"] == {"value": 1.0,
                                          "reason": None}


# ---------- 失败文档指标 ----------

def test_failed_doc_metrics_null_batch197(tmp_path):
    rep = _run(tmp_path)
    m = rep["per_doc"][1]["metrics"]
    assert m["error_code"] == {"value": "E_X", "reason": None}
    assert m["pipeline_success"]["value"] is False
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- wall_time 5 键 ----------

def test_wall_time_five_key_shape_batch197(tmp_path):
    rep = _run(tmp_path)
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert list(wt.keys()) == ["total", "parse", "chunk",
                               "parse_reason", "chunk_reason"]
    assert type(wt["total"]) is float and wt["total"] >= 0
    assert wt["parse"] is None and wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# ---------- ef 命中 ----------

def test_ef_matches_true_flow_batch197(tmp_path):
    rep = _run(tmp_path)
    assert rep["expected_failures"] == [{
        "doc_id": "ef1", "expected_error_code": "E_X",
        "actual_error_code": "E_X", "matches": True}]


# ---------- 成功率 1/2 ----------

def test_success_rate_half_batch197(tmp_path):
    rep = _run(tmp_path)
    assert rep["summary"]["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


# ---------- _per_doc 与私有字段 ----------

def test_per_doc_dir_empty_no_leak_batch197(tmp_path):
    rep = _run(tmp_path)
    pd_dir = tmp_path / "o" / "_per_doc"
    assert pd_dir.is_dir()
    assert list(pd_dir.glob("*.json")) == []
    raw = (tmp_path / "o" / "r.json").read_text(encoding="utf-8")
    assert "_annotation_present" not in raw
    assert "_tolerance_chars" not in raw
    assert "_missing_markers" not in raw


# ---------- provenance parser_version ----------

def test_provenance_parser_version_from_doc_batch197(tmp_path):
    rep = _run(tmp_path)
    assert rep["provenance"]["parser_version"] == "pv-1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch197():
    src = _src()
    assert "image_dir if (image_dir is not None and image_dir.is_dir()) else None" in src
    assert '"parse_reason": "not_instrumented",' in src
    assert "out_p = Path(output_path)" in src
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


# ---------- forbidden tokens 第四百六十九批 ----------

def test_source_no_eval_batch197():
    assert "eval(" not in _src()


def test_source_no_exec_batch197():
    assert "exec(" not in _src()


def test_source_no_compile_batch197():
    assert "compile(" not in _src()


def test_source_no_globals_batch197():
    assert "globals(" not in _src()


def test_source_no_locals_batch197():
    assert "locals(" not in _src()


def test_source_no_os_system_batch197():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch197():
    assert "subprocess" not in _src()


def test_source_no_popen_batch197():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch197():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch197():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch197():
    assert "socket" not in _src()


def test_source_no_requests_batch197():
    assert "requests" not in _src()


def test_source_no_urllib_batch197():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch197():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch197():
    assert "yield" not in _src()


def test_source_no_async_await_batch197():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch197():
    assert _src().count("open(") == 2
