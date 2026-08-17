"""evaluation/runner.py 第四百五十七轮 edges 测试（Round 1013）。

补强 edges124 未触及的角度（第三百八十九批，probe 实证）。

新角度：
- document 与 errors 同时非空 → _process_one 走 errors 分支
  丢弃 document.parser_version → provenance.parser_version
  None（"pv-hidden" 被吞）；per_doc error_code 照记 "E_Y"
- ef 循环 process_single 抛异常 → RuntimeError 原样传播、
  报告文件不落盘（ef 循环在写盘前，无兜底）
- forbidden tokens 第四百八十三批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "pv-hidden"
    source_hash = "ab12cd34"

    def to_dict(self):
        return {"elements": [], "chunks": [],
                "source_type": "pdf", "document_id": "x",
                "schema_version": "0.1.0", "source_path": "a.pdf",
                "source_hash": "a" * 64,
                "parser_name": "fallback",
                "parser_version": "pv-hidden",
                "relations": [], "warnings": [], "errors": [],
                "metadata": {}}


class _FakeErr:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "bad.pdf").write_bytes(b"x")


def _manifest(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        **data}), encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(f, tmp_path)


# ---------- doc+errors 吞 parser_version ----------

def test_doc_with_errors_swallows_parser_version_batch211(
        tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m2.json", {
        "documents": [{"doc_id": "d1",
                       "path": "samples/bad.pdf",
                       "source_type": "pdf"}]})
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(),
                                    [_FakeErr("E_Y")])):
        rep = run_evaluation(m, tmp_path / "o2.json")
    assert rep["provenance"]["parser_version"] is None
    assert rep["per_doc"][0]["metrics"]["error_code"] == {
        "value": "E_Y", "reason": None}


# ---------- ef 循环异常 ----------

def test_ef_loop_exception_no_file_batch211(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m1.json", {
        "documents": [{"doc_id": "d1",
                       "path": "samples/bad.pdf",
                       "source_type": "pdf"}],
        "expected_failures": [
            {"doc_id": "ef1", "path": "samples/bad.pdf",
             "expected_error_code": "E_X"}]})

    def boom(path, stub, **kw):
        if "ef1" in str(stub):
            raise RuntimeError("ef-crash")
        return _FakeDoc(), []

    with patch.object(runner_mod, "process_single",
                      side_effect=boom), \
            pytest.raises(RuntimeError, match="ef-crash"):
        run_evaluation(m, tmp_path / "o.json")
    assert not (tmp_path / "o.json").exists()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch211():
    src = _src()
    assert 'return None, errors[0].to_dict(), elapsed, None, image_dir' in src
    assert "actual_code = errors[0].code if errors else None" in src
    assert "parser_version_for_prov: str | None = None" in src


# ---------- forbidden tokens 第四百八十三批 ----------

def test_source_no_eval_batch211():
    assert "eval(" not in _src()


def test_source_no_exec_batch211():
    assert "exec(" not in _src()


def test_source_no_compile_batch211():
    assert "compile(" not in _src()


def test_source_no_globals_batch211():
    assert "globals(" not in _src()


def test_source_no_locals_batch211():
    assert "locals(" not in _src()


def test_source_no_os_system_batch211():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch211():
    assert "subprocess" not in _src()


def test_source_no_popen_batch211():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch211():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch211():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch211():
    assert "socket" not in _src()


def test_source_no_requests_batch211():
    assert "requests" not in _src()


def test_source_no_urllib_batch211():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch211():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch211():
    assert "yield" not in _src()


def test_source_no_async_await_batch211():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch211():
    assert _src().count("open(") == 2
