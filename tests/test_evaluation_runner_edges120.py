"""evaluation/runner.py 第四百二十二轮 edges 测试（Round 978）。

补强 edges119 未触及的角度（第三百五十四批，probe 实证）。

新角度：
- _process_one 拿到 (None, [])（无文档无错误）→ 构造 code
  "unknown" + message "process_single returned None without
  errors"、parser_version None、image_dir None
- document 与 errors 并存：image_dir 在 errors 检查前已按
  source_hash 计算 → 错误五元组仍携带非 None image_dir
  （images-abc123），document 被丢弃为 None
- expected_failures matches 双路：码分歧 False / 码一致 True
- forbidden tokens 第四百四十八批（open 2）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import _process_one, run_evaluation


class _Doc:
    source_hash = "abc123"
    parser_version = "pv-1"

    def to_dict(self):
        return {"ok": True}


class _Err:
    code = "E_X"

    def to_dict(self):
        return {"code": "E_X", "message": "m"}


class _ErrDyn:
    def __init__(self, c):
        self.code = c

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _doc(tmp_path):
    return types.SimpleNamespace(
        doc_id="d1", resolved_path=tmp_path / "a.pdf")


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")


# ---------- (None, []) → unknown ----------

def test_process_one_unknown_error_path_batch176(tmp_path):
    _setup(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [])):
        out, err, elapsed, pv, idir = _process_one(
            _doc(tmp_path), tmp_path, "fallback", 800)
    assert out is None
    assert err == {"code": "unknown",
                   "message": "process_single returned None "
                              "without errors"}
    assert elapsed >= 0.0
    assert pv is None
    assert idir is None


# ---------- document + errors → image_dir 保留 ----------

def test_process_one_doc_with_errors_keeps_image_dir_batch176(
        tmp_path):
    _setup(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_Doc(), [_Err()])):
        out, err, elapsed, pv, idir = _process_one(
            _doc(tmp_path), tmp_path, "fallback", 800)
    assert out is None
    assert err == {"code": "E_X", "message": "m"}
    assert pv is None
    assert idir is not None
    assert idir.name == "images-abc123"


# ---------- ef matches 双路 ----------

def _ef_manifest(tmp_path, code_expected):
    f = tmp_path / f"m_{code_expected}.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.pdf",
             "expected_error_code": code_expected}]}),
        encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(f, tmp_path)


def test_ef_matches_false_on_divergence_batch176(tmp_path):
    _setup(tmp_path)
    m = _ef_manifest(tmp_path, "E_EXPECT")
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_ErrDyn("E_ACTUAL")])):
        rep = run_evaluation(m, tmp_path / "o1.json")
    r = rep["expected_failures"][0]
    assert r == {"doc_id": "ef1",
                 "expected_error_code": "E_EXPECT",
                 "actual_error_code": "E_ACTUAL",
                 "matches": False}


def test_ef_matches_true_on_same_code_batch176(tmp_path):
    _setup(tmp_path)
    m = _ef_manifest(tmp_path, "E_SAME")
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_ErrDyn("E_SAME")])):
        rep = run_evaluation(m, tmp_path / "o2.json")
    r = rep["expected_failures"][0]
    assert r["actual_error_code"] == "E_SAME"
    assert r["matches"] is True


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch176():
    src = _src()
    assert '"code": "unknown", "message": "process_single returned None without errors"' in src
    assert "image_dir = image_output_dir_for(out_stub, document.source_hash)" in src
    assert '"matches": actual_code == ef.expected_error_code,' in src
    assert "if parser_version and not parser_version_for_prov:" in src


# ---------- forbidden tokens 第四百四十八批 ----------

def test_source_no_eval_batch176():
    assert "eval(" not in _src()


def test_source_no_exec_batch176():
    assert "exec(" not in _src()


def test_source_no_compile_batch176():
    assert "compile(" not in _src()


def test_source_no_globals_batch176():
    assert "globals(" not in _src()


def test_source_no_locals_batch176():
    assert "locals(" not in _src()


def test_source_no_os_system_batch176():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch176():
    assert "subprocess" not in _src()


def test_source_no_popen_batch176():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch176():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch176():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch176():
    assert "socket" not in _src()


def test_source_no_requests_batch176():
    assert "requests" not in _src()


def test_source_no_urllib_batch176():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch176():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch176():
    assert "yield" not in _src()


def test_source_no_async_await_batch176():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch176():
    assert _src().count("open(") == 2
