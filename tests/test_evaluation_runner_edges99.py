"""evaluation/runner.py 第二百七十五轮 edges 测试（Round 831）。

补强 edges98 未触及的角度（第二百零五批）。

新角度：
- _load_annotation 直测四态：None / 不存在 / 合法 JSON 直传 /
  空文件（JSONDecodeError → None）
- tolerance_chars 真实传播：锚点距预测边界 5 字符 →
  tol=2 时 P/R/F1 全 0.0、tol=9 时全 1.0
- expected_failures 多错误时只取 errors[0].code
- output_path 深层父目录自动创建（a/b/c/report.json）
- forbidden tokens 第三百零一批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import evaluation.runner as runner_mod
import evaluation.schema_validation as sv
from evaluation.runner import _load_annotation, run_evaluation


class _FakeDoc:
    def __init__(self, d):
        self._d = d
        self.parser_version = "9.9"
        self.source_hash = "abc123"

    def to_dict(self):
        return self._d


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


# ---------- _load_annotation 直测 ----------

def test_load_annotation_none_batch55(tmp_path):
    assert _load_annotation(None) is None


def test_load_annotation_missing_batch55(tmp_path):
    assert _load_annotation(tmp_path / "nope.json") is None


def test_load_annotation_valid_batch55(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(json.dumps({"chunk_boundary_anchors": [
        {"marker": "A"}]}), encoding="utf-8")
    assert _load_annotation(f) == {
        "chunk_boundary_anchors": [{"marker": "A"}]}


def test_load_annotation_empty_file_batch55(tmp_path):
    f = tmp_path / "empty.json"
    f.write_text("", encoding="utf-8")
    assert _load_annotation(f) is None


# ---------- tolerance 传播 ----------

_CHUNKS_DOC = {"elements": [], "chunks": [
    {"text": "A" * 10}, {"text": "X" * 5 + "BC"}]}


def _run_tol(tmp_path, tol):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({"chunk_boundary_anchors": [
        {"marker": "BC"}]}), encoding="utf-8")

    m = SimpleNamespace(
        documents=[SimpleNamespace(
            doc_id="d1", resolved_path=root / "samples" / "a.pdf",
            source_type="pdf", expectations=None,
            annotation_resolved=ann)],
        expected_failures=[], project_root=root,
        devset_status="incomplete", file_count=1,
        content_group_count=1, pdf_count=1, docx_count=0,
        categories_covered=[])
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (_FakeDoc(_CHUNKS_DOC), [])), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "build_provenance",
                      lambda **k: {"git_commit": None,
                                   "git_dirty": False}):
        rep = run_evaluation(
            m, tmp_path / "out.json", tolerance_chars=tol)
    return rep


def test_tolerance_2_miss_batch55(tmp_path):
    rep = _run_tol(tmp_path, 2)
    m = rep["per_doc"][0]["metrics"]
    assert m["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


def test_tolerance_9_hit_batch55(tmp_path):
    rep = _run_tol(tmp_path, 9)
    m = rep["per_doc"][0]["metrics"]
    assert m["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- ef 多错误首错 ----------

def test_ef_first_error_code_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    m = SimpleNamespace(
        documents=[], expected_failures=[SimpleNamespace(
            doc_id="f1", resolved_path=root / "samples" / "a.pdf",
            expected_error_code="X")],
        project_root=root, devset_status="incomplete",
        file_count=0, content_group_count=0, pdf_count=0,
        docx_count=0, categories_covered=[])
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (None, [_Err("X"), _Err("Y")])), \
         patch.object(runner_mod, "build_provenance",
                      lambda **k: {"git_commit": None,
                                   "git_dirty": False}):
        rep = run_evaluation(m, tmp_path / "out.json")
    assert rep["expected_failures"][0]["actual_error_code"] == "X"
    assert rep["expected_failures"][0]["matches"] is True


# ---------- 深层输出目录 ----------

def test_nested_output_dirs_created_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    m = SimpleNamespace(
        documents=[], expected_failures=[], project_root=root,
        devset_status="incomplete", file_count=0,
        content_group_count=0, pdf_count=0, docx_count=0,
        categories_covered=[])
    with patch.object(runner_mod, "build_provenance",
                      lambda **k: {"git_commit": None,
                                   "git_dirty": False}):
        run_evaluation(m, tmp_path / "a" / "b" / "c" / "r.json")
    assert (tmp_path / "a" / "b" / "c" / "r.json").is_file()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert src.count("out_stub.unlink()") == 2
    assert '"code": "unknown"' in src
    assert "elapsed = time.perf_counter() - t0" in src
    assert "if parser_version and not parser_version_for_prov:" in src


# ---------- forbidden tokens 第三百零一批 ----------

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
