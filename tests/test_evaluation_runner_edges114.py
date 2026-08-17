"""evaluation/runner.py 第三百八十轮 edges 测试（Round 936）。

补强 edges113 未触及的角度（第三百一十二批，probe 实证）。

新角度：
- _load_annotation 直测五态：None / 文件不存在 / 坏 JSON /
  目录路径 → 全 None；合法文件 → dict（异常不外泄）
- wall_time_seconds 五键全序 [total, parse, chunk,
  parse_reason, chunk_reason]，parse/chunk 恒 None +
  "not_instrumented"
- 内部 per_doc 行七键全序（_annotation_present /
  _tolerance_chars / _missing_markers 居末三）与公开行
  四键对照（经 aggregate_summary spy 捕获）
- 报告顶层六键全序 [report_version, provenance, devset,
  summary, per_doc, expected_failures]
- tolerance_chars=7 → 内部行 _tolerance_chars 7、metrics
  中键已被 pop（不在 metrics）；缺省 30
- _missing_markers 缺省 []；有效标注 → _annotation_present
  True；坏 JSON 标注文件 → no_annotation（加载失败同无标注）
- _per_doc 目录生命周期：空清单不创建；有文档则创建且
  运行后为空（stub 已 unlink）
- forbidden tokens 第四百零六批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import _load_annotation, run_evaluation


class _FakeDoc:
    parser_version = "9.9"
    source_hash = "h"

    def __init__(self):
        self._d = {
            "elements": [{"element_id": "e1", "type": "paragraph",
                          "content": "AB"}],
            "chunks": [{"text": "AB",
                        "source_element_ids": ["e1"]}]}

    def to_dict(self):
        return self._d


def _mk(tmp_path, docs, ann_file=None):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    entry = {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"}
    if ann_file:
        entry["annotation_file"] = ann_file
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [entry] if docs else []}), encoding="utf-8")
    return load_manifest(f, tmp_path)


def _run(tmp_path, m, out_name="r.json", **kw):
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        return run_evaluation(m, tmp_path / out_name, **kw)


def _run_spy(tmp_path, m, captured, **kw):
    orig_agg = runner_mod.aggregate_summary

    def spy(rows):
        captured.extend(rows)
        return orig_agg(rows)

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=spy):
        return run_evaluation(m, tmp_path / "r.json", **kw)


# ---------- _load_annotation 五态 ----------

def test_load_annotation_matrix_batch134(tmp_path):
    assert _load_annotation(None) is None
    assert _load_annotation(tmp_path / "ghost.json") is None
    bad = tmp_path / "bad.ann"
    bad.write_text("{x", encoding="utf-8")
    assert _load_annotation(bad) is None
    assert _load_annotation(tmp_path) is None
    ok = tmp_path / "ok.ann"
    ok.write_text('{"a": 1}', encoding="utf-8")
    assert _load_annotation(ok) == {"a": 1}


# ---------- wall_time 五键 ----------

def test_wall_time_five_keys_batch134(tmp_path):
    rep = _run(tmp_path, _mk(tmp_path, [1]))
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert list(wt) == ["total", "parse", "chunk",
                        "parse_reason", "chunk_reason"]
    assert wt["parse"] is None and wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)


# ---------- 内部行七键 + 公开行四键 ----------

def test_internal_row_seven_keys_batch134(tmp_path):
    captured = []
    _run_spy(tmp_path, _mk(tmp_path, [1]), captured)
    row = captured[0]
    assert list(row) == [
        "doc_id", "source_type", "metrics", "wall_time_seconds",
        "_annotation_present", "_tolerance_chars",
        "_missing_markers"]
    rep_keys = ["doc_id", "source_type", "metrics",
                "wall_time_seconds"]
    assert list(_run(tmp_path, _mk(tmp_path, [1]),
                     out_name="r2.json")["per_doc"][0]) == rep_keys


# ---------- 报告顶层六键 ----------

def test_report_top_six_keys_batch134(tmp_path):
    rep = _run(tmp_path, _mk(tmp_path, [1]))
    assert list(rep) == [
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures"]


# ---------- tolerance 传播与 pop ----------

def test_tolerance_popped_and_propagated_batch134(tmp_path):
    captured = []
    _run_spy(tmp_path, _mk(tmp_path, [1]), captured,
             tolerance_chars=7)
    row = captured[0]
    assert row["_tolerance_chars"] == 7
    assert "_tolerance_chars" not in row["metrics"]
    captured2 = []
    _run_spy(tmp_path, _mk(tmp_path, [1]), captured2,
             tolerance_chars=99)
    assert captured2[0]["_tolerance_chars"] == 99


def test_missing_markers_default_empty_batch134(tmp_path):
    captured = []
    _run_spy(tmp_path, _mk(tmp_path, [1]), captured)
    assert captured[0]["_missing_markers"] == []
    assert captured[0]["_annotation_present"] is False


# ---------- 标注集成 ----------

def test_valid_annotation_present_true_batch134(tmp_path):
    ann = tmp_path / "d1.ann"
    ann.write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": "ZZZ"}]}),
        encoding="utf-8")
    captured = []
    _run_spy(tmp_path, _mk(tmp_path, [1], "d1.ann"), captured)
    assert captured[0]["_annotation_present"] is True


def test_malformed_annotation_no_annotation_batch134(tmp_path):
    bad = tmp_path / "badann.json"
    bad.write_text("{broken", encoding="utf-8")
    rep = _run(tmp_path, _mk(tmp_path, [1], "badann.json"))
    assert rep["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {
        "value": None, "reason": "no_annotation"}


# ---------- _per_doc 生命周期 ----------

def test_per_doc_dir_lifecycle_batch134(tmp_path):
    out = tmp_path / "empty_out" / "r.json"
    with patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(_mk(tmp_path, []), out)
    assert not (tmp_path / "empty_out" / "_per_doc").exists()
    out2 = tmp_path / "one_out" / "r.json"
    _run(tmp_path, _mk(tmp_path, [1]))
    assert (tmp_path / "_per_doc").exists()
    assert list((tmp_path / "_per_doc").iterdir()) == []


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch134():
    src = _src()
    assert 'if path is None or not path.is_file():' in src
    assert "except (OSError, json.JSONDecodeError):" in src
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src
    assert "if out_stub.is_file():" in src


# ---------- forbidden tokens 第四百零六批 ----------

def test_source_no_eval_batch134():
    assert "eval(" not in _src()


def test_source_no_exec_batch134():
    assert "exec(" not in _src()


def test_source_no_compile_batch134():
    assert "compile(" not in _src()


def test_source_no_globals_batch134():
    assert "globals(" not in _src()


def test_source_no_locals_batch134():
    assert "locals(" not in _src()


def test_source_no_os_system_batch134():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch134():
    assert "subprocess" not in _src()


def test_source_no_popen_batch134():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch134():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch134():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch134():
    assert "socket" not in _src()


def test_source_no_requests_batch134():
    assert "requests" not in _src()


def test_source_no_urllib_batch134():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch134():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch134():
    assert "yield" not in _src()


def test_source_no_async_await_batch134():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch134():
    assert _src().count("open(") == 2
