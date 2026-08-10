"""evaluation/cli.py 第四十三轮 edges 测试（Round 425）。

补强 edges41 未触及的角度：
- _build_parser 边界第十五批（subparser 名称 / subparser 数量 / formatter / 各 action type / 各 action dest）
- argparse Namespace 第十五批（namespace != / namespace __dict__ / parsed args 属性类型）
- _format_metric 边界第十五批（None value / bool True / bool False / float 精度 / dict 多 item / list 不支持）
- _run_inspect_doc 边界第十五批（缺 document_id / 缺 elements / 缺 chunks / 缺 source_path / stdout labels 全）
- main 路由第十五批（inspect-doc 全部子命令 / validate-report 各失败模式 / run 各失败模式）
- module source forbidden tokens 第二十一批
- module source 字符串精确补强第十八批
- signatures 第十八批
- module 合理性第十八批
- 端到端集成第十八批
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 边界第十五批 ----------


def test_build_parser_run_subparser_prog_format_batch15():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = sub_actions[0].choices["run"]
    assert "run" in run_p.prog


def test_build_parser_validate_report_subparser_prog_batch15():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = sub_actions[0].choices["validate-report"]
    assert "validate-report" in val_p.prog


def test_build_parser_inspect_doc_subparser_prog_batch15():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = sub_actions[0].choices["inspect-doc"]
    assert "inspect-doc" in ins_p.prog


def test_build_parser_run_arg_count_batch15():
    """run 子命令应有 4 个 option args：--manifest, --output, --parser, --max-chars, --tolerance-chars。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = sub_actions[0].choices["run"]
    option_actions = [a for a in run_p._actions if a.option_strings]
    # 减去 --help
    user_options = [a for a in option_actions if "--help" not in a.option_strings]
    assert len(user_options) == 5


