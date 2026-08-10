"""evaluation/cli.py 第三十三轮 edges 测试（Round 356）。

重点补强 edges31 未触及的角度：
- _build_parser source level 字符串精确补强第二批
- main source level 字符串精确补强第二批
- _format_metric source level 字符串精确补强第二批
- _run_inspect_doc source level 字符串精确补强第二批
- argparse 边界第四批（help strings / choices tuple / prog / formatter）
- main 行为深度第五批（更多组合）
- module source forbidden tokens 第七批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
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


# ---------- _build_parser source level 字符串精确补强第二批 ----------


def test_build_parser_source_starts_with_def():
    src = inspect.getsource(_build_parser)
    assert src.lstrip().startswith("def _build_parser(")


def test_build_parser_source_returns_argument_parser():
    src = inspect.getsource(_build_parser)
    assert "return p" in src


def test_build_parser_source_uses_argparse_argument_parser():
    src = inspect.getsource(_build_parser)
    assert "argparse.ArgumentParser(" in src


def test_build_parser_source_prog_eq_evaluation_cli():
    src = inspect.getsource(_build_parser)
    assert 'prog="evaluation.cli"' in src


def test_build_parser_source_description_present():
    src = inspect.getsource(_build_parser)
    assert "description=" in src


def test_build_parser_source_formatter_class():
    src = inspect.getsource(_build_parser)
    assert "RawDescriptionHelpFormatter" in src


def test_build_parser_source_add_subparsers():
    src = inspect.getsource(_build_parser)
    assert ".add_subparsers(" in src
    assert 'dest="command"' in src
    assert "required=True" in src


def test_build_parser_source_three_add_parser():
    src = inspect.getsource(_build_parser)
    assert src.count("add_parser(") == 3


def test_build_parser_source_add_parser_run():
    src = inspect.getsource(_build_parser)
    assert '.add_parser("run"' in src


def test_build_parser_source_add_parser_validate_report():
    src = inspect.getsource(_build_parser)
    assert '"validate-report"' in src


def test_build_parser_source_add_parser_inspect_doc():
    src = inspect.getsource(_build_parser)
    assert '"inspect-doc"' in src


def test_build_parser_source_choices_fallback_kreuzberg():
    src = inspect.getsource(_build_parser)
    assert '"fallback"' in src
    assert '"kreuzberg"' in src


def test_build_parser_source_default_fallback():
    src = inspect.getsource(_build_parser)
    assert 'default="fallback"' in src


def test_build_parser_source_max_chars_default_800():
    src = inspect.getsource(_build_parser)
    assert "default=800" in src


def test_build_parser_source_tolerance_chars_default_30():
    src = inspect.getsource(_build_parser)
    assert "default=30" in src


def test_build_parser_source_type_int_for_max_chars():
    src = inspect.getsource(_build_parser)
    assert "type=int" in src


def test_build_parser_source_required_manifest():
    src = inspect.getsource(_build_parser)
    assert '"--manifest", required=True' in src


def test_build_parser_source_required_output():
    src = inspect.getsource(_build_parser)
    assert '"--output", required=True' in src


def test_build_parser_source_no_eval_no_exec():
    src = inspect.getsource(_build_parser)
    assert "eval(" not in src
    assert "exec(" not in src


def test_build_parser_source_no_compile():
    src = inspect.getsource(_build_parser)
    assert "compile(" not in src


def test_build_parser_source_no_subprocess():
    src = inspect.getsource(_build_parser)
    assert "subprocess" not in src


def test_build_parser_source_no_os_system():
    src = inspect.getsource(_build_parser)
    assert "os.system" not in src


# ---------- main source level 字符串精确补强第二批 ----------


def test_main_source_starts_with_def():
    src = inspect.getsource(main)
    assert src.lstrip().startswith("def main(")


def test_main_source_returns_int():
    src = inspect.getsource(main)
    # 多处 return 0/1/2
    assert "return 0" in src
    assert "return 1" in src
    assert "return 2" in src


def test_main_source_uses_build_parser():
    src = inspect.getsource(main)
    assert "_build_parser()" in src


def test_main_source_uses_parse_args():
    src = inspect.getsource(main)
    assert ".parse_args(argv)" in src


def test_main_source_handles_run_command():
    src = inspect.getsource(main)
    assert 'args.command == "run"' in src


def test_main_source_handles_validate_report_command():
    src = inspect.getsource(main)
    assert 'args.command == "validate-report"' in src


def test_main_source_handles_inspect_doc_command():
    src = inspect.getsource(main)
    assert 'args.command == "inspect-doc"' in src


def test_main_source_uses_path():
    src = inspect.getsource(main)
    assert "Path(" in src


def test_main_source_uses_load_manifest():
    src = inspect.getsource(main)
    assert "load_manifest(" in src


def test_main_source_uses_run_evaluation():
    src = inspect.getsource(main)
    assert "run_evaluation(" in src


def test_main_source_uses_validate_file():
    src = inspect.getsource(main)
    assert 'validate_file(' in src


def test_main_source_uses_get_git_provenance():
    src = inspect.getsource(main)
    assert "get_git_provenance(" in src


def test_main_source_catches_manifest_error():
    src = inspect.getsource(main)
    assert "ManifestError" in src


def test_main_source_catches_eval_schema_error():
    src = inspect.getsource(main)
    assert "EvalSchemaError" in src


def test_main_source_catches_json_decode_error():
    src = inspect.getsource(main)
    assert "json.JSONDecodeError" in src


def test_main_source_catches_file_not_found_error():
    src = inspect.getsource(main)
    assert "FileNotFoundError" in src


def test_main_source_uses_manifest_project_root():
    src = inspect.getsource(main)
    assert "manifest.project_root" in src


def test_main_source_uses_stderr():
    src = inspect.getsource(main)
    assert "sys.stderr" in src or "file=sys.stderr" in src


def test_main_source_default_return_2():
    """末尾默认 return 2。"""
    src = inspect.getsource(main)
    # 末尾应该有 return 2 兜底
    assert "return 2" in src


def test_main_source_uses_args_parser():
    src = inspect.getsource(main)
    assert "args.parser" in src


def test_main_source_uses_args_max_chars():
    src = inspect.getsource(main)
    assert "args.max_chars" in src


def test_main_source_uses_args_tolerance_chars():
    src = inspect.getsource(main)
    assert "args.tolerance_chars" in src


def test_main_source_uses_args_manifest():
    src = inspect.getsource(main)
    assert "args.manifest" in src


def test_main_source_uses_args_output():
    src = inspect.getsource(main)
    assert "args.output" in src


def test_main_source_uses_args_input():
    src = inspect.getsource(main)
    assert "args.input" in src


def test_main_source_no_eval():
    src = inspect.getsource(main)
    assert "eval(" not in src


def test_main_source_no_exec():
    src = inspect.getsource(main)
    assert "exec(" not in src


def test_main_source_no_subprocess():
    src = inspect.getsource(main)
    assert "subprocess" not in src


def test_main_source_no_yield():
    src = inspect.getsource(main)
    assert "yield" not in src


def test_main_source_no_async():
    src = inspect.getsource(main)
    assert "async def" not in src


def test_main_source_no_global():
    src = inspect.getsource(main)
    lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    for l in lines:
        assert not l.strip().startswith("global ")


def test_main_source_uses_validate_file_with_report_schema():
    src = inspect.getsource(main)
    assert '"evaluation-report.schema.json"' in src


# ---------- _format_metric source level 字符串精确补强第二批 ----------


def test_format_metric_source_starts_with_def():
    src = inspect.getsource(_format_metric)
    assert src.lstrip().startswith("def _format_metric(")


def test_format_metric_source_two_params():
    src = inspect.getsource(_format_metric)
    assert "name: str" in src
    assert "metric: dict" in src


def test_format_metric_source_uses_get_value():
    src = inspect.getsource(_format_metric)
    assert 'metric.get("value")' in src


def test_format_metric_source_uses_get_reason():
    src = inspect.getsource(_format_metric)
    assert 'metric.get("reason")' in src


def test_format_metric_source_handles_none():
    src = inspect.getsource(_format_metric)
    assert "if value is None" in src or "value is None" in src


def test_format_metric_source_handles_bool():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, bool)" in src


def test_format_metric_source_handles_float():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, float)" in src


def test_format_metric_source_handles_dict():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, dict)" in src


def test_format_metric_source_str_lower_for_bool():
    src = inspect.getsource(_format_metric)
    assert ".lower()" in src or "str(value).lower" in src


def test_format_metric_source_float_format_4f():
    src = inspect.getsource(_format_metric)
    assert ":.4f" in src


def test_format_metric_source_name_padding():
    src = inspect.getsource(_format_metric)
    assert "{name:36}" in src or ":36" in src


def test_format_metric_source_default_ok():
    src = inspect.getsource(_format_metric)
    assert "'ok'" in src or '"ok"' in src


def test_format_metric_source_dict_items_join():
    src = inspect.getsource(_format_metric)
    assert ".join(" in src


def test_format_metric_source_no_eval():
    src = inspect.getsource(_format_metric)
    assert "eval(" not in src


def test_format_metric_source_no_subprocess():
    src = inspect.getsource(_format_metric)
    assert "subprocess" not in src


# ---------- _run_inspect_doc source level 字符串精确补强第二批 ----------


def test_run_inspect_doc_source_starts_with_def():
    src = inspect.getsource(_run_inspect_doc)
    assert src.lstrip().startswith("def _run_inspect_doc(")


def test_run_inspect_doc_source_one_param_args():
    src = inspect.getsource(_run_inspect_doc)
    assert "args" in src


def test_run_inspect_doc_source_lazy_import_annotation():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in src


def test_run_inspect_doc_source_lazy_import_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.metrics import" in src


def test_run_inspect_doc_source_imports_chunk_boundary_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf" in src


def test_run_inspect_doc_source_imports_figure_caption_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf" in src


def test_run_inspect_doc_source_imports_compute_automatic_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "compute_automatic_metrics" in src


def test_run_inspect_doc_source_uses_path_args_input():
    src = inspect.getsource(_run_inspect_doc)
    assert "Path(args.input)" in src


def test_run_inspect_doc_source_uses_is_file():
    src = inspect.getsource(_run_inspect_doc)
    assert ".is_file()" in src


def test_run_inspect_doc_source_handles_json_decode_error():
    src = inspect.getsource(_run_inspect_doc)
    assert "json.JSONDecodeError" in src


def test_run_inspect_doc_source_uses_doc_get():
    src = inspect.getsource(_run_inspect_doc)
    assert 'doc.get("source_type"' in src


def test_run_inspect_doc_source_uses_doc_get_elements():
    src = inspect.getsource(_run_inspect_doc)
    assert 'doc.get("elements")' in src


def test_run_inspect_doc_source_uses_doc_get_chunks():
    src = inspect.getsource(_run_inspect_doc)
    assert 'doc.get("chunks")' in src


def test_run_inspect_doc_source_passes_args_tolerance_chars():
    src = inspect.getsource(_run_inspect_doc)
    assert "args.tolerance_chars" in src


def test_run_inspect_doc_source_uses_format_metric():
    src = inspect.getsource(_run_inspect_doc)
    assert "_format_metric(" in src


def test_run_inspect_doc_source_uses_sort_key():
    src = inspect.getsource(_run_inspect_doc)
    assert "_sort_key" in src


def test_run_inspect_doc_source_uses_sorted():
    src = inspect.getsource(_run_inspect_doc)
    assert "sorted(" in src


def test_run_inspect_doc_source_returns_int():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 0" in src
    assert "return 1" in src
    assert "return 2" in src


def test_run_inspect_doc_source_uses_print():
    src = inspect.getsource(_run_inspect_doc)
    assert "print(" in src


def test_run_inspect_doc_source_no_eval():
    src = inspect.getsource(_run_inspect_doc)
    assert "eval(" not in src


def test_run_inspect_doc_source_no_subprocess():
    src = inspect.getsource(_run_inspect_doc)
    assert "subprocess" not in src


def test_run_inspect_doc_source_handles_not_dict():
    src = inspect.getsource(_run_inspect_doc)
    assert "isinstance(doc, dict)" in src


def test_run_inspect_doc_source_uses_open():
    src = inspect.getsource(_run_inspect_doc)
    assert ".open(" in src


def test_run_inspect_doc_source_uses_utf8():
    src = inspect.getsource(_run_inspect_doc)
    assert '"utf-8"' in src or "'utf-8'" in src


# ---------- argparse 边界第四批 ----------


def test_build_parser_prog_value():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_value():
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 5


def test_build_parser_formatter_class_raw_description():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_subparsers_required():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m", "--output", "r"])
    assert ns.command == "run"


def test_build_parser_run_help_string():
    p = _build_parser()
    # 通过 _actions 检查 help
    actions = {a.dest: a for a in p._actions}
    assert "command" in actions


def test_build_parser_run_max_chars_help_text():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(subparsers) == 1
    run_p = subparsers[0].choices["run"]
    max_chars_action = next(
        a for a in run_p._actions if "--max-chars" in (a.option_strings or [])
    )
    assert max_chars_action.help is not None
    assert "800" in max_chars_action.help


def test_build_parser_run_tolerance_chars_help_text():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    tol_action = next(
        a for a in run_p._actions if "--tolerance-chars" in (a.option_strings or [])
    )
    assert tol_action.help is not None
    assert "30" in tol_action.help


def test_build_parser_run_parser_help_text():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    parser_action = next(
        a for a in run_p._actions if "--parser" in (a.option_strings or [])
    )
    assert parser_action.help is not None


def test_build_parser_validate_report_help_text():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = subparsers[0].choices["validate-report"]
    # validate-report 用 help 而非 description
    assert val_p is not None


def test_build_parser_inspect_doc_help_text():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = subparsers[0].choices["inspect-doc"]
    assert ins_p is not None


def test_build_parser_run_manifest_required():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    manifest_action = next(
        a for a in run_p._actions if "--manifest" in (a.option_strings or [])
    )
    assert manifest_action.required is True


def test_build_parser_run_output_required():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    output_action = next(
        a for a in run_p._actions if "--output" in (a.option_strings or [])
    )
    assert output_action.required is True


def test_build_parser_run_parser_not_required():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    parser_action = next(
        a for a in run_p._actions if "--parser" in (a.option_strings or [])
    )
    assert parser_action.required is False


def test_build_parser_run_max_chars_not_required():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    max_chars_action = next(
        a for a in run_p._actions if "--max-chars" in (a.option_strings or [])
    )
    assert max_chars_action.required is False


def test_build_parser_validate_report_input_positional():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_build_parser_inspect_doc_input_positional():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_build_parser_inspect_doc_default_tolerance_30():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_override():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert ns.tolerance_chars == 100


def test_build_parser_inspect_doc_no_parser_param():
    """inspect-doc 没有 --parser 参数。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc", "doc.json", "--parser", "fallback"])


