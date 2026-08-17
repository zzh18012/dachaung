"""evaluation/runner.py 第四百七十一轮 edges 测试（Round 1027）。

补强 edges126 未触及的角度（第四百零三批，probe 实证）。

新角度（全量报告 RS 合法性组合）：
- 双接线 doc（annotation_file 真标注 + expectations）
  与 expected_failures 同一 manifest、同一次 run 产出：
  产出报告通过 evaluation-report.schema.json 全量校验
  ——此前 edges121 真标注端到端无 ef、edges20/21 有
  ef 无 annotation，edges103 有两者但 summary 被打桩
  成 {"sentinel": 1} 无法过 RS
- 同屏共存四路非空信号：per_doc boundary P 1.0
  （真标注驱动）、silent_drop_count 3（expectations
  5 - 实际 2）、ef actual==expected matches True、
  summary silent_drop_total 3 + boundary macro 1.0
- forbidden tokens 第四百九十七批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate_file


class _FakeDoc:
    parser_version = "pv"
    source_hash = "sh"

    def to_dict(self):
        return {"elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "AB"},
            {"element_id": "e2", "type": "paragraph",
             "content": "CD"}],
            "chunks": [{"text": "AB",
                        "source_element_ids": ["e1"]},
                       {"text": "CD",
                        "source_element_ids": ["e2"]}]}


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "samples" / "bad.pdf").write_bytes(b"garbage")
    (tmp_path / "anns").mkdir()
    (tmp_path / "anns" / "ann.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "AB", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf",
                       "annotation_file": "anns/ann.json",
                       "expectations": {"element_count_by_type":
                                        {"paragraph": 5}}}],
        "expected_failures": [
            {"doc_id": "f1", "path": "samples/bad.pdf",
             "expected_error_code": "E_PARSE_FAIL"}]}),
        encoding="utf-8")
    m = load_manifest(mf, tmp_path)

    def fake_ps(path, *a, **kw):
        if path.name == "bad.pdf":
            return None, [_Err("E_PARSE_FAIL")]
        return _FakeDoc(), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps):
        return run_evaluation(m, tmp_path / "o.json"), tmp_path


# ---------- 全量报告 RS 校验 ----------

def test_dual_wired_plus_ef_report_rs_valid_batch225(tmp_path):
    rep, root = _run(tmp_path)
    validate_file(root / "o.json",
                  "evaluation-report.schema.json")


# ---------- 四路非空信号同屏 ----------

def test_four_nonnull_signals_coexist_batch225(tmp_path):
    rep, _ = _run(tmp_path)
    pd = rep["per_doc"][0]["metrics"]
    assert pd["chunk_boundary_precision"] == {"value": 1.0,
                                              "reason": None}
    assert pd["chunk_boundary_f1"]["value"] == 1.0
    assert pd["silent_drop_count"] == {"value": 3,
                                       "reason": None}
    assert rep["expected_failures"] == [{
        "doc_id": "f1", "expected_error_code": "E_PARSE_FAIL",
        "actual_error_code": "E_PARSE_FAIL", "matches": True}]


# ---------- summary 侧聚合同屏 ----------

def test_summary_macro_and_total_coexist_batch225(tmp_path):
    rep, _ = _run(tmp_path)
    s = rep["summary"]
    assert s["silent_drop_total"] == 3
    assert s["ratio_macro_averages"]["chunk_boundary_f1"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch225():
    src = _src()
    assert '"actual_error_code": actual_code,' in src
    assert ("\"matches\": actual_code =="
            " ef.expected_error_code,") in src
    assert "document, errors = process_single(" in src


# ---------- forbidden tokens 第四百九十七批 ----------

def test_source_no_eval_batch225():
    assert "eval(" not in _src()


def test_source_no_exec_batch225():
    assert "exec(" not in _src()


def test_source_no_compile_batch225():
    assert "compile(" not in _src()


def test_source_no_globals_batch225():
    assert "globals(" not in _src()


def test_source_no_locals_batch225():
    assert "locals(" not in _src()


def test_source_no_os_system_batch225():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch225():
    assert "subprocess" not in _src()


def test_source_no_popen_batch225():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch225():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch225():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch225():
    assert "socket" not in _src()


def test_source_no_requests_batch225():
    assert "requests" not in _src()


def test_source_no_urllib_batch225():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch225():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch225():
    assert "yield" not in _src()


def test_source_no_async_await_batch225():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch225():
    assert _src().count("open(") == 2
