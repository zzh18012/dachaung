"""evaluation/cli.py 第三百六十七轮 edges 测试（Round 923）。

补强 edges111 未触及的角度（第二百九十九批，probe 实证）。

新角度：
- run 三 kwargs 全透传：--parser kreuzberg + --max-chars 555 +
  --tolerance-chars -3（负容差 argparse 照收 type=int）
- --max-chars abc → argparse SystemExit 2
- validate-report 对合法 JSON 但形状不符 → rc 1 "[FAIL]"
- inspect-doc 顶层 list / string → rc 1
  "JSON 顶层不是对象"（双形态）
- --output 父路径是文件 → run_evaluation 内 mkdir 抛
  FileExistsError 直接冒出（cli 无兜底）
- forbidden tokens 第三百九十三批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


def _mf(tmp_path, name="m.json"):
    f = tmp_path / name
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    return f


# ---------- run kwargs 全透传 ----------

def test_run_all_kwargs_passthrough_batch121(tmp_path, capsys):
    cap = {}

    def fake_re(m, o, **kw):
        cap.update(kw)
        return {"per_doc": [], "devset": {}}

    with patch.object(cli_mod, "run_evaluation",
                      side_effect=fake_re), \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(_mf(tmp_path)),
                   "--output", str(tmp_path / "o.json"),
                   "--parser", "kreuzberg", "--max-chars", "555",
                   "--tolerance-chars", "-3"])
    assert rc == 0
    assert cap == {"parser_name": "kreuzberg", "max_chars": 555,
                   "tolerance_chars": -3}


def test_max_chars_non_int_system_exit_batch121(tmp_path):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", str(_mf(tmp_path)),
              "--output", str(tmp_path / "o.json"),
              "--max-chars", "abc"])
    assert ei.value.code == 2


# ---------- validate-report 形状不符 ----------

def test_validate_report_wrong_shape_fail_batch121(tmp_path,
                                                   capsys):
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"hello": 1}), encoding="utf-8")
    rc = main(["validate-report", str(f)])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[FAIL] ")
    assert "报告校验失败：" in err


# ---------- inspect 顶层非对象 ----------

@pytest.mark.parametrize("content", ["[1, 2]", '"hello"', "42"])
def test_inspect_non_object_top_batch121(tmp_path, capsys, content):
    f = tmp_path / "l.json"
    f.write_text(content, encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert capsys.readouterr().err.strip() == \
        "[ERROR] JSON 顶层不是对象"


# ---------- output 父路径是文件 ----------

def test_output_parent_is_file_crash_batch121(tmp_path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        main(["run", "--manifest", str(_mf(tmp_path)),
              "--output", str(blocker / "o.json")])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch121():
    src = _src()
    assert 'parser_name=args.parser,' in src
    assert 'max_chars=args.max_chars,' in src
    assert 'tolerance_chars=args.tolerance_chars,' in src
    assert 'print(f"[ERROR] 文档不存在: {input_path}", file=sys.stderr)' in src


# ---------- forbidden tokens 第三百九十三批 ----------

def test_source_no_eval_batch121():
    assert "eval(" not in _src()


def test_source_no_exec_batch121():
    assert "exec(" not in _src()


def test_source_no_compile_batch121():
    assert "compile(" not in _src()


def test_source_no_globals_batch121():
    assert "globals(" not in _src()


def test_source_no_locals_batch121():
    assert "locals(" not in _src()


def test_source_no_os_system_batch121():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch121():
    assert "subprocess" not in _src()


def test_source_no_popen_batch121():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch121():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch121():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch121():
    assert "socket" not in _src()


def test_source_no_requests_batch121():
    assert "requests" not in _src()


def test_source_no_urllib_batch121():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch121():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch121():
    assert "yield" not in _src()


def test_source_no_async_await_batch121():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch121():
    assert _src().count("open(") == 1
