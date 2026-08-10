"""evaluation/cli.py 第三十一轮 edges 测试（Round 343）。

重点补强 edges29 未触及的角度：
- argparse namespace 行为深度（parse_args 返回 Namespace / dest / type 转换）
- main 行为深度第三批（更多错误码组合 / 输出验证）
- _format_metric 行为深度第三批（更多 value 类型 / reason 组合）
- _run_inspect_doc 行为深度第三批（更多边界）
- module source forbidden tokens 第五批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import argparse
import inspect
import json
import types
from pathlib import Path

import pytest

from evaluation import cli as cli_mod
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- argparse namespace 行为深度 ----------


def test_build_parser_run_subcommand_parses_to_namespace():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "o.json",
    ])
    assert isinstance(ns, argparse.Namespace)


def test_build_parser_namespace_command_field_is_run():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.command == "run"


def test_build_parser_namespace_command_field_is_validate_report():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "r.json"])
    assert ns.command == "validate-report"


def test_build_parser_namespace_command_field_is_inspect_doc():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "d.json"])
    assert ns.command == "inspect-doc"


def test_build_parser_namespace_manifest_field_is_str():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.manifest == "m.json"


def test_build_parser_namespace_output_field_is_str():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.output == "o.json"


def test_build_parser_namespace_parser_default_fallback():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.parser == "fallback"


def test_build_parser_namespace_max_chars_default_800():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.max_chars == 800


def test_build_parser_namespace_tolerance_chars_default_30():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_namespace_max_chars_converted_to_int():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "1000",
    ])
    assert ns.max_chars == 1000
    assert isinstance(ns.max_chars, int)


def test_build_parser_namespace_tolerance_chars_converted_to_int():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json", "--tolerance-chars", "50",
    ])
    assert ns.tolerance_chars == 50
    assert isinstance(ns.tolerance_chars, int)


def test_build_parser_namespace_validate_report_input_field():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_build_parser_namespace_inspect_doc_input_field():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_build_parser_namespace_inspect_doc_tolerance_default_30():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_namespace_inspect_doc_tolerance_custom():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "15"])
    assert ns.tolerance_chars == 15


def test_build_parser_run_with_kreuzberg_choice():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json", "--parser", "kreuzberg",
    ])
    assert ns.parser == "kreuzberg"


def test_build_parser_unknown_subcommand_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["unknown"])


def test_build_parser_no_subcommand_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_run_missing_required_manifest_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "o.json"])


def test_build_parser_run_missing_required_output_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json"])


def test_build_parser_run_invalid_parser_choice_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m.json", "--output", "o.json", "--parser", "invalid",
        ])


def test_build_parser_run_non_int_max_chars_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "x",
        ])


def test_build_parser_validate_report_missing_input_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_inspect_doc_missing_input_raises_systemexit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


# ---------- main 行为深度第三批 ----------


def _write_manifest(tmp_path, status="incomplete", docs=None):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": status,
        "documents": docs or [],
        "expected_failures": [],
    }), encoding="utf-8")
    return p


def test_main_run_returns_0_for_incomplete_status(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0


def test_main_run_returns_0_for_complete_status(tmp_path, capsys):
    m = _write_manifest(tmp_path, status="complete")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0


def test_main_run_writes_output_file(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    assert out.is_file()


def test_main_run_output_is_valid_json(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_main_run_output_has_report_version(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "report_version" in data


def test_main_run_with_max_chars_arg(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    rc = main([
        "run", "--manifest", str(m), "--output", str(out), "--max-chars", "500",
    ])
    assert rc == 0


def test_main_run_with_tolerance_chars_arg(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    rc = main([
        "run", "--manifest", str(m), "--output", str(out), "--tolerance-chars", "20",
    ])
    assert rc == 0


def test_main_run_manifest_dir_not_exists_returns_2(tmp_path, capsys):
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(tmp_path / "no.json"), "--output", str(out)])
    assert rc == 2


def test_main_run_invalid_manifest_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(bad), "--output", str(out)])
    assert rc == 1


def test_main_validate_report_invalid_top_level_dict_returns_1(tmp_path, capsys):
    """非 schema 兼容 dict → 1。"""
    bad = tmp_path / "r.json"
    bad.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_main_validate_report_returns_2_for_missing_file(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "nonexistent.json")])
    assert rc == 2


def test_main_validate_report_returns_1_for_invalid_json(tmp_path, capsys):
    bad = tmp_path / "r.json"
    bad.write_text("not json at all", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_main_validate_report_round_trip_after_run(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    rc = main(["validate-report", str(out)])
    assert rc == 0


def test_main_inspect_doc_returns_2_for_missing_file(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2


def test_main_inspect_doc_returns_1_for_invalid_json(tmp_path, capsys):
    bad = tmp_path / "d.json"
    bad.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_returns_1_for_top_level_array(tmp_path, capsys):
    bad = tmp_path / "d.json"
    bad.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_returns_1_for_top_level_int(tmp_path, capsys):
    bad = tmp_path / "d.json"
    bad.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_returns_0_for_empty_dict(tmp_path, capsys):
    """空 dict 也能跑（defaults everywhere）。"""
    d = tmp_path / "d.json"
    d.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 0


def test_main_inspect_doc_with_unicode_doc(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "document_id": "文档1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "文档1" in captured.out


def test_main_inspect_doc_with_chunks_section(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "document_id": "x",
        "source_type": "pdf",
        "elements": [],
        "chunks": [{"text": "abc", "source_element_ids": []}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "chunks=1" in captured.out


def test_main_inspect_doc_with_metrics_section(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "document_id": "x",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_main_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(d), "--tolerance-chars", "100"])
    assert rc == 0


def test_main_returns_int_type(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert isinstance(rc, int)


# ---------- _format_metric 行为深度第三批 ----------


def test_format_metric_with_none_value_uses_reason():
    out = _format_metric("m", {"value": None, "reason": "no_data"})
    assert "no_data" in out


def test_format_metric_with_none_value_no_reason():
    out = _format_metric("m", {"value": None, "reason": None})
    assert "None" in out or "null" in out


def test_format_metric_with_bool_true_lowercase():
    out = _format_metric("m", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_with_bool_false_lowercase():
    out = _format_metric("m", {"value": False, "reason": None})
    assert "false" in out
    assert "False" not in out


def test_format_metric_with_int_value():
    out = _format_metric("count", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_with_negative_int():
    out = _format_metric("count", {"value": -10, "reason": None})
    assert "-10" in out


def test_format_metric_with_zero_int():
    out = _format_metric("count", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_with_float_4_decimals():
    out = _format_metric("ratio", {"value": 0.123456789, "reason": None})
    assert "0.1235" in out


def test_format_metric_with_dict_value():
    out = _format_metric("counts", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_with_empty_dict():
    out = _format_metric("counts", {"value": {}, "reason": None})
    assert "counts" in out


def test_format_metric_with_unicode_reason():
    out = _format_metric("m", {"value": None, "reason": "无元素"})
    assert "无元素" in out


def test_format_metric_with_long_reason():
    reason = "a" * 100
    out = _format_metric("m", {"value": None, "reason": reason})
    assert reason in out


def test_format_metric_returns_str():
    out = _format_metric("m", {"value": 1, "reason": None})
    assert isinstance(out, str)


def test_format_metric_with_huge_int():
    out = _format_metric("count", {"value": 10**18, "reason": None})
    assert "1000000000000000000" in out


def test_format_metric_with_tiny_float():
    out = _format_metric("ratio", {"value": 0.0001, "reason": None})
    assert "0.0001" in out


# ---------- _run_inspect_doc 行为深度第三批 ----------


def test_run_inspect_doc_with_pdf_doc(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "document_id": "x",
        "source_type": "pdf",
        "source_path": "x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "page": 1,
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "content": "hello",
                "source_locator": {"type": "pdf", "page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]},
            },
        ],
        "chunks": [],
    }), encoding="utf-8")
    rc = _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    assert rc == 0
    captured = capsys.readouterr()
    assert "x.pdf" in captured.out
    assert "fallback" in captured.out


def test_run_inspect_doc_with_docx_doc(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "document_id": "y",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    assert rc == 0
    captured = capsys.readouterr()
    assert "docx" in captured.out


def test_run_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    rc = _run_inspect_doc(argparse.Namespace(input=str(tmp_path / "no.json"), tolerance_chars=30))
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text("not json", encoding="utf-8")
    rc = _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    assert rc == 1


def test_run_inspect_doc_top_level_array_returns_1(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text("[]", encoding="utf-8")
    rc = _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    assert rc == 1


def test_run_inspect_doc_top_level_int_returns_1(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text("42", encoding="utf-8")
    rc = _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    assert rc == 1


def test_run_inspect_doc_prints_file_path(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_prints_document_id(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "document_id": "abc123",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "document_id:" in captured.out
    assert "abc123" in captured.out


def test_run_inspect_doc_prints_source_path(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "source_path": "x.pdf",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "source:" in captured.out
    assert "x.pdf" in captured.out


def test_run_inspect_doc_prints_parser_name(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "parser_name": "fallback",
        "parser_version": "1.0",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "parser:" in captured.out
    assert "fallback" in captured.out


def test_run_inspect_doc_prints_counts(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({
        "elements": [{"type": "paragraph"}],
        "chunks": [{"text": "x"}],
        "source_type": "pdf",
    }), encoding="utf-8")
    _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_run_inspect_doc_prints_metrics_label(tmp_path, capsys):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    _run_inspect_doc(argparse.Namespace(input=str(d), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


# ---------- module source forbidden tokens 第五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "asdl", "asyncio",
        "audioop", "base64", "binascii", "binhex", "calendar",
        "concurrent", "contextlib", "copyreg", "crypt",
        "curses", "datetime", "dl", "docxml",
        "dummy_threading", "email", "encodings", "ensurepip",
        "enum", "errno", "fileinput", "fnmatch",
        "formatter", "ftplib", "functools", "genericpath",
        "getopt", "getpass", "gettext", "glob",
        "gopherlib", "heapq", "html", "http",
        "imaplib", "ihooks", "imghdr", "importlib",
        "inspect", "ipaddress", "itertools", "keyword",
        "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "markupbase", "md5",
        "mhlib", "mimetypes", "mimify", "mmap",
        "msilib", "multifile", "multiprocessing", "mutex",
        "netrc", "nis", "nntplib", "numbers",
        "opcode", "operator", "optparse", "os2emxpath",
        "parser", "pdb", "pickle", "pickletools",
        "pipes", "pkgutil", "platform", "plistlib",
        "poplib", "posixfile", "posixpath", "profile",
        "pstats", "pty", "pyclbr", "py_compile",
        "pydoc", "queue", "quopri", "random",
        "readline", "reprlib", "rexec", "rfc822",
        "rlcompleter", "robotparser", "runpy", "sched",
        "secrets", "select", "sets", "sgmlop",
        "sgmllib", "sha", "shelve", "shlex",
        "shutil", "signal", "site", "smtplib",
        "smtpd", "sndhdr", "socket", "socketserver",
        "spawn", "spwd", "sqlite3", "ssl",
        "stat", "stringprep", "struct", "subprocess",
        "sunau", "sunaudio", "symtable", "sysconfig",
        "tabnanny", "tarfile", "telnetlib", "tempfile",
        "termios", "threading", "time", "timeit",
        "tomllib", "token", "tokenize", "trace",
        "traceback", "tracemalloc", "tty", "turtle",
        "types", "unicodedata", "unittest", "urllib",
        "urllib2", "urlparse", "user", "userdict",
        "userlist", "usersite", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser",
        "whichdb", "wsgiref", "xdrlib", "xml",
        "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib", "zoneinfo", "math",
    ],
)
def test_module_source_forbidden_tokens_fifth_batch(token):
    """这些 stdlib 模块不应出现在 cli.py。"""
    src = inspect.getsource(cli_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_imports_argparse():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_module_source_imports_json():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_module_source_imports_sys():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_module_source_imports_path():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_module_source_has_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__ == "__main__":' in src


def test_module_source_main_block_uses_systemexit():
    src = inspect.getsource(cli_mod)
    assert "raise SystemExit(main())" in src


def test_module_source_no_yield():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(cli_mod)
    assert "async " not in src


def test_module_source_no_global():
    src = inspect.getsource(cli_mod)
    assert "global " not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(cli_mod)
    body_lines = [l for l in src.splitlines() if not l.strip().startswith(("#", '"', "'"))]
    body = "\n".join(body_lines)
    assert "\nclass " not in body


def test_module_source_no_decorators():
    src = inspect.getsource(cli_mod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_has_4_module_level_functions():
    src = inspect.getsource(cli_mod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 4


def test_module_source_has_inner_function_in_run_inspect_doc():
    """_run_inspect_doc 内嵌 _sort_key。"""
    src = inspect.getsource(cli_mod)
    inner_count = sum(1 for line in src.splitlines() if line.startswith("    def "))
    assert inner_count == 1


# ---------- signatures 精确补强 ----------


def test_main_signature_return_int_or_str():
    sig = inspect.signature(main)
    a = sig.return_annotation
    assert a is int or a == "int"


def test_main_signature_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_signature_argv_kind_positional_or_keyword():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_build_parser_signature_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_build_parser_return_annotation_argparse_argument_parser():
    sig = inspect.signature(_build_parser)
    a = sig.return_annotation
    assert "ArgumentParser" in str(a)


def test_format_metric_signature_2_params():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_format_metric_param_names():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_param_kinds():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_format_metric_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_format_metric_return_str():
    sig = inspect.signature(_format_metric)
    a = sig.return_annotation
    assert a is str or a == "str"


def test_run_inspect_doc_signature_1_param():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_run_inspect_doc_param_name_args():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_return_int():
    sig = inspect.signature(_run_inspect_doc)
    a = sig.return_annotation
    assert a is int or a == "int"


def test_no_varargs_varkw_in_functions():
    for fn in [main, _build_parser, _format_metric, _run_inspect_doc]:
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(cli_mod, types.ModuleType)


def test_module_namespace_name():
    assert cli_mod.__name__ == "evaluation.cli"


def test_module_has_no_all_attribute():
    assert not hasattr(cli_mod, "__all__")


def test_module_has_4_functions():
    functions = [
        v for v in vars(cli_mod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == cli_mod.__name__
    ]
    assert len(functions) == 4


def test_module_has_3_private_functions():
    private = [
        v for v in vars(cli_mod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == cli_mod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 3


def test_module_has_1_public_function():
    public = [
        v for v in vars(cli_mod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == cli_mod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(public) == 1
    assert public[0].__name__ == "main"


def test_module_no_class():
    classes = [
        v for v in vars(cli_mod).values()
        if isinstance(v, type) and v.__module__ == cli_mod.__name__
    ]
    assert len(classes) == 0


def test_module_callable_main():
    assert callable(cli_mod.main)


def test_module_callable_build_parser():
    assert callable(cli_mod._build_parser)


def test_module_callable_format_metric():
    assert callable(cli_mod._format_metric)


def test_module_callable_run_inspect_doc():
    assert callable(cli_mod._run_inspect_doc)


# ---------- 端到端集成补强 ----------


def test_e2e_run_with_minimal_manifest_writes_output(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
    assert out.is_file()


def test_e2e_run_creates_subdir(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "sub" / "deep" / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
    assert out.is_file()


def test_e2e_run_stdout_includes_documents_count(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert "documents=0" in captured.out


def test_e2e_run_stdout_includes_devset_status(tmp_path, capsys):
    m = _write_manifest(tmp_path, status="incomplete")
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert "devset_status=incomplete" in captured.out


def test_e2e_run_stdout_includes_git_commit(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert "git_commit" in captured.out


def test_e2e_run_stdout_includes_ok_marker(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_e2e_validate_report_round_trip(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    rc = main(["validate-report", str(out)])
    assert rc == 0


def test_e2e_inspect_doc_round_trip_with_run_output(tmp_path, capsys):
    """先跑 run 生成 evaluation-report，不能直接 inspect-doc（schema 不同）。"""
    # 这里只能用普通 document.json 测 inspect-doc
    d = tmp_path / "doc.json"
    d.write_text(json.dumps({
        "document_id": "x",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 0


def test_e2e_unknown_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["unknown"])
    assert ei.value.code == 2


def test_e2e_no_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


def test_e2e_run_with_invalid_parser_choice_exits_2(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    with pytest.raises(SystemExit) as ei:
        main([
            "run", "--manifest", str(m), "--output", str(out),
            "--parser", "invalid_parser",
        ])
    assert ei.value.code == 2


def test_e2e_run_with_non_int_max_chars_exits_2(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    with pytest.raises(SystemExit) as ei:
        main([
            "run", "--manifest", str(m), "--output", str(out),
            "--max-chars", "abc",
        ])
    assert ei.value.code == 2


def test_e2e_inspect_doc_returns_int_type(tmp_path):
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert isinstance(rc, int)


def test_e2e_run_returns_int_type(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert isinstance(rc, int)


def test_e2e_validate_report_returns_int_type(tmp_path, capsys):
    m = _write_manifest(tmp_path)
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    rc = main(["validate-report", str(out)])
    assert isinstance(rc, int)


def test_e2e_run_with_unicode_in_path(tmp_path, capsys):
    """路径含 Unicode 也能工作。"""
    sub = tmp_path / "测试"
    sub.mkdir()
    m = sub / "manifest.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
