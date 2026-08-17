"""evaluation/runner.py 第四百三十六轮 edges 测试（Round 992）。

补强 edges121 未触及的角度（第三百六十八批，probe 实证）。

新角度：
- process_single 抛异常（而非返回错误）→ 无 try/except 兜
  底 → RuntimeError 原样向上传播，报告文件不落盘
- expected_failures 的文档实际成功（无 errors）→
  actual_error_code None、matches False（None != 期望码）
- forbidden tokens 第四百六十二批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


class _Doc:
    parser_version = "pv"
    source_hash = "sh"

    def to_dict(self):
        return {"elements": [], "chunks": []}


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")


def _manifest(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete", **data}),
        encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(f, tmp_path)


# ---------- 异常传播 ----------

def test_process_single_exception_propagates_batch190(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m1.json", {
        "documents": [{"doc_id": "d1", "path": "s/a.pdf",
                       "source_type": "pdf"}]})
    with pytest.raises(RuntimeError, match="crash"), \
            patch.object(runner_mod, "process_single",
                         side_effect=RuntimeError("crash")):
        run_evaluation(m, tmp_path / "o1.json")
    assert not (tmp_path / "o1.json").exists()


# ---------- ef 文档实际成功 ----------

def test_ef_success_doc_actual_none_batch190(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m2.json", {
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "s/ok.pdf",
             "expected_error_code": "E_EXPECT"}]})
    with patch.object(runner_mod, "process_single",
                      return_value=(_Doc(), [])):
        rep = run_evaluation(m, tmp_path / "o2.json")
    assert rep["expected_failures"][0] == {
        "doc_id": "ef1",
        "expected_error_code": "E_EXPECT",
        "actual_error_code": None,
        "matches": False}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch190():
    src = _src()
    assert src.count("document, errors = process_single(") == 2
    assert src.count("if out_stub.is_file():") == 2
    assert "actual_code = errors[0].code if errors else None" in src
    assert "public_per_doc = []" in src


# ---------- forbidden tokens 第四百六十二批 ----------

def test_source_no_eval_batch190():
    assert "eval(" not in _src()


def test_source_no_exec_batch190():
    assert "exec(" not in _src()


def test_source_no_compile_batch190():
    assert "compile(" not in _src()


def test_source_no_globals_batch190():
    assert "globals(" not in _src()


def test_source_no_locals_batch190():
    assert "locals(" not in _src()


def test_source_no_os_system_batch190():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch190():
    assert "subprocess" not in _src()


def test_source_no_popen_batch190():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch190():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch190():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch190():
    assert "socket" not in _src()


def test_source_no_requests_batch190():
    assert "requests" not in _src()


def test_source_no_urllib_batch190():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch190():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch190():
    assert "yield" not in _src()


def test_source_no_async_await_batch190():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch190():
    assert _src().count("open(") == 2