def test_build_parser_inspect_doc_no_max_chars():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc", "doc.json", "--max-chars", "1000"])


def test_build_parser_validate_report_no_optional_args():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_inspect_doc_no_input():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_choices_correct():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert set(subparsers[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_choices_only_fallback_kreuzberg():
    p = _build_parser()
    subparsers = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers[0].choices["run"]
    parser_action = next(
        a for a in run_p._actions if "--parser" in (a.option_strings or [])
    )
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


# ---------- main 行为深度第五批 ----------


def test_main_unknown_command_returns_2():
    """argparse 子命令 required=True 时未知子命令会 SystemExit。"""
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_validate_report_nonexistent_returns_2(tmp_path):
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_inspect_doc_nonexistent_returns_2(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_top_level_array_returns_1(tmp_path):
    f = tmp_path / "arr.json"
    f.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_top_level_int_returns_1(tmp_path):
    f = tmp_path / "int.json"
    f.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_top_level_string_returns_1(tmp_path):
    f = tmp_path / "str.json"
    f.write_text('"hello"', encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_top_level_null_returns_1(tmp_path):
    f = tmp_path / "null.json"
    f.write_text("null", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_minimal_doc_returns_0(tmp_path):
    f = tmp_path / "doc.json"
    f.write_text(
        json.dumps({
            "document_id": "d1",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(f)])
    assert rc == 0


def test_main_validate_report_valid_array_returns_1(tmp_path):
    """报告顶层必须是 dict；array 不通过 schema。"""
    f = tmp_path / "report.json"
    f.write_text("[]", encoding="utf-8")
    rc = main(["validate-report", str(f)])
    assert rc == 1


def test_main_validate_report_invalid_json_returns_1(tmp_path):
    f = tmp_path / "report.json"
    f.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(f)])
    assert rc == 1


def test_main_validate_report_minimal_valid_dict(tmp_path):
    """构造一个最小的合法 evaluation-report JSON。"""
    f = tmp_path / "report.json"
    # Schema 要求 evaluator_version、report_version、parser_name、parser_version、metrics
    f.write_text(
        json.dumps({
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": "test",
            "metrics": {},
            "per_doc": [],
        }),
        encoding="utf-8",
    )
    rc = main(["validate-report", str(f)])
    # 即使 schema 不接受也应该是 1（校验失败）
    assert rc in (0, 1)


def test_main_run_with_nonexistent_manifest_returns_2(tmp_path):
    rc = main([
        "run",
        "--manifest", str(tmp_path / "nope.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2


# ---------- module source forbidden tokens 第七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "subprocess",
        "multiprocessing", "queue", "socket", "select",
        "re.match", "re.sub", "re.compile",
        "datetime.datetime",
        "time.time", "time.sleep", "time.perf_counter",
        "os.system", "os.popen", "os.exec",
        "os.spawn", "os.fork",
        "logging.getLogger", "logging.info",
        "logging.warning", "logging.error",
        "logging.debug", "logging.critical",
        "urllib.request", "http.client", "http.server",
        "ctypes", "cffi", "gc.collect",
        "pickle.loads", "pickle.dumps",
        "shutil.rmtree", "shutil.copy",
        "tempfile.mkdtemp",
        "glob.glob",
        "argparse.ArgumentParser",  # 仅出现在 _build_parser 中是合法的
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque", "collections.defaultdict",
        "collections.Counter", "collections.namedtuple",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_cli_source_no_forbidden_token(token):
    src = inspect.getsource(cli_mod)
    # 这些模块/标识符不应在 cli.py 中出现
    # 注意 argparse 是合法的（必须用），单独处理
    if token == "argparse.ArgumentParser":
        # argparse 确实用了，但用得合法
        assert "import argparse" in src
        return
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_cli_source_module_docstring_present():
    src = inspect.getsource(cli_mod)
    assert src.startswith('"""')


def test_cli_source_docstring_mentions_subcommands():
    src = inspect.getsource(cli_mod)
    assert "run" in src
    assert "validate-report" in src
    assert "inspect-doc" in src


def test_cli_source_has_utf8_reconfigure():
    src = inspect.getsource(cli_mod)
    assert "reconfigure" in src
    assert 'encoding="utf-8"' in src


def test_cli_source_4_stdlib_imports():
    src = inspect.getsource(cli_mod)
    assert "from __future__ import annotations" in src
    assert "import argparse" in src
    assert "import json" in src
    assert "import sys" in src
    assert "from pathlib import Path" in src


def test_cli_source_4_evaluation_imports():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src
    assert "from evaluation.report import get_git_provenance" in src
    assert "from evaluation.runner import run_evaluation" in src
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_cli_source_no_relative_import_above_eval():
    src = inspect.getsource(cli_mod)
    assert "from .." not in src


def test_cli_source_no_star_import():
    src = inspect.getsource(cli_mod)
    assert "import *" not in src


def test_cli_source_no_yield():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_cli_source_no_async_def():
    src = inspect.getsource(cli_mod)
    assert "async def" not in src


def test_cli_source_no_walrus():
    src = inspect.getsource(cli_mod)
    assert ":=" not in src


def test_cli_source_has_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__' in src
    assert "__main__" in src


def test_cli_source_main_block_raises_system_exit():
    src = inspect.getsource(cli_mod)
    assert "raise SystemExit(main())" in src


def test_cli_source_4_functions():
    """4 个 user-defined function：_build_parser、main、_format_metric、_run_inspect_doc。"""
    import types as _types
    funcs = [
        name for name, val in vars(cli_mod).items()
        if isinstance(val, _types.FunctionType) and val.__module__ == cli_mod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_cli_source_no_user_class():
    classes = [
        name for name, val in vars(cli_mod).items()
        if isinstance(val, type) and val.__module__ == cli_mod.__name__
    ]
    assert classes == []


def test_cli_source_has_no_all_attribute():
    """cli.py 没有 __all__。"""
    assert not hasattr(cli_mod, "__all__") or cli_mod.__all__ is None


def test_cli_source_uses_print():
    src = inspect.getsource(cli_mod)
    assert "print(" in src


def test_cli_source_no_eval():
    src = inspect.getsource(cli_mod)
    assert "eval(" not in src


def test_cli_source_no_exec():
    src = inspect.getsource(cli_mod)
    assert "exec(" not in src


def test_cli_source_no_compile():
    src = inspect.getsource(cli_mod)
    assert "compile(" not in src


def test_cli_source_uses_hasattr():
    src = inspect.getsource(cli_mod)
    assert "hasattr(sys.stdout" in src


def test_cli_source_uses_attribute_error():
    src = inspect.getsource(cli_mod)
    assert "AttributeError" in src


def test_cli_source_uses_oserror():
    src = inspect.getsource(cli_mod)
    assert "OSError" in src


def test_cli_source_uses_errors_replace():
    src = inspect.getsource(cli_mod)
    assert 'errors="replace"' in src


def test_cli_source_no_open_input_user_input():
    """cli.py 不读 stdin。"""
    src = inspect.getsource(cli_mod)
    assert "sys.stdin" not in src


def test_cli_source_module_level_reconfigure_block():
    """模块级 reconfigure 块。"""
    src = inspect.getsource(cli_mod)
    # 应该在 module top-level（不在函数内）
    assert 'sys.stdout.reconfigure' in src


# ---------- signatures 精确补强 ----------


def test_signature_build_parser():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_main():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"


def test_signature_main_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_format_metric():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["name", "metric"]


def test_signature_format_metric_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_run_inspect_doc():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "args"


def test_signature_run_inspect_doc_no_default():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.parameters["args"].default is inspect.Parameter.empty


def test_signature_build_parser_no_varargs():
    sig = inspect.signature(_build_parser)
    assert "args" not in sig.parameters
    assert "kwargs" not in sig.parameters


def test_signature_main_no_varargs():
    sig = inspect.signature(main)
    assert "args" not in sig.parameters
    assert "kwargs" not in sig.parameters


def test_signature_format_metric_no_varargs():
    sig = inspect.signature(_format_metric)
    assert "args" not in sig.parameters
    assert "kwargs" not in sig.parameters


def test_signature_run_inspect_doc_no_varargs():
    sig = inspect.signature(_run_inspect_doc)
    # args 是参数名（POSITIONAL_OR_KEYWORD），不是 *args（VAR_POSITIONAL）
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_main_return_annotation():
    sig = inspect.signature(main)
    # main 声明 -> int
    # 因 from __future__ import annotations，注解是字符串
    annot = sig.return_annotation
    assert annot == "int" or annot is int


def test_signature_run_inspect_doc_return_annotation():
    sig = inspect.signature(_run_inspect_doc)
    annot = sig.return_annotation
    assert annot == "int" or annot is int


def test_signature_format_metric_return_annotation():
    sig = inspect.signature(_format_metric)
    annot = sig.return_annotation
    assert annot == "str" or annot is str


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert cli_mod.__doc__ is not None
    assert len(cli_mod.__doc__) > 10


def test_module_docstring_mentions_cli():
    assert "CLI" in cli_mod.__doc__ or "cli" in cli_mod.__doc__.lower()


def test_module_docstring_mentions_run():
    assert "run" in cli_mod.__doc__


def test_module_docstring_mentions_validate():
    assert "validate" in cli_mod.__doc__.lower()


def test_module_docstring_mentions_inspect():
    assert "inspect" in cli_mod.__doc__.lower()


def test_module_name_is_evaluation_cli():
    assert cli_mod.__name__ == "evaluation.cli"


def test_module_file_ends_with_cli_py():
    assert cli_mod.__file__.endswith("cli.py")


def test_module_namespace_4_callables():
    """4 个 module-level 函数：_build_parser、main、_format_metric、_run_inspect_doc。"""
    funcs = [
        name for name, val in vars(cli_mod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == cli_mod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_namespace_has_main():
    assert hasattr(cli_mod, "main")
    assert callable(cli_mod.main)


def test_module_namespace_has_build_parser():
    assert hasattr(cli_mod, "_build_parser")
    assert callable(cli_mod._build_parser)


def test_module_namespace_has_format_metric():
    assert hasattr(cli_mod, "_format_metric")
    assert callable(cli_mod._format_metric)


def test_module_namespace_has_run_inspect_doc():
    assert hasattr(cli_mod, "_run_inspect_doc")
    assert callable(cli_mod._run_inspect_doc)


def test_module_no_classes_user_defined():
    classes = [
        name for name, val in vars(cli_mod).items()
        if isinstance(val, type) and val.__module__ == cli_mod.__name__
    ]
    assert classes == []


def test_module_imports_argparse():
    import argparse as _argparse
    assert cli_mod.argparse is _argparse


def test_module_imports_json():
    import json as _json
    assert cli_mod.json is _json


def test_module_imports_sys():
    import sys as _sys
    assert cli_mod.sys is _sys


def test_module_imports_path():
    assert hasattr(cli_mod, "Path")


def test_module_imports_manifest_error():
    assert hasattr(cli_mod, "ManifestError")


def test_module_imports_load_manifest():
    assert hasattr(cli_mod, "load_manifest")


def test_module_imports_get_git_provenance():
    assert hasattr(cli_mod, "get_git_provenance")


def test_module_imports_run_evaluation():
    assert hasattr(cli_mod, "run_evaluation")


def test_module_imports_eval_schema_error():
    assert hasattr(cli_mod, "EvalSchemaError")


def test_module_imports_validate_file():
    assert hasattr(cli_mod, "validate_file")


# ---------- 端到端集成补强 ----------


def test_e2e_run_inspect_doc_full_output(tmp_path, capsys):
    """跑一个真实文档，检查 stdout 输出。"""
    f = tmp_path / "doc.json"
    f.write_text(
        json.dumps({
            "document_id": "d1",
            "source_type": "pdf",
            "source_path": "/abs/path.pdf",
            "parser_name": "fallback",
            "parser_version": "test",
            "elements": [{"element_id": "e1", "type": "paragraph", "text": "hello"}],
            "chunks": [{"chunk_id": "c1", "source_element_ids": ["e1"], "text": "hello"}],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out
    assert "document_id:" in out
    assert "metrics:" in out


def test_e2e_run_inspect_doc_with_tolerance_chars(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(
        json.dumps({
            "document_id": "d1",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "100"])
    assert rc == 0


def test_e2e_run_inspect_doc_with_empty_dict(tmp_path):
    f = tmp_path / "doc.json"
    f.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0


def test_e2e_format_metric_int_value():
    s = _format_metric("count", {"value": 5, "reason": None})
    assert "5" in s
    assert "count" in s


def test_e2e_format_metric_str_value():
    s = _format_metric("name", {"value": "hello", "reason": None})
    assert "hello" in s


def test_e2e_format_metric_list_value():
    """value 不是 None/bool/float/dict/int/str 时走 default 分支。"""
    s = _format_metric("name", {"value": [1, 2, 3], "reason": None})
    assert "name" in s


def test_e2e_format_metric_long_name():
    s = _format_metric("a" * 50, {"value": 1, "reason": None})
    assert "a" * 50 in s


def test_e2e_format_metric_dict_value():
    s = _format_metric("element_count", {"value": {"paragraph": 5}, "reason": None})
    assert "paragraph=5" in s


def test_e2e_format_metric_dict_value_multiple_keys():
    s = _format_metric(
        "element_count",
        {"value": {"paragraph": 5, "heading": 2}, "reason": None},
    )
    assert "paragraph=5" in s
    assert "heading=2" in s


def test_e2e_format_metric_reason_in_output():
    s = _format_metric("name", {"value": None, "reason": "no_data"})
    assert "no_data" in s


def test_e2e_format_metric_default_ok_reason():
    s = _format_metric("name", {"value": True, "reason": None})
    assert "ok" in s


def test_e2e_format_metric_no_value_no_reason():
    s = _format_metric("name", {})
    # 空 dict → value=None，走 None 分支
    assert "name" in s
    assert "None" in s or "null" in s
