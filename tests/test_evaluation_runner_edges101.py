"""evaluation/runner.py 第二百八十九轮 edges 测试（Round 845）。

补强 edges100 未触及的角度（第二百一十九批）。

新角度：
- 报告顶层键序恰 6 项（report_version … expected_failures）且
  report_version 恒 "1.1"
- wall_time_seconds 完整形态（parse/chunk null +
  双 not_instrumented reason，runner 级锁定）
- per_doc 键序恰 4 项（doc_id → source_type → metrics →
  wall_time_seconds）
- 空 manifest 跑完不创建 _per_doc 目录
- ef 的 process_single 收到 stub 路径
  output_root/_per_doc/f1.json（位置参数捕获）
- 单 doc 集成：summary counts sum=2、participating=1
- forbidden tokens 第三百一十五批
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch

import evaluation.runner as runner_mod
import evaluation.schema_validation as sv
from evaluation.runner import run_evaluation


class _FakeDoc:
    def __init__(self, d):
        self._d = d
        self.parser_version = "1.0"
        self.source_hash = "abc123"

    def to_dict(self):
        return self._d


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


_TWO_EL_DOC = {
    "elements": [
        {"element_id": "e1", "type": "paragraph",
         "content": "A"},
        {"element_id": "e2", "type": "paragraph",
         "content": "B"}],
    "chunks": [{"text": "AB",
                "source_element_ids": ["e1", "e2"]}],
}


def _manifest(tmp_path, docs=(), ef=()):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    (root / "samples").mkdir(exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")

    def _entry(i=1):
        return SimpleNamespace(
            doc_id=f"d{i}",
            resolved_path=root / "samples" / "a.pdf",
            source_type="pdf", expectations=None,
            annotation_resolved=None)

    return SimpleNamespace(
        documents=[_entry(i + 1) for i in range(len(docs))] if
        isinstance(docs, int) else list(docs),
        expected_failures=list(ef), project_root=root,
        devset_status="incomplete",
        file_count=len(docs) if not isinstance(docs, int)
        else docs,
        content_group_count=1, pdf_count=1, docx_count=0,
        categories_covered=[])


def _run(m, out, ps=None):
    ps = ps or (lambda *a, **k: (_FakeDoc(_TWO_EL_DOC), []))
    with patch.object(runner_mod, "process_single", ps), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "build_provenance",
                      lambda **k: {"git_commit": None,
                                   "git_dirty": False}):
        return run_evaluation(m, out)


# ---------- 顶层键序 ----------

def test_report_top_key_order_batch55(tmp_path):
    m = _manifest(tmp_path, docs=[SimpleNamespace(
        doc_id="d1",
        resolved_path=tmp_path / "proj" / "samples" / "a.pdf",
        source_type="pdf", expectations=None,
        annotation_resolved=None)])
    rep = _run(m, tmp_path / "out.json")
    assert list(rep.keys()) == [
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures"]
    assert rep["report_version"] == "1.1"


# ---------- wall_time 完整形态 ----------

def test_wall_time_full_shape_batch55(tmp_path):
    m = _manifest(tmp_path, docs=[SimpleNamespace(
        doc_id="d1",
        resolved_path=tmp_path / "proj" / "samples" / "a.pdf",
        source_type="pdf", expectations=None,
        annotation_resolved=None)])
    rep = _run(m, tmp_path / "out.json")
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert list(wt.keys()) == [
        "total", "parse", "chunk", "parse_reason",
        "chunk_reason"]
    assert isinstance(wt["total"], float)
    assert wt["parse"] is None and wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# ---------- per_doc 键序 ----------

def test_per_doc_key_order_batch55(tmp_path):
    m = _manifest(tmp_path, docs=[SimpleNamespace(
        doc_id="d1",
        resolved_path=tmp_path / "proj" / "samples" / "a.pdf",
        source_type="pdf", expectations=None,
        annotation_resolved=None)])
    rep = _run(m, tmp_path / "out.json")
    assert list(rep["per_doc"][0].keys()) == [
        "doc_id", "source_type", "metrics",
        "wall_time_seconds"]


# ---------- 空 manifest ----------

def test_empty_manifest_no_per_doc_dir_batch55(tmp_path):
    m = _manifest(tmp_path, docs=[])
    rep = _run(m, tmp_path / "out.json")
    assert rep["per_doc"] == []
    assert not (tmp_path / "_per_doc").exists()


# ---------- ef stub 路径捕获 ----------

def test_ef_stub_path_capture_batch55(tmp_path):
    m = _manifest(tmp_path, docs=[], ef=[SimpleNamespace(
        doc_id="f1",
        resolved_path=tmp_path / "proj" / "samples" / "a.pdf",
        expected_error_code="X")])
    calls: list = []

    def _ps(*a, **k):
        calls.append(a)
        return (None, [_Err("X")])

    rep = _run(m, tmp_path / "out.json", ps=_ps)
    assert len(calls) == 1
    assert calls[0][1] == tmp_path / "_per_doc" / "f1.json"
    assert rep["expected_failures"][0]["matches"] is True


# ---------- summary counts 集成 ----------

def test_summary_counts_integration_batch55(tmp_path):
    m = _manifest(tmp_path, docs=[SimpleNamespace(
        doc_id="d1",
        resolved_path=tmp_path / "proj" / "samples" / "a.pdf",
        source_type="pdf", expectations=None,
        annotation_resolved=None)])
    rep = _run(m, tmp_path / "out.json")
    assert rep["summary"]["counts"]["element_count_total"] == {
        "sum": 2, "participating_docs": 1}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"' in src
    assert 'out_stub = output_root / "_per_doc" / f"{ef.doc_id}.json"' in src
    assert '"report_version": REPORT_VERSION,' in src


# ---------- forbidden tokens 第三百一十五批 ----------

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
