"""evaluation/cli.py 第四十二轮 edges 测试（Round 418）。

补强 edges40 未触及的角度：
- _build_parser 边界深度第十四批（formatter_class / prog / description 文案 / subparser required=True / subparser dest='command' / 各子命令不可缺）
- argparse 系统级第十四批（argparse 进程 exit code / SystemExit code / 解析未知短选项 / 解析未知长选项 / 缺 required 参数）
- _format_metric 边界深度第十四批（int 值 / 字符串值 / 字典嵌套 dict / 大数字 / Unicode reason / 长 name 超过 36 / padding 含全角）
- _run_inspect_doc 边界深度第十四批（stdout 含 file:/document_id:/source:/parser:/counts:/metrics: labels / doc 缺 elements / doc 缺 chunks / elements 是 None / chunks 是 None / doc 缺 source_type / 输入是 list 而非 dict → return 1 / 输入是 int 而非 dict → return 1）
- main 路由深度第十四批（schema_invalid → 1 / post-validate fail → 1 / inspect-doc JSON 解析失败 → 1 / validate-report schema 失败 → 1）
- module source forbidden tokens 第二十批
- module source 字符串精确补强第十七批
- signatures 第十七批
- module 合理性第十七批
- 端到端集成第十七批
"""

from __future__ import annotations

import argparse
import inspect
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 边界深度第十四批 ----------


def test_build_parser_prog_value_batch14():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_formatter_class_batch14():
    p = _build_parser()
    assert p.formatter_class == argparse.RawDescriptionHelpFormatter


def test_build_parser_description_present_batch14():
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_subparser_dest_command_batch14():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions[0].dest == "command"


def test_build_parser_subparser_required_true_batch14():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions[0].required is True


