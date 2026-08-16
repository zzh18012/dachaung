"""evaluation/cli.py 第一百零四轮 edges 测试（Round 734）。

补强 edges82-84 未触及的角度（第九十九批）。

新角度：
- _format_metric 补角：list 值走通用分支 "[1, 2]" / dict 按 key 排序
  "a=1, b=2" / int 42 不走浮点格式 / 0.0→"0.0000" / 1/3→"0.3333" /
  负浮点 "-0.5000" / bool + reason → reason 胜过 'ok'
- argparse：--parser kreuzberg 接受、bogus 拒绝 exit 2、
  --max-chars 非数字 exit 2、--help / run --help exit 0
- inspect-doc 现状记录：恒传 error=None → 带 error 键的文档 JSON
  仍报 pipeline_success true（error 键被忽略）；_tolerance_chars
  未被 pop，作为指标行混入输出（run 路径会 pop，inspect 路径不会）
- inspect-doc：BOM → rc1 "Unexpected UTF-8 BOM"；缺文件 → rc2 文档不存在
- validate-report happy path stdout 精确 / FileNotFoundError → rc2
- 源码补强（required=True / RawDescriptionHelpFormatter / prog）
- forbidden tokens 第二百零四批
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, main


# ---------- _format_metric 补角 ----------

def test_format_metric_list_value_generic_branch_batch54():
    assert _format_metric("n", {"value": [1, 2]}) == \
        "  n" + " " * 36 + "[1, 2]  (ok)"


def test_format_metric_dict_sorted_by_key_batch54():
    assert _format_metric("n", {"value": {"b": 2, "a": 1}}) == \
        "  n" + " " * 36 + "a=1, b=2  (ok)"


def test_format_metric_int_not_float_formatted_batch54():
    assert _format_metric("n", {"value": 42}) == \
        "  n" + " " * 36 + "42  (ok)"


def test_format_metric_float_variants_batch54():
    assert _format_metric("n", {"value": 0.0}).endswith("0.0000  (ok)")
    assert _format_metric("n", {"value": 1 / 3}).endswith("0.3333  (ok)")
    assert _format_metric("n", {"value": -0.5, "reason": None}).endswith(
        "-0.5000  (ok)")


def test_format_metric_bool_reason_wins_batch54():
    assert _format_metric("n", {"value": True, "reason": "r"}) == \
        "  n" + " " * 36 + "true  (r)"


# ---------- argparse 补角 ----------

def test_parser_accepts_kreuzberg_and_numeric_flags_batch54():
    a = _build_parser().parse_args(
        ["run", "--manifest", "m", "--output", "o",
         "--parser", "kreuzberg", "--max-chars", "77",
         "--tolerance-chars", "5"])
    assert (a.command, a.parser, a.max_chars, a.tolerance_chars) == \
        ("run", "kreuzberg", 77, 5)


def test_parser_rejects_bad_choice_and_bad_int_batch54():
    with pytest.raises(SystemExit) as e1:
        _build_parser().parse_args(
            ["run", "--manifest", "m", "--output", "o",
             "--parser", "bogus"])
    assert e1.value.code == 2
    with pytest.raises(SystemExit) as e2:
        _build_parser().parse_args(
            ["run", "--manifest", "m", "--output", "o",
             "--max-chars", "abc"])
    assert e2.value.code == 2


@pytest.mark.parametrize("argv,marker", [
    (["--help"], "评测 CLI"),
    (["run", "--help"], "--manifest"),  # 子命令帮助不含主描述
])
def test_help_exits_zero_batch54(argv, marker, capsys):
    with pytest.raises(SystemExit) as e:
        _build_parser().parse_args(argv)
    assert e.value.code == 0
    assert marker in capsys.readouterr().out


# ---------- inspect-doc 现状记录 ----------

def test_inspect_error_doc_still_success_batch54(tmp_path, capsys):
    # inspect-doc 恒传 error=None：error 键被忽略，pipeline_success true
    f = tmp_path / "err.json"
    f.write_text(json.dumps({
        "document_id": "e", "source_type": "pdf", "source_path": "e.pdf",
        "error": {"code": "open_error", "message": "boom"},
    }), encoding="utf-8")
    assert main(["inspect-doc", str(f)]) == 0
    out = capsys.readouterr().out
    assert "pipeline_failed" not in out
    first = next(l for l in out.splitlines() if l.startswith("  "))
    assert first.strip().startswith("pipeline_success")
    assert "true" in first


def test_inspect_tolerance_printed_as_metric_batch54(tmp_path, capsys):
    # run 路径会 pop _tolerance_chars，inspect 路径不会（现状记录）
    f = tmp_path / "ok.json"
    f.write_text(json.dumps({
        "document_id": "o", "source_type": "docx", "source_path": "o.docx",
        "elements": [{"type": "paragraph", "content": "hi"}],
        "chunks": [{"text": "hi", "source_element_ids": ["x"]}],
    }), encoding="utf-8")
    assert main(["inspect-doc", str(f), "--tolerance-chars", "7"]) == 0
    out = capsys.readouterr().out
    tol_lines = [l for l in out.splitlines()
                 if l.strip().startswith("_tolerance_chars")]
    assert len(tol_lines) == 1
    assert tol_lines[0].strip().endswith("7  (ok)")


def test_inspect_bom_json_rc1_batch54(tmp_path, capsys):
    f = tmp_path / "bom.json"
    f.write_bytes(b'\xef\xbb\xbf{"document_id": "b"}')
    assert main(["inspect-doc", str(f)]) == 1
    assert "Unexpected UTF-8 BOM" in capsys.readouterr().err


def test_inspect_missing_file_rc2_batch54(tmp_path, capsys):
    assert main(["inspect-doc", str(tmp_path / "ghost.json")]) == 2
    assert capsys.readouterr().err.startswith("[ERROR] 文档不存在:")


# ---------- validate-report ----------

def test_validate_report_ok_stdout_batch54(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli_mod, "validate_file", lambda *a, **k: None)
    f = tmp_path / "rep.json"
    f.write_text("{}", encoding="utf-8")
    assert main(["validate-report", str(f)]) == 0
    assert capsys.readouterr().out.strip() == \
        f"[OK] {f} 通过 evaluation-report Schema 校验"


def test_validate_report_filenotfound_rc2_batch54(monkeypatch, tmp_path,
                                                   capsys):
    def raise_fnf(*a, **k):
        raise FileNotFoundError("schema gone")
    monkeypatch.setattr(cli_mod, "validate_file", raise_fnf)
    f = tmp_path / "rep.json"
    f.write_text("{}", encoding="utf-8")
    assert main(["validate-report", str(f)]) == 2
    assert "schema gone" in capsys.readouterr().err


# ---------- 源码补强 ----------

def test_source_parser_config_batch54():
    import inspect
    src = inspect.getsource(cli_mod)
    assert "required=True" in src
    assert "RawDescriptionHelpFormatter" in src
    assert 'prog="evaluation.cli"' in src
    assert 'choices=("fallback", "kreuzberg")' in src


# ---------- forbidden tokens 第二百零四批 ----------

def _src() -> str:
    import inspect
    return inspect.getsource(cli_mod)


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
    assert _src().count("open(") == 1  # input_path.open
