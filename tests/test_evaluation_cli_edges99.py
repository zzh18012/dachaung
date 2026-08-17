"""evaluation/cli.py 第二百七十六轮 edges 测试（Round 832）。

补强 edges98 未触及的角度（第二百零六批）。

新角度：
- _format_metric 全分支直测：float 4 位小数 / bool 小写 /
  null 带 reason（不补 ok）/ dict 按 key 排序 / 负 int /
  字符串 value 走兜底分支
- run 子命令三态：run_evaluation 抛 EvalSchemaError → rc1
  「生成的报告未通过 Schema 校验」；自校验失败 → rc1
  「报告自校验失败」；成功 → stdout 统计行 + git 前 12 位
- inspect-doc 头部五行 + --tolerance-chars 9 透传
  _tolerance_chars 行
- 无子命令 / --parser 非法 → SystemExit 2
- forbidden tokens 第三百零二批
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main
from evaluation.schema import EvalSchemaError


# ---------- _format_metric 全分支 ----------

def _fmt(value, reason=None):
    return _format_metric("n", {"value": value, "reason": reason})


def test_format_metric_float_batch55():
    assert _fmt(0.5) == f"  {'n':36} 0.5000  (ok)"


def test_format_metric_bool_batch55():
    assert _fmt(True) == f"  {'n':36} true  (ok)"
    assert _fmt(False) == f"  {'n':36} false  (ok)"


def test_format_metric_null_reason_batch55():
    assert _fmt(None, "no_annotation") == f"  {'n':36} null  (no_annotation)"


def test_format_metric_dict_sorted_batch55():
    assert _fmt({"b": 2, "a": 1}) == f"  {'n':36} a=1, b=2  (ok)"


def test_format_metric_negative_int_batch55():
    assert _fmt(-5) == f"  {'n':36} -5  (ok)"


def test_format_metric_string_fallback_batch55():
    assert _fmt("xyz") == f"  {'n':36} xyz  (ok)"


# ---------- run 三态 ----------

def _run_env(tmp_path, report, run_side=None):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    m = SimpleNamespace(project_root=tmp_path)
    return mf, m


def test_run_eval_schema_error_rc1_batch55(
        tmp_path, capsys):
    mf, m = _run_env(tmp_path, None)
    with patch.object(cli_mod, "load_manifest",
                      lambda p: m), \
         patch.object(cli_mod, "run_evaluation",
                      side_effect=EvalSchemaError("bad")), \
         patch.object(cli_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json")])
    assert rc == 1
    assert "生成的报告未通过 Schema 校验" in capsys.readouterr().err


def test_run_self_validate_fail_rc1_batch55(tmp_path, capsys):
    mf, m = _run_env(tmp_path, None)
    rep = {"per_doc": [], "devset": {"status": "incomplete",
                                     "file_count": 0}}
    with patch.object(cli_mod, "load_manifest",
                      lambda p: m), \
         patch.object(cli_mod, "run_evaluation",
                      lambda *a, **k: rep), \
         patch.object(cli_mod, "validate_file",
                      side_effect=EvalSchemaError("v")), \
         patch.object(cli_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json")])
    assert rc == 1
    assert "报告自校验失败" in capsys.readouterr().err


def test_run_success_stats_line_batch55(tmp_path, capsys):
    mf, m = _run_env(tmp_path, None)
    rep = {
        "per_doc": [
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "incomplete", "file_count": 3,
                   "content_group_count": 2, "pdf_count": 2,
                   "docx_count": 1},
    }
    with patch.object(cli_mod, "load_manifest",
                      lambda p: m), \
         patch.object(cli_mod, "run_evaluation",
                      lambda *a, **k: rep), \
         patch.object(cli_mod, "validate_file",
                      lambda p, s: None), \
         patch.object(cli_mod, "get_git_provenance",
                      lambda r: {"git_commit": "a" * 40,
                                 "git_dirty": True}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "documents=3（成功 2，失败 1）" in out
    assert "devset_status=incomplete file_count=3 groups=2" in out
    assert "pdf=2 docx=1" in out
    assert f"git_commit={'a' * 12} git_dirty=True" in out


# ---------- inspect-doc 头部 ----------

def test_inspect_doc_header_batch55(tmp_path, capsys):
    doc = {
        "document_id": "doc-1", "source_type": "pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]}],
    }
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "9"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"file:        {f}" in out
    assert "document_id: doc-1" in out
    assert "source:      ?  type=pdf" in out
    assert "parser:      fallback v1.0" in out
    assert "counts:      elements=1 chunks=1" in out
    assert f"  {'_tolerance_chars':36} 9  (ok)" in out


# ---------- argparse ----------

def test_no_subcommand_system_exit_batch55():
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


def test_bad_parser_choice_system_exit_batch55(tmp_path):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", str(mf),
              "--output", "o.json", "--parser", "bogus"])
    assert ei.value.code == 2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'if hasattr(sys.stdout, "reconfigure"):' in src
    assert "评测完成：{output_path}" in src
    assert "or 'unknown')[:12]}" in src


# ---------- forbidden tokens 第三百零二批 ----------

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


def test_source_open_count_is_1_batch55():
    assert _src().count("open(") == 1