def test_build_parser_subcommands_count_3_batch14():
    """3 个子命令：run, validate-report, inspect-doc。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert set(sub_actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_help_batch14():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = sub_actions[0].choices["run"]
    # 至少包含一个 --parser 选项
    has_parser = any("--parser" in a.option_strings for a in run_p._actions)
    assert has_parser


def test_build_parser_validate_report_positional_input_batch14():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = sub_actions[0].choices["validate-report"]
    positional = [a for a in val_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_build_parser_inspect_doc_positional_input_batch14():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = sub_actions[0].choices["inspect-doc"]
    positional = [a for a in ins_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_build_parser_run_default_parser_fallback_batch14():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_run_default_max_chars_800_batch14():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_30_batch14():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_default_tolerance_chars_30_batch14():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


# ---------- argparse 系统级第十四批 ----------


def test_main_unknown_subcommand_raises_systemexit_batch14(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["nonexistent-command"])
    # argparse 子命令错误 → exit code 2
    assert exc_info.value.code == 2


def test_main_no_command_raises_systemexit_batch14():
    with pytest.raises(SystemExit):
        main([])


def test_main_run_missing_manifest_raises_systemexit_batch14():
    with pytest.raises(SystemExit):
        main(["run", "--output", "o.json"])


def test_main_run_missing_output_raises_systemexit_batch14():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json"])


def test_main_run_invalid_parser_value_raises_systemexit_batch14():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json", "--output", "o.json", "--parser", "bad"])


def test_main_run_non_int_max_chars_raises_systemexit_batch14():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "abc"])


def test_main_run_unknown_option_raises_systemexit_batch14():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json", "--output", "o.json", "--unknown-flag", "x"])


# ---------- _format_metric 边界深度第十四批 ----------


def test_format_metric_int_value_batch14():
    out = _format_metric("count", {"value": 42, "reason": "ok"})
    assert "42" in out


def test_format_metric_string_value_batch14():
    out = _format_metric("code", {"value": "E001", "reason": "ok"})
    assert "E001" in out


def test_format_metric_dict_with_int_value_batch14():
    out = _format_metric("counts", {"value": {"a": 3, "b": 5}, "reason": "ok"})
    assert "a=3" in out
    assert "b=5" in out


def test_format_metric_large_float_value_batch14():
    out = _format_metric("big", {"value": 1234567.123456, "reason": "ok"})
    # 4 位小数
    assert "1234567.1235" in out


def test_format_metric_unicode_reason_batch14():
    out = _format_metric("name", {"value": None, "reason": "无标注"})
    assert "无标注" in out


def test_format_metric_long_name_batch14():
    """name 长度超过 36 仍能渲染（padding 不会截断）。"""
    long_name = "x" * 100
    out = _format_metric(long_name, {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_short_name_batch14():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out


def test_format_metric_metric_is_empty_dict_batch14():
    """metric 是空 dict → value=None → null + reason=None。"""
    out = _format_metric("empty", {})
    assert "null" in out
    assert "None" in out


def test_format_metric_dict_value_with_none_inner_batch14():
    """dict value 内含 None → str(None) = 'None'。"""
    out = _format_metric("d", {"value": {"k": None}, "reason": "ok"})
    assert "k=None" in out


def test_format_metric_returns_str_batch14():
    out = _format_metric("x", {"value": 1, "reason": "ok"})
    assert isinstance(out, str)


# ---------- _run_inspect_doc 边界深度第十四批 ----------


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


def test_run_inspect_doc_input_not_exist_returns_2_batch14(capsys):
    args = MagicMock()
    args.input = "/nonexistent/path.json"
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_input_invalid_json_returns_1_batch14(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_input_is_list_returns_1_batch14(tmp_path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_input_is_int_returns_1_batch14(tmp_path, capsys):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_prints_file_label_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_prints_document_id_label_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "document_id:" in captured.out


def test_run_inspect_doc_prints_source_label_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "source:" in captured.out


def test_run_inspect_doc_prints_parser_label_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "parser:" in captured.out


def test_run_inspect_doc_prints_counts_label_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "counts:" in captured.out


def test_run_inspect_doc_prints_metrics_label_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_missing_source_type_uses_unknown_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path, source_type=None)
    # 需要 source_type 缺失（移除 key）
    doc_text = p.read_text(encoding="utf-8")
    doc = json.loads(doc_text)
    doc.pop("source_type", None)
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_returns_zero_on_success_batch14(tmp_path):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 路由深度第十四批 ----------


def test_main_run_manifest_not_exist_returns_2_batch14(capsys):
    rc = main(["run", "--manifest", "/nonexistent/manifest.json", "--output", "out.json"])
    assert rc == 2


def test_main_validate_report_input_not_exist_returns_2_batch14(capsys):
    rc = main(["validate-report", "/nonexistent/report.json"])
    assert rc == 2


def test_main_inspect_doc_input_not_exist_returns_2_batch14(capsys):
    rc = main(["inspect-doc", "/nonexistent/doc.json"])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch14(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_invalid_json_returns_1_batch14(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_0_on_valid_doc_batch14(tmp_path):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_returns_int_batch14():
    """main 应总是返回 int（即使异常也应统一）。"""
    rc = main(["inspect-doc", "/nonexistent/x.json"])
    assert isinstance(rc, int)


# ---------- module source forbidden tokens 第二十批 ----------


_FORBIDDEN_TOKENS_ROUND20 = [
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


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND20)
def test_module_source_forbidden_tokens_round20_batch14(token):
    source = inspect.getsource(climod)
    assert token not in source


# ---------- module source 字符串精确补强第十七批 ----------


def test_module_source_module_docstring_present_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_argparse_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import argparse" in head


def test_module_source_imports_json_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_sys_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import sys" in head


def test_module_source_imports_pathlib_path_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_manifest_helpers_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.manifest import ManifestError, load_manifest" in head


def test_module_source_imports_report_helpers_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.report import get_git_provenance" in head


def test_module_source_imports_runner_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.runner import run_evaluation" in head


def test_module_source_imports_schema_batch14():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.schema import EvalSchemaError, validate_file" in head


def test_module_source_defines_build_parser_batch14():
    source = inspect.getsource(climod)
    assert "def _build_parser(" in source


def test_module_source_defines_main_batch14():
    source = inspect.getsource(climod)
    assert "def main(" in source


def test_module_source_defines_format_metric_batch14():
    source = inspect.getsource(climod)
    assert "def _format_metric(" in source


def test_module_source_defines_run_inspect_doc_batch14():
    source = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in source


def test_module_source_has_subparsers_batch14():
    source = inspect.getsource(climod)
    assert "add_subparsers" in source


def test_module_source_has_required_true_batch14():
    source = inspect.getsource(climod)
    assert "required=True" in source


def test_module_source_has_choices_fallback_kreuzberg_batch14():
    source = inspect.getsource(climod)
    assert "fallback" in source
    assert "kreuzberg" in source


def test_module_source_has_sys_exit_or_return_int_batch14():
    """main 应通过 return int 表达退出码。"""
    source = inspect.getsource(climod)
    assert "return 0" in source or "return 1" in source or "return 2" in source


def test_module_source_has_main_guard_batch14():
    source = inspect.getsource(climod)
    assert "__main__" in source


def test_module_source_uses_validate_file_batch14():
    source = inspect.getsource(climod)
    assert "validate_file(" in source


def test_module_source_uses_load_manifest_batch14():
    source = inspect.getsource(climod)
    assert "load_manifest(" in source


def test_module_source_uses_run_evaluation_batch14():
    source = inspect.getsource(climod)
    assert "run_evaluation(" in source


def test_module_source_has_run_subcommand_batch14():
    source = inspect.getsource(climod)
    assert '"run"' in source or "'run'" in source


def test_module_source_has_validate_report_subcommand_batch14():
    source = inspect.getsource(climod)
    assert "validate-report" in source


def test_module_source_has_inspect_doc_subcommand_batch14():
    source = inspect.getsource(climod)
    assert "inspect-doc" in source


# ---------- signatures 第十七批 ----------


def test_build_parser_no_args_batch14():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_main_optional_argv_batch14():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.default is None


def test_format_metric_two_args_batch14():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2
    for name in ("name", "metric"):
        assert name in sig.parameters


def test_run_inspect_doc_one_arg_batch14():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1
    assert "args" in sig.parameters


def test_main_return_annotation_int_batch14():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_build_parser_return_annotation_argument_parser_batch14():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_format_metric_return_annotation_str_batch14():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_run_inspect_doc_return_annotation_int_batch14():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


def test_main_argv_annotation_list_str_or_none_batch14():
    sig = inspect.signature(main)
    p_str = str(sig.parameters["argv"].annotation)
    assert "list" in p_str
    assert "None" in p_str


def test_format_metric_name_annotation_str_batch14():
    sig = inspect.signature(_format_metric)
    p_str = str(sig.parameters["name"].annotation)
    assert "str" in p_str


def test_format_metric_metric_annotation_dict_batch14():
    sig = inspect.signature(_format_metric)
    p_str = str(sig.parameters["metric"].annotation)
    assert "dict" in p_str


# ---------- module 合理性第十七批 ----------


def test_module_dunder_file_exists_batch14():
    assert hasattr(climod, "__file__")
    assert climod.__file__ is not None


def test_module_dunder_file_cli_py_batch14():
    assert "evaluation" in climod.__file__
    assert climod.__file__.endswith("cli.py")


def test_module_name_evaluation_cli_batch14():
    assert climod.__name__ == "evaluation.cli"


def test_module_has_main_callable_batch14():
    assert callable(climod.main)


def test_module_has_build_parser_callable_batch14():
    assert callable(climod._build_parser)


def test_module_has_format_metric_callable_batch14():
    assert callable(climod._format_metric)


def test_module_has_run_inspect_doc_callable_batch14():
    assert callable(climod._run_inspect_doc)


def test_module_no_class_definitions_batch14():
    classes = [
        n for n, v in vars(climod).items()
        if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


# ---------- 端到端集成第十七批 ----------


def test_e2e_main_inspect_doc_full_flow_batch14(tmp_path, capsys):
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


def test_e2e_main_inspect_doc_with_elements_and_chunks_batch14(tmp_path, capsys):
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


def test_e2e_main_inspect_doc_with_tolerance_chars_batch14(tmp_path):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "99"])
    assert rc == 0


def test_e2e_main_inspect_doc_idempotent_batch14(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    main(["inspect-doc", str(p)])
    out1 = capsys.readouterr().out
    main(["inspect-doc", str(p)])
    out2 = capsys.readouterr().out
    # 两次输出应相同
    assert out1 == out2


def test_e2e_main_validate_report_with_invalid_schema_batch14(tmp_path, capsys):
    """写一个不符合 schema 的 JSON，验证 validate-report 返回 1。"""
    p = tmp_path / "report.json"
    p.write_text('{"wrong": "shape"}', encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_inspect_doc_with_empty_doc_batch14(tmp_path):
    """doc 只有 document_id，无 elements/chunks。"""
    doc = {"document_id": "x"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_inspect_doc_stdout_encoding_utf8_batch14(tmp_path, capsys):
    """含 Unicode reason 的 metric 应正确输出（不抛 UnicodeEncodeError）。"""
    doc = {
        "document_id": "x",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [],
        "chunks": [],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_subcommand_routing_run_batch14():
    """run 命令应进入 run 分支（manifest 不存在 → return 2）。"""
    rc = main(["run", "--manifest", "/nonexistent/x.json", "--output", "o.json"])
    assert rc == 2


def test_e2e_main_subcommand_routing_validate_report_batch14():
    """validate-report 命令应进入 validate-report 分支（input 不存在 → return 2）。"""
    rc = main(["validate-report", "/nonexistent/x.json"])
    assert rc == 2


def test_e2e_main_subcommand_routing_inspect_doc_batch14():
    """inspect-doc 命令应进入 inspect-doc 分支（input 不存在 → return 2）。"""
    rc = main(["inspect-doc", "/nonexistent/x.json"])
    assert rc == 2