def test_build_parser_validate_report_arg_count_batch15():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = sub_actions[0].choices["validate-report"]
    positional = [a for a in val_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1


def test_build_parser_inspect_doc_arg_count_batch15():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = sub_actions[0].choices["inspect-doc"]
    positional = [a for a in ins_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1
    option_actions = [a for a in ins_p._actions if a.option_strings and "--help" not in a.option_strings]
    assert len(option_actions) == 1  # --tolerance-chars


def test_build_parser_choices_actions_count_3_batch15():
    """3 个子命令。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(sub_actions[0].choices) == 3


def test_build_parser_run_manifest_required_batch15():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.manifest == "m.json"


def test_build_parser_run_output_required_batch15():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.output == "o.json"


def test_build_parser_run_parser_choices_tuple_batch15():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


# ---------- argparse Namespace 第十五批 ----------


def test_namespace_equality_batch15():
    p = _build_parser()
    args1 = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    args2 = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args1 == args2


def test_namespace_inequality_batch15():
    p = _build_parser()
    args1 = p.parse_args(["run", "--manifest", "a.json", "--output", "o.json"])
    args2 = p.parse_args(["run", "--manifest", "b.json", "--output", "o.json"])
    assert args1 != args2


def test_namespace_dict_access_batch15():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    d = vars(args)
    assert d["manifest"] == "m.json"
    assert d["output"] == "o.json"


def test_namespace_command_attr_batch15():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"


def test_namespace_max_chars_type_int_batch15():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "999"])
    assert args.max_chars == 999
    assert isinstance(args.max_chars, int)


# ---------- _format_metric 边界第十五批 ----------


def test_format_metric_none_value_batch15():
    out = _format_metric("x", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_true_value_batch15():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_false_value_batch15():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out
    assert "ok" in out


def test_format_metric_float_precision_4_batch15():
    out = _format_metric("x", {"value": 0.123456789, "reason": None})
    assert "0.1235" in out


def test_format_metric_int_value_batch15():
    out = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_dict_multiple_items_batch15():
    out = _format_metric("x", {"value": {"a": 1, "b": 2, "c": 3}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out


def test_format_metric_dict_sorted_batch15():
    out = _format_metric("x", {"value": {"z": 1, "a": 2}, "reason": None})
    # sorted → a 在 z 前
    assert out.index("a=2") < out.index("z=1")


def test_format_metric_no_reason_int_batch15():
    out = _format_metric("x", {"value": 42})
    # reason None → 'ok'
    assert "ok" in out


# ---------- _run_inspect_doc 边界第十五批 ----------


def _write_valid_doc(tmp_path, **overrides):
    doc = {
        "document_id": "abc",
        "source_path": "/x.pdf",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [],
        "chunks": [],
    }
    doc.update(overrides)
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_missing_document_id_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc.pop("document_id")
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "?" in captured.out  # 缺 document_id → '?'


def test_run_inspect_doc_missing_source_path_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc.pop("source_path")
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_missing_elements_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc.pop("elements")
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_missing_chunks_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc.pop("chunks")
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "chunks=0" in captured.out


def test_run_inspect_doc_elements_none_batch15(tmp_path, capsys):
    # elements=None propagates through compute_automatic_metrics and raises
    # TypeError because document.get("elements", []) returns None (key exists).
    # _run_inspect_doc does not wrap compute_automatic_metrics in try/except,
    # so the exception propagates to the caller.
    import pytest as _pytest
    p = _write_valid_doc(tmp_path, elements=None)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with _pytest.raises(TypeError):
        _run_inspect_doc(args)


def test_run_inspect_doc_chunks_none_batch15(tmp_path, capsys):
    # chunks=None: _run_inspect_doc itself uses `doc.get("chunks") or []`,
    # so its local `chunks` is []. But `doc` still has chunks=None, and
    # compute_automatic_metrics reads document.get("chunks", []) → None.
    # _text_preservation then iterates None → TypeError, which propagates.
    import pytest as _pytest
    p = _write_valid_doc(tmp_path, elements=[], chunks=None)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with _pytest.raises(TypeError):
        _run_inspect_doc(args)


def test_run_inspect_doc_with_tolerance_99_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 99
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_stdout_contains_metrics_lines_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 至少 6 个 stdout 行（file/document_id/source/parser/counts/metrics + 各种 metric 行）
    assert len(captured.out.split("\n")) > 6


# ---------- main 路由第十五批 ----------


def test_main_run_manifest_path_not_exist_returns_2_batch15(capsys):
    rc = main(["run", "--manifest", "/nonexistent/x.json", "--output", "o.json"])
    assert rc == 2


def test_main_validate_report_path_not_exist_returns_2_batch15(capsys):
    rc = main(["validate-report", "/nonexistent/x.json"])
    assert rc == 2


def test_main_inspect_doc_path_not_exist_returns_2_batch15(capsys):
    rc = main(["inspect-doc", "/nonexistent/x.json"])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1_batch15(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_list_json_returns_1_batch15(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_int_json_returns_1_batch15(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_validate_report_invalid_schema_returns_1_batch15(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"wrong": "shape"}', encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_0_on_valid_batch15(tmp_path):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_returns_int_type_batch15():
    rc = main(["inspect-doc", "/nonexistent/x.json"])
    assert isinstance(rc, int)


# ---------- module source forbidden tokens 第二十一批 ----------


_FORBIDDEN_TOKENS_ROUND21 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND21)
def test_module_source_forbidden_tokens_round21_batch15(token):
    source = inspect.getsource(climod)
    assert token not in source


# ---------- module source 字符串精确补强第十八批 ----------


def test_module_source_module_docstring_present_batch15():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch15():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_argparse_batch15():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import argparse" in head


def test_module_source_imports_json_batch15():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_sys_batch15():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import sys" in head


def test_module_source_imports_pathlib_path_batch15():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_defines_build_parser_batch15():
    source = inspect.getsource(climod)
    assert "def _build_parser(" in source


def test_module_source_defines_main_batch15():
    source = inspect.getsource(climod)
    assert "def main(" in source


def test_module_source_defines_format_metric_batch15():
    source = inspect.getsource(climod)
    assert "def _format_metric(" in source


def test_module_source_defines_run_inspect_doc_batch15():
    source = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in source


def test_module_source_has_main_guard_batch15():
    source = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in source


def test_module_source_has_sys_exit_call_batch15():
    source = inspect.getsource(climod)
    assert "SystemExit" in source or "sys.exit" in source


def test_module_source_uses_load_manifest_batch15():
    source = inspect.getsource(climod)
    assert "load_manifest(" in source


def test_module_source_uses_validate_file_batch15():
    source = inspect.getsource(climod)
    assert "validate_file(" in source


def test_module_source_uses_run_evaluation_batch15():
    source = inspect.getsource(climod)
    assert "run_evaluation(" in source


def test_module_source_has_run_subcommand_string_batch15():
    source = inspect.getsource(climod)
    assert '"run"' in source or "'run'" in source


def test_module_source_has_validate_report_subcommand_string_batch15():
    source = inspect.getsource(climod)
    assert '"validate-report"' in source or "'validate-report'" in source


def test_module_source_has_inspect_doc_subcommand_string_batch15():
    source = inspect.getsource(climod)
    assert '"inspect-doc"' in source or "'inspect-doc'" in source


def test_module_source_has_subparsers_required_batch15():
    source = inspect.getsource(climod)
    assert "required=True" in source


def test_module_source_has_choices_tuple_batch15():
    source = inspect.getsource(climod)
    assert "fallback" in source
    assert "kreuzberg" in source


def test_module_source_no_subprocess_import_batch15():
    source = inspect.getsource(climod)
    assert "import subprocess" not in source


def test_module_source_uses_get_git_provenance_batch15():
    source = inspect.getsource(climod)
    assert "get_git_provenance" in source


# ---------- signatures 第十八批 ----------


def test_build_parser_no_args_batch15():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_main_optional_argv_batch15():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.default is None


def test_format_metric_two_args_batch15():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_run_inspect_doc_one_arg_batch15():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_main_return_int_batch15():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_build_parser_return_argument_parser_batch15():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_format_metric_return_str_batch15():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_run_inspect_doc_return_int_batch15():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# ---------- module 合理性第十八批 ----------


def test_module_dunder_file_exists_batch15():
    assert hasattr(climod, "__file__")
    assert climod.__file__ is not None


def test_module_dunder_file_cli_py_batch15():
    assert "evaluation" in climod.__file__
    assert climod.__file__.endswith("cli.py")


def test_module_name_evaluation_cli_batch15():
    assert climod.__name__ == "evaluation.cli"


def test_module_has_main_callable_batch15():
    assert callable(climod.main)


def test_module_has_build_parser_callable_batch15():
    assert callable(climod._build_parser)


def test_module_has_format_metric_callable_batch15():
    assert callable(climod._format_metric)


def test_module_has_run_inspect_doc_callable_batch15():
    assert callable(climod._run_inspect_doc)


def test_module_no_class_definitions_batch15():
    classes = [
        n for n, v in vars(climod).items()
        if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


# ---------- 端到端集成第十八批 ----------


def test_e2e_main_inspect_doc_full_flow_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert "document_id:" in captured.out
    assert "source:" in captured.out
    assert "parser:" in captured.out
    assert "counts:" in captured.out
    assert "metrics:" in captured.out


def test_e2e_main_inspect_doc_with_elements_and_chunks_batch15(tmp_path, capsys):
    doc = {
        "document_id": "abc",
        "source_path": "/x.pdf",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "Title"},
            {"type": "paragraph", "element_id": "p1", "content": "Body"},
        ],
        "chunks": [
            {"text": "Title Body", "source_element_ids": ["h1", "p1"]},
        ],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=2" in captured.out
    assert "chunks=1" in captured.out


def test_e2e_main_inspect_doc_idempotent_batch15(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    main(["inspect-doc", str(p)])
    out1 = capsys.readouterr().out
    main(["inspect-doc", str(p)])
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_e2e_main_validate_report_with_invalid_schema_batch15(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text('{"wrong": "shape"}', encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_validate_report_with_invalid_json_batch15(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_inspect_doc_with_empty_doc_batch15(tmp_path):
    doc = {"document_id": "x"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_subcommand_routing_run_batch15():
    rc = main(["run", "--manifest", "/nonexistent/x.json", "--output", "o.json"])
    assert rc == 2


def test_e2e_main_subcommand_routing_validate_report_batch15():
    rc = main(["validate-report", "/nonexistent/x.json"])
    assert rc == 2


def test_e2e_main_subcommand_routing_inspect_doc_batch15():
    rc = main(["inspect-doc", "/nonexistent/x.json"])
    assert rc == 2


def test_e2e_main_inspect_doc_with_high_tolerance_batch15(tmp_path):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "999"])
    assert rc == 0


def test_e2e_main_inspect_doc_returns_0_with_full_doc_batch15(tmp_path):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
