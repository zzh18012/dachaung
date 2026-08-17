"""evaluation/cli.py 第三百三十九轮 edges 测试（Round 895）。

补强 edges107 未触及的角度（第二百七十一批，probe 实证）。

新角度：
- --parser choices 限定 fallback/kreuzberg：非法值 SystemExit 2
- --parser kreuzberg 透传 run_evaluation kwargs
- validate-report 成功行完整文本锁定
- inspect-doc 文档头 5 行（缺字段全 "?" 默认）
- inspect-doc --tolerance-chars 透传 chunk_boundary_prf
- _format_metric int / dict(sorted) / bool False 三分支精确渲染
- main([]) 空 argv → SystemExit 2（subparsers required）
- manifest 加载失败（Schema 不过）→ rc1 "清单加载失败"
- forbidden tokens 第三百六十五批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.annotation_metrics as am_mod
import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main


def _mk_manifest(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf, root


# ---------- --parser choices ----------

def test_parser_invalid_choice_system_exit_batch93(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", "x", "--output", "y",
              "--parser", "bad"])
    assert ei.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_parser_kreuzberg_passthrough_batch93(tmp_path):
    mf, _ = _mk_manifest(tmp_path)
    out = tmp_path / "r.json"
    with patch.object(cli_mod, "run_evaluation",
                      return_value={"per_doc": [], "devset": {}}
                      ) as fake_run, \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf), "--output", str(out),
                   "--parser", "kreuzberg"])
    assert rc == 0
    assert fake_run.call_args.kwargs["parser_name"] == "kreuzberg"


# ---------- validate-report 成功行 ----------

def test_validate_report_ok_line_batch93(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    with patch.object(cli_mod, "validate_file"):
        rc = main(["validate-report", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == \
        f"[OK] {f} 通过 evaluation-report Schema 校验"


# ---------- inspect-doc 头部默认 ----------

def test_inspect_header_defaults_batch93(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    lines = out.splitlines()
    assert lines[0] == f"file:        {f}"
    assert lines[1] == "document_id: ?"
    assert lines[2] == "source:      ?  type=pdf"
    assert lines[3] == "parser:      ? v?"
    assert lines[4] == "counts:      elements=0 chunks=0"


# ---------- tolerance 透传 ----------

def test_inspect_tolerance_passthrough_batch93(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8")
    captured = {}

    def fake_cbp(doc, ann, **kwargs):
        captured.update(kwargs)
        return {}

    with patch.object(am_mod, "chunk_boundary_prf",
                      side_effect=fake_cbp):
        rc = main(["inspect-doc", str(f), "--tolerance-chars", "11"])
    assert rc == 0
    assert captured == {"tolerance_chars": 11}


# ---------- _format_metric 分支 ----------

def test_format_metric_int_batch93():
    s = _format_metric("n", {"value": 5, "reason": None})
    # {name:36} 与 {value} 之间有一个分隔空格
    assert s == "  n" + " " * 36 + "5  (ok)"


def test_format_metric_dict_sorted_batch93():
    s = _format_metric("n", {"value": {"b": 2, "a": 1},
                             "reason": None})
    assert s == "  n" + " " * 36 + "a=1, b=2  (ok)"


def test_format_metric_bool_false_batch93():
    s = _format_metric("n", {"value": False, "reason": None})
    assert s == "  n" + " " * 36 + "false  (ok)"


def test_format_metric_float_reason_kept_batch93():
    s = _format_metric("n", {"value": 0.5, "reason": "why"})
    assert s.endswith("0.5000  (why)")


# ---------- 空 argv ----------

def test_main_empty_argv_system_exit_batch93(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2
    assert "command" in capsys.readouterr().err


# ---------- manifest 加载失败 rc1 ----------

def test_run_manifest_schema_fail_rc1_batch93(tmp_path, capsys):
    mf = tmp_path / "bad.json"
    mf.write_text(json.dumps({"manifest_version": "1.0"}),
                  encoding="utf-8")
    rc = main(["run", "--manifest", str(mf),
               "--output", str(tmp_path / "r.json")])
    e = capsys.readouterr().err
    assert rc == 1
    assert "[ERROR] 清单加载失败" in e


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch93():
    src = _src()
    assert 'choices=("fallback", "kreuzberg")' in src
    assert '通过 evaluation-report Schema 校验' in src
    assert "def _sort_key(name: str) -> tuple[int, str]:" in src
    assert "if isinstance(value, dict):" in src


# ---------- forbidden tokens 第三百六十五批 ----------

def test_source_no_eval_batch93():
    assert "eval(" not in _src()


def test_source_no_exec_batch93():
    assert "exec(" not in _src()


def test_source_no_compile_batch93():
    assert "compile(" not in _src()


def test_source_no_globals_batch93():
    assert "globals(" not in _src()


def test_source_no_locals_batch93():
    assert "locals(" not in _src()


def test_source_no_os_system_batch93():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch93():
    assert "subprocess" not in _src()


def test_source_no_popen_batch93():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch93():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch93():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch93():
    assert "socket" not in _src()


def test_source_no_requests_batch93():
    assert "requests" not in _src()


def test_source_no_urllib_batch93():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch93():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch93():
    assert "yield" not in _src()


def test_source_no_async_await_batch93():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch93():
    assert _src().count("open(") == 1
