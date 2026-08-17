"""evaluation/cli.py 第五百四十一轮 edges 测试（Round 1097）。

补强 edges134-136 未触及的角度（第四百七十三批，probe 实证）。

新角度（CLI 失败路径的四个盲区：逃逸 / 常量 / 分歧 / 裸条目）：
- **PermissionError 逃逸**：run --output 指向已存在
  目录 → main 不捕获 PermissionError——结构化
  错误纪律只覆盖清单侧，输出路径误用直接炸出
  （唯一的非结构化失败通道，probe 实证）
- **report_version 常量违例**：top-level "9.9" →
  rc 1 + "校验失败 (1 处)：'1.1' was expected @
  path=['report_version']"——CLI 层首锁 const 执法
- **版本分歧容忍**：top "9.9" + provenance "1.1" →
  仍恰好 1 处——provenance.report_version 是自由
  字符串，const 只铡 top-level
- **per_doc 裸条目拒绝**：[{"bogus_key": 1}] →
  rc 1 + "'doc_id' is a required property @
  path=['per_doc', 0]"（5 处之首）——per_doc def
  闭仓的 CLI 行为面（edges107 只做了内省）
- forbidden tokens 第五百六十八批（open 1）
"""

from __future__ import annotations

import inspect
import json
import pathlib

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


def _base_report(**over):
    rep = {
        "report_version": "1.1",
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0,
                   "docx_count": 0, "categories_covered": []},
        "provenance": {
            "git_commit": None, "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso":
                "2026-01-01T00:00:00+00:00"},
        "summary": {}, "per_doc": []}
    rep.update(over)
    return rep


def _validate(tmp_path, rep):
    rp = tmp_path / "rep.json"
    rp.write_text(json.dumps(rep), encoding="utf-8")
    return main(["validate-report", str(rp)])


# ---------- PermissionError 逃逸 ----------

def test_output_dir_permission_escape_batch296(tmp_path):
    (tmp_path / "adir").mkdir()
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    with pytest.raises(PermissionError):
        main(["run", "--manifest", str(mf),
              "--output", str(tmp_path / "adir")])


# ---------- report_version 常量违例 ----------

def test_report_version_const_rejected_batch296(
        tmp_path, capsys):
    rc = _validate(tmp_path, _base_report(
        report_version="9.9",
        provenance=dict(
            _base_report()["provenance"],
            report_version="9.9")))
    assert rc == 1
    out = capsys.readouterr().err
    assert "校验失败 (1 处)" in out
    assert ("'1.1' was expected @ "
            "path=['report_version']") in out


# ---------- 版本分歧容忍 ----------

def test_version_divergence_single_error_batch296(
        tmp_path, capsys):
    rc = _validate(tmp_path, _base_report(
        report_version="9.9"))
    assert rc == 1
    out = capsys.readouterr().err
    assert "校验失败 (1 处)" in out
    assert "provenance" not in out


# ---------- per_doc 裸条目拒绝 ----------

def test_bare_per_doc_entry_rejected_batch296(
        tmp_path, capsys):
    rc = _validate(tmp_path, _base_report(
        per_doc=[{"bogus_key": 1}]))
    assert rc == 1
    out = capsys.readouterr().err
    assert ("'doc_id' is a required property @ "
            "path=['per_doc', 0]") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch296():
    src = _src()
    assert "清单不存在" in src
    assert "文档不存在" in src


# ---------- forbidden tokens 第五百六十八批 ----------

def test_source_no_eval_batch296():
    assert "eval(" not in _src()


def test_source_no_exec_batch296():
    assert "exec(" not in _src()


def test_source_no_compile_batch296():
    assert "compile(" not in _src()


def test_source_no_globals_batch296():
    assert "globals(" not in _src()


def test_source_no_locals_batch296():
    assert "locals(" not in _src()


def test_source_no_os_system_batch296():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch296():
    assert "subprocess" not in _src()


def test_source_no_popen_batch296():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch296():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch296():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch296():
    assert "socket" not in _src()


def test_source_no_requests_batch296():
    assert "requests" not in _src()


def test_source_no_urllib_batch296():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch296():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch296():
    assert "yield" not in _src()


def test_source_no_async_await_batch296():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch296():
    assert _src().count("open(") == 1
