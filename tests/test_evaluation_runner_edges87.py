"""evaluation/runner.py 第二百零五轮 edges 测试（Round 747）。

补强 edges85/edges86 未触及的角度（第一百一十二批）。

新角度：
- 调用顺序：文档循环先于 ef 循环（捕获 [d1, d2, ef1]）
- build_provenance 收到 manifest.project_root（非 output 目录）
- 真实 annotation 文件 e2e：带标注文档 chunk_boundary_precision 1.0、
  无标注文档 no_annotation —— 同一份报告内对照
- 多文档 metrics 键集一致
- devset 从 manifest 真实计数（pdf 1 / docx 1）
- 磁盘 indent=2（第二行 '  "report_version": '）
- forbidden tokens 第二百一十七批
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import run_evaluation

ROOT = Path(__file__).resolve().parents[1]


class _DocObj:
    source_hash = "h"
    parser_version = "pv"

    def to_dict(self):
        return {"document_id": "x", "source_type": "pdf",
                "elements": [],
                "chunks": [{"text": "AB"}, {"text": "CD"}]}


class _FakeErr:
    code = "open_error"

    def to_dict(self):
        return {"code": "open_error", "message": "m"}


@pytest.fixture
def capture(monkeypatch):
    state = {"calls": [], "prov": []}

    def fake_ps(inp, out, parser_name="fallback", max_chars=800,
                write_json=False):
        state["calls"].append(out.stem)
        if out.stem.startswith("ef"):
            return None, [_FakeErr()]
        return _DocObj(), []

    def fake_bp(project_root, **k):
        state["prov"].append(project_root)
        return {"git_commit": None, "git_dirty": False,
                "evaluator_version": "1.1", "report_version": "1.1",
                "parser_name": "fallback", "parser_version": None,
                "dependencies": {}, "max_chars": 800,
                "run_timestamp_iso": "t"}
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    monkeypatch.setattr(runner_mod, "build_provenance", fake_bp)
    return state


def _entry(i, st="pdf", ann=None):
    return DocumentEntry(
        doc_id=i, path_str=f"{i}.pdf", resolved_path=ROOT / f"{i}.pdf",
        source_type=st, sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=ann,
        expectations=None)


def _ef(i="ef1", code="open_error"):
    return ExpectedFailure(doc_id=i, path_str=f"{i}.pdf",
                           resolved_path=ROOT / f"{i}.pdf",
                           expected_error_code=code, source_type=None)


# ---------- 顺序与根 ----------

def test_doc_loop_before_ef_loop_batch54(capture, tmp_path):
    man = Manifest("1.0", "incomplete", (_entry("d1"), _entry("d2")),
                   (_ef(),), ROOT)
    run_evaluation(man, tmp_path / "r.json")
    assert capture["calls"] == ["d1", "d2", "ef1"]


def test_provenance_gets_manifest_root_batch54(capture, tmp_path):
    man = Manifest("1.0", "incomplete", (_entry("d1"),), (), ROOT)
    run_evaluation(man, tmp_path / "r.json")
    assert capture["prov"] == [ROOT]


# ---------- annotation e2e ----------

def test_annotation_e2e_contrast_batch54(capture, tmp_path):
    ann_f = tmp_path / "d1.json"
    ann_f.write_text(json.dumps({"chunk_boundary_anchors": [
        {"marker": "AB", "position": "after"}]}), encoding="utf-8")
    man = Manifest("1.0", "incomplete",
                   (_entry("d1", ann=ann_f), _entry("d2", "docx")),
                   (), ROOT)
    rep = run_evaluation(man, tmp_path / "r.json")
    with_ann = rep["per_doc"][0]["metrics"]["chunk_boundary_precision"]
    without = rep["per_doc"][1]["metrics"]["chunk_boundary_precision"]
    assert with_ann == {"value": 1.0, "reason": None}
    assert without == {"value": None, "reason": "no_annotation"}


# ---------- 多文档一致性 ----------

def test_multi_doc_metric_keysets_equal_batch54(capture, tmp_path):
    man = Manifest("1.0", "incomplete",
                   (_entry("d1"), _entry("d2", "docx")), (), ROOT)
    rep = run_evaluation(man, tmp_path / "r.json")
    assert (set(rep["per_doc"][0]["metrics"])
            == set(rep["per_doc"][1]["metrics"]))


def test_devset_counts_from_manifest_batch54(capture, tmp_path):
    man = Manifest("1.0", "incomplete",
                   (_entry("d1"), _entry("d2", "docx")), (), ROOT)
    rep = run_evaluation(man, tmp_path / "r.json")
    assert rep["devset"]["pdf_count"] == 1
    assert rep["devset"]["docx_count"] == 1
    assert rep["devset"]["file_count"] == 2


# ---------- 磁盘格式 ----------

def test_disk_indent_two_batch54(capture, tmp_path):
    out = tmp_path / "r.json"
    run_evaluation(Manifest("1.0", "incomplete", (_entry("d1"),), (),
                            ROOT), out)
    lines = io.open(out, encoding="utf-8").read().splitlines()
    assert lines[1] == '  "report_version": "1.1",'
    assert lines[0] == "{"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_provenance_root_arg_batch54():
    assert "project_root=manifest.project_root" in _src()


# ---------- forbidden tokens 第二百一十七批 ----------

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
