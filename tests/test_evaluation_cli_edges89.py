"""evaluation/cli.py 第一百零八轮 edges 测试（Round 762）。

补强 edges85-88 未触及的角度（第一百二十六批）。

新角度：
- run 三参数透传：--parser kreuzberg / --max-chars 123 /
  --tolerance-chars 55 逐字进 run_evaluation kwargs
- run 空评测汇总行：documents=0（成功 0，失败 0）与
  devset_status=None file_count=None ...（devset 缺键时 .get 全 None）
- inspect-doc 未守卫输入：elements None → TypeError(len)、
  chunks None → TypeError(iterable) —— 自身 header 的 or [] 防护
  只救了显示层、救不了 compute_automatic_metrics 的原样直传；
  双空列表则 rc 0 且 counts elements=0 chunks=0
- inspect-doc 顶层 [] → rc 1 "[ERROR] JSON 顶层不是对象"
- _format_metric：字符串值原样（1 字符名 → 35 pad + 1 分隔）、
  int 0 → "0  (ok)"、负 float -0.5 → "-0.5000  (ok)"
- main() 无 argv → 读 sys.argv（monkeypatch sys.argv）
- validate-report 传目录 → rc 2 "报告不存在"
- argparse：未知 flag → SystemExit 2；无子命令 → SystemExit 2 +
  "required"（subparsers required）
- forbidden tokens 第二百三十二批
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main

ROOT = Path(__file__).resolve().parents[1]


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


def _manifest(tmp):
    mf = tmp / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    return mf


@pytest.fixture
def tmp():
    return Path(tempfile.mkdtemp())


# ---------- run 参数透传 ----------

def test_run_kwargs_passthrough_batch54(tmp, monkeypatch):
    cap = {}
    monkeypatch.setattr(cli_mod, "run_evaluation",
                        lambda man, out, **k: (cap.update(k),
                                               {"per_doc": [],
                                                "devset": {}})[1])
    monkeypatch.setattr(cli_mod, "validate_file", lambda p, s: None)
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda r: {"git_commit": "c" * 40,
                                   "git_dirty": True})
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest", str(_manifest(tmp)),
                   "--output", str(tmp / "r.json"), "--parser", "kreuzberg",
                   "--max-chars", "123", "--tolerance-chars", "55"])
    assert rc == 0
    assert cap == {"parser_name": "kreuzberg", "max_chars": 123,
                   "tolerance_chars": 55}


def test_run_empty_summary_lines_batch54(tmp, monkeypatch):
    monkeypatch.setattr(cli_mod, "run_evaluation",
                        lambda man, out, **k: {"per_doc": [], "devset": {}})
    monkeypatch.setattr(cli_mod, "validate_file", lambda p, s: None)
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": False})
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest", str(_manifest(tmp)),
                   "--output", str(tmp / "r.json")])
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert "      documents=0（成功 0，失败 0）" in lines
    assert ("      devset_status=None file_count=None groups=None "
            "pdf=None docx=None") in lines


# ---------- inspect-doc 未守卫输入 ----------

def _write_doc(tmp, doc):
    f = tmp / "d.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


def test_inspect_elements_none_crashes_batch54(tmp):
    f = _write_doc(tmp, {"document_id": "d", "source_type": "pdf",
                         "elements": None})
    with pytest.raises(TypeError):
        main(["inspect-doc", str(f)])


def test_inspect_chunks_none_crashes_batch54(tmp):
    f = _write_doc(tmp, {"document_id": "d", "source_type": "pdf",
                         "elements": [], "chunks": None})
    with pytest.raises(TypeError):
        main(["inspect-doc", str(f)])


def test_inspect_both_empty_ok_batch54(tmp):
    f = _write_doc(tmp, {"document_id": "d", "source_type": "pdf",
                         "elements": [], "chunks": []})
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    assert rc == 0
    assert "counts:      elements=0 chunks=0" in out.getvalue().splitlines()


def test_inspect_top_level_list_rc1_batch54(tmp):
    f = tmp / "arr.json"
    f.write_text("[]", encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert err.getvalue().strip() == "[ERROR] JSON 顶层不是对象"


# ---------- _format_metric ----------

def test_format_metric_string_value_batch54():
    assert _format_metric("n", {"value": "xyz", "reason": None}) == \
        "  n" + " " * 36 + "xyz  (ok)"


def test_format_metric_int_zero_batch54():
    assert _format_metric("n", {"value": 0, "reason": None}) == \
        "  n" + " " * 36 + "0  (ok)"


def test_format_metric_negative_float_batch54():
    assert _format_metric("n", {"value": -0.5, "reason": None}) == \
        "  n" + " " * 36 + "-0.5000  (ok)"


# ---------- main() 读 sys.argv ----------

def test_main_reads_sys_argv_batch54(tmp, monkeypatch):
    f = _write_doc(tmp, {"document_id": "d", "source_type": "pdf",
                         "elements": [], "chunks": []})
    monkeypatch.setattr("sys.argv", ["prog", "inspect-doc", str(f)])
    out, err, co, ce = _cap()
    with co, ce:
        rc = main()
    assert rc == 0
    assert "document_id: d" in out.getvalue()


# ---------- validate-report 目录 ----------

def test_validate_report_directory_rc2_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(tmp)])
    assert rc == 2
    assert err.getvalue().startswith("[ERROR] 报告不存在: ")


# ---------- argparse 拒绝 ----------

def test_unknown_flag_systemexit_two_batch54():
    buf = io.StringIO()
    with pytest.raises(SystemExit) as ei, contextlib.redirect_stderr(buf):
        main(["run", "--manifest", "x", "--output", "o", "--bogus"])
    assert ei.value.code == 2


def test_no_subcommand_systemexit_two_batch54():
    buf = io.StringIO()
    with pytest.raises(SystemExit) as ei, contextlib.redirect_stderr(buf):
        main([])
    assert ei.value.code == 2
    assert "required" in buf.getvalue()


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_or_guard_only_in_header_batch54():
    src = _src()
    # 显示层有 or [] 防护；metrics 层没有
    assert src.count('doc.get("elements") or []') == 1
    assert 'doc.get("chunks") or []' in src
    assert "document=doc," in src


# ---------- forbidden tokens 第二百三十二批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
