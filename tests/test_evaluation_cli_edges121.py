"""evaluation/cli.py 第四百三十轮 edges 测试（Round 986）。

补强 edges120 未触及的角度（第三百六十二批，probe 实证）。

新角度：
- main([]) → argparse required 子命令 → SystemExit code 2
- --parser kreuzberg（choices 第二项）与 --max-chars -800
  （负数 int 照收）原样透传 run_evaluation kwargs
- inspect-doc --tolerance-chars 7 → 泄漏键渲染
  "_tolerance_chars … 7  (ok)"（把 R979 的泄漏与 CLI 参数
  打通）
- _format_metric 直测：list 值走通用分支 "[1, 2]  (ok)"、
  bool True 渲染小写 "true  (ok)"
- forbidden tokens 第四百五十六批（open 1）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "s/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


# ---------- 无子命令 ----------

def test_no_command_system_exit_two_batch184(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2
    assert "the following arguments are required: command" in \
        capsys.readouterr().err


# ---------- parser / 负 max-chars 透传 ----------

def test_parser_kreuzberg_and_negative_max_chars_batch184(
        tmp_path):
    mf = _setup(tmp_path)
    out = tmp_path / "o.json"
    fake = {"per_doc": [], "devset": {}}
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake) as mk, \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf), "--output",
                   str(out), "--parser", "kreuzberg",
                   "--max-chars", "-800"])
    assert rc == 0
    k = mk.call_args.kwargs
    assert k["parser_name"] == "kreuzberg"
    assert k["max_chars"] == -800
    assert isinstance(k["max_chars"], int)


# ---------- 自定义容差泄漏 ----------

def test_inspect_doc_custom_tolerance_leak_batch184(tmp_path,
                                                    capsys):
    doc = {"source_type": "pdf",
           "elements": [{"type": "paragraph", "content": "A",
                         "source_locator": {"page": 1,
                                            "bbox": [0, 0, 1, 1]}}],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1"]}]}
    df = tmp_path / "d.json"
    df.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(df), "--tolerance-chars", "7"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "_tolerance_chars".ljust(36) + " 7  (ok)" in out


# ---------- _format_metric 直测 ----------

def test_format_metric_list_and_bool_batch184():
    assert _format_metric(
        "m", {"value": [1, 2], "reason": None}) == \
        "  " + "m".ljust(36) + " [1, 2]  (ok)"
    assert _format_metric(
        "m", {"value": True, "reason": None}) == \
        "  " + "m".ljust(36) + " true  (ok)"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch184():
    src = _src()
    assert "sub = p.add_subparsers(dest=\"command\", required=True)" in src
    assert "parser_name=args.parser," in src
    assert "max_chars=args.max_chars," in src
    assert "if isinstance(value, bool):" in src


# ---------- forbidden tokens 第四百五十六批 ----------

def test_source_no_eval_batch184():
    assert "eval(" not in _src()


def test_source_no_exec_batch184():
    assert "exec(" not in _src()


def test_source_no_compile_batch184():
    assert "compile(" not in _src()


def test_source_no_globals_batch184():
    assert "globals(" not in _src()


def test_source_no_locals_batch184():
    assert "locals(" not in _src()


def test_source_no_os_system_batch184():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch184():
    assert "subprocess" not in _src()


def test_source_no_popen_batch184():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch184():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch184():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch184():
    assert "socket" not in _src()


def test_source_no_requests_batch184():
    assert "requests" not in _src()


def test_source_no_urllib_batch184():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch184():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch184():
    assert "yield" not in _src()


def test_source_no_async_await_batch184():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch184():
    assert _src().count("open(") == 1
