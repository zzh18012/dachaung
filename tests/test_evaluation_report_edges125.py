"""evaluation/report.py 第五百三十二轮 edges 测试（Round 1088）。

补强 edges122-124 未触及的角度（第四百六十四批，probe 实证）。

新角度（退化 run 的报告形态三联）：
- **空清单 12 项 macro 全同形**：documents [] 真实 run
  → ratio_macro_averages 恰 12 键、值集合只有一种
  {macro_average None, participating_docs 0,
  not_evaluated 0}——退化不产生分化的参与度
- **ef-only 板**（documents [] + 一条 ef 真跑）：per_doc
  []、ef 条目四键 {doc_id, expected_error_code,
  actual_error_code docx_open_failed, matches True}、
  success {0, 0, rate None}——ef 命中不点亮任何
  pipeline 成功账（total 只数 documents）
- **仓外 provenance**：tmp 非 git 仓 → git_commit None /
  git_dirty False；fallback 的 parser_version None；
  max_chars 200 与 parser_name fallback 如实入档
- forbidden tokens 第五百五十九批（report 变体：15 项
  去 subprocess + open 0 + subprocess.run == 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _run(tmp_path, ef, name="m.json"):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "b.docx").write_bytes(
        b"fake not docx")
    (tmp_path / name).write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": ef}), encoding="utf-8")
    return run_evaluation(load_manifest(tmp_path / name,
                                        tmp_path),
                          tmp_path / "o.json", max_chars=200)


# ---------- 空清单 macro 全同形 ----------

def test_empty_board_macros_uniform_batch287(tmp_path):
    rep = _run(tmp_path, [])
    ra = rep["summary"]["ratio_macro_averages"]
    assert len(ra) == 12
    shapes = {json.dumps(v, sort_keys=True)
              for v in ra.values()}
    assert shapes == {
        '{"macro_average": null, "not_evaluated": 0,'
        ' "participating_docs": 0}'}


# ---------- ef-only 板 ----------

def test_ef_only_board_batch287(tmp_path):
    rep = _run(tmp_path, [{
        "doc_id": "f1", "path": "samples/b.docx",
        "expected_error_code": "docx_open_failed"}])
    assert rep["per_doc"] == []
    assert rep["expected_failures"] == [{
        "doc_id": "f1",
        "expected_error_code": "docx_open_failed",
        "actual_error_code": "docx_open_failed",
        "matches": True}]
    assert rep["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 0,
                             "total": 0, "rate": None}}


# ---------- 仓外 provenance ----------

def test_provenance_outside_repo_batch287(tmp_path):
    rep = _run(tmp_path, [])
    prov = rep["provenance"]
    assert prov["git_commit"] is None
    assert prov["git_dirty"] is False
    assert prov["parser_version"] is None
    assert prov["parser_name"] == "fallback"
    assert prov["max_chars"] == 200


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch287():
    src = _src()
    assert "def build_provenance(" in src
    assert "run_timestamp_iso" in src


# ---------- forbidden tokens 第五百五十九批（report 变体） ----------

def test_source_no_eval_batch287():
    assert "eval(" not in _src()


def test_source_no_exec_batch287():
    assert "exec(" not in _src()


def test_source_no_compile_batch287():
    assert "compile(" not in _src()


def test_source_no_globals_batch287():
    assert "globals(" not in _src()


def test_source_no_locals_batch287():
    assert "locals(" not in _src()


def test_source_no_os_system_batch287():
    assert "os.system" not in _src()


def test_source_no_popen_batch287():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch287():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch287():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch287():
    assert "socket" not in _src()


def test_source_no_requests_batch287():
    assert "requests" not in _src()


def test_source_no_urllib_batch287():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch287():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch287():
    assert "yield" not in _src()


def test_source_no_async_await_batch287():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch287():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch287():
    assert _src().count("subprocess.run") == 2
