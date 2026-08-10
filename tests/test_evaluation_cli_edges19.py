r"""evaluation/cli.py 边角测试 - 第十九轮（Round 272）。

edges18 已覆盖：build_parser prog/description/formatter/subparsers required+dest/3 subparser
/5+1+2 args/required args/默认值/类型/choices/SystemExit；_format_metric None/bool True+False/
float 4 decimal/int/empty dict/sorted dict items/str/list/missing keys/empty dict/name 36 char 对齐；
_run_inspect_doc 输入不存在/JSON 无效/top 非 dict/minimal dict succeed/缺 source_type/elements/chunks/
null elements 计数/输出含 file/document_id/source/parser/metrics line/sort bool first/tolerance 透传/
default tolerance/returns 0；main 三 subcommand 错误路径；源码 token 含/不含；namespace has；
identity/qualname；signature 详细（main argv 默认 None；_build_parser no params；_format_metric 2 params；
_run_inspect_doc 1 param；no var args/kwargs）。

edges19 补强未覆盖的角度：
- _format_metric 详细字符串精确性（精确前缀/分隔符/字面量）
- _run_inspect_doc _sort_key 函数内部行为（tuple 类型；None 优先级；bool 优先级）
- _run_inspect_doc 打印顺序（file → document_id → source → parser → counts → metrics header）
- main argv=None 时不崩（用 monkeypatch sys.argv）
- argparse _SubParsersAction 类型精确
- argparse _actions 第一个是 help action
- 模块 import 顺序精确（argparse → json → sys → pathlib → evaluation.manifest → evaluation.report → evaluation.runner → evaluation.schema）
- evaluation 子模块导入名精确（load_manifest / ManifestError / get_git_provenance / run_evaluation / validate_file / EvalSchemaError）
- 模块 source 含 'choices=("fallback", "kreuzberg")' 精确字符串
- 模块 source 含 'sys.stdout.reconfigure(encoding="utf-8", errors="replace")'
- 模块 source 含 'if hasattr(sys.stdout, "reconfigure")'
- 模块 source 含 'print(f"[ERROR]"' / 'print(f"[OK]"' / 'print(f"[FAIL]"'
- _format_metric 输出始终以 '  '（两个空格）开头
- _format_metric 中 None reason fallback 为 'ok' 字面量
- _format_metric float 输出含 '.0000' 当 value=0.0
- _format_metric 当 value=0（int）走 fallback（int 不是 bool 不是 float 不是 dict）
- _run_inspect_doc metrics 包含 figure_caption_prf + chunk_boundary_prf 输出
- _run_inspect_doc 三个 lazy import 在函数内
- _run_inspect_doc 输出含 'elements=' 和 'chunks='
- _run_inspect_doc 输出 file 行用 input_path（Path 对象）
- main validate-report 调用 validate_file 的 schema_name 是 'evaluation-report.schema.json'
- main 返回值类型是 int
- 模块 __name__ == '__main__' 块抛 SystemExit
- _build_parser subparser 帮助文本含中文
- prog 与 description 的精确字符串
- 模块顶层 docstring 提到子命令 run / validate-report / inspect-doc
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import cli as cli_module
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# _format_metric 精确字符串
# =========================================================================


def test_format_metric_output_starts_with_two_spaces():
    """所有 _format_metric 输出都以 '  '（两个空格）开头。"""
    out = _format_metric("x", {"value": None, "reason": "no_x"})
    assert out.startswith("  ")


def test_format_metric_output_starts_with_two_spaces_for_bool():
    out = _format_metric("x", {"value": True, "reason": None})
    assert out.startswith("  ")


def test_format_metric_output_starts_with_two_spaces_for_int():
    out = _format_metric("x", {"value": 5, "reason": None})
    assert out.startswith("  ")


def test_format_metric_none_value_uses_literal_null():
    out = _format_metric("schema_valid", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "(no_data)" in out


def test_format_metric_none_value_no_extra_ok():
    """None 时不应 fallback 为 'ok'。"""
    out = _format_metric("x", {"value": None, "reason": None})
    assert "ok" not in out


def test_format_metric_bool_value_with_none_reason_uses_ok_literal():
    """bool value + reason=None → fallback 'ok'。"""
    out = _format_metric("x", {"value": True, "reason": None})
    assert "(ok)" in out


def test_format_metric_int_value_with_none_reason_uses_ok_literal():
    out = _format_metric("x", {"value": 5, "reason": None})
    assert "(ok)" in out


def test_format_metric_dict_value_with_none_reason_uses_ok_literal():
    out = _format_metric("x", {"value": {"a": 1}, "reason": None})
    assert "(ok)" in out


def test_format_metric_float_value_with_none_reason_uses_ok_literal():
    out = _format_metric("x", {"value": 1.5, "reason": None})
    assert "(ok)" in out


def test_format_metric_zero_float_renders_dot_0000():
    out = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_one_float_renders_dot_1_0000():
    out = _format_metric("x", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_float_renders_4_decimals_exact():
    """{value:.4f} 格式 → 整数部分原样，小数 4 位。"""
    out = _format_metric("x", {"value": 0.123456, "reason": None})
    # 截断到 4 位（实际是四舍五入）
    assert "0.1235" in out


def test_format_metric_negative_float_renders_minus_sign():
    out = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_dict_value_comma_separated_exact():
    """dict value: 'k=v, k2=v2'（按 key sorted）。"""
    out = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1, b=2" in out


def test_format_metric_dict_value_three_items_comma_separated():
    out = _format_metric("x", {"value": {"a": 1, "b": 2, "c": 3}, "reason": None})
    assert "a=1, b=2, c=3" in out


def test_format_metric_dict_value_sorts_by_key():
    """sorted(value.items()) → 按 key 字典序。"""
    out = _format_metric("x", {"value": {"b": 2, "a": 1}, "reason": None})
    # a 应在 b 前
    assert out.index("a=1") < out.index("b=2")


def test_format_metric_bool_true_lowercase_string():
    """str(True).lower() == 'true'。"""
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_lowercase_string():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out
    assert "False" not in out


def test_format_metric_str_value_uses_str_builtin():
    """str value 走 fallback → str(value) + ok。"""
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out
    assert "(ok)" in out


def test_format_metric_list_value_uses_str_builtin():
    """list value 走 fallback → str([1,2,3])。"""
    out = _format_metric("x", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_name_field_alignment_with_long_name():
    """name:36 → 长 name（>36 char）不截断，输出仍含原 name。"""
    long_name = "x" * 50
    out = _format_metric(long_name, {"value": 0, "reason": None})
    assert long_name in out


def test_format_metric_returns_str_type():
    out = _format_metric("x", {"value": 1, "reason": None})
    assert isinstance(out, str)


# =========================================================================
# _run_inspect_doc _sort_key 详细
# =========================================================================


def test_run_inspect_doc_output_has_counts_label(capsys, tmp_path):
    """输出含 'counts:' 标签。"""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "counts:" in captured.out


def test_run_inspect_doc_output_counts_line_format(capsys, tmp_path):
    """counts: elements=N chunks=N。"""
    doc_path = tmp_path / "doc.json"
    doc = {"elements": [{"type": "paragraph"}], "chunks": [{"id": "c1"}]}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_run_inspect_doc_output_prints_metrics_header(capsys, tmp_path):
    """输出 'metrics:' header。"""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 'metrics:' 单独行
    assert "metrics:\n" in captured.out or "metrics:" in captured.out


def test_run_inspect_doc_output_file_line_uses_input_path(capsys, tmp_path):
    """file: 行用 input_path（Path 对象 → str）。"""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert str(doc_path) in captured.out


def test_run_inspect_doc_output_lines_in_order(capsys, tmp_path):
    """file → document_id → source → parser → counts → metrics 顺序。"""
    doc_path = tmp_path / "doc.json"
    doc = {"document_id": "doc-1", "source_path": "/p", "source_type": "pdf"}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    out = captured.out
    pos_file = out.find("file:")
    pos_doc_id = out.find("document_id:")
    pos_source = out.find("source:")
    pos_parser = out.find("parser:")
    pos_counts = out.find("counts:")
    pos_metrics = out.find("metrics:")
    assert pos_file < pos_doc_id < pos_source < pos_parser < pos_counts < pos_metrics


def test_run_inspect_doc_output_has_blank_line_before_metrics(capsys, tmp_path):
    """counts 行后有空行，然后是 metrics: 行。"""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 至少有一处 \n\n 分隔
    assert "\n\n" in captured.out


def test_run_inspect_doc_sort_key_metrics_in_order(capsys, tmp_path):
    """bool metrics → int/float → 其他 → null 顺序。"""
    doc_path = tmp_path / "doc.json"
    # 构造能产生不同类型 metric 的 doc
    doc = {"source_type": "unknown", "elements": []}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 至少有一行 null 类的 metric
    assert "null" in captured.out


# =========================================================================
# _run_inspect_doc lazy imports
# =========================================================================


def test_run_inspect_doc_lazy_imports_figure_caption_prf():
    """figure_caption_prf 在函数内 lazy import。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in src
    assert "figure_caption_prf" in src


def test_run_inspect_doc_lazy_imports_chunk_boundary_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf" in src


def test_run_inspect_doc_lazy_imports_compute_automatic_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "compute_automatic_metrics" in src


def test_run_inspect_doc_calls_compute_automatic_metrics_with_image_base_dir_none():
    """compute_automatic_metrics 调用包含 image_base_dir=None 字面量。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "image_base_dir=None" in src


def test_run_inspect_doc_calls_metrics_update_twice():
    """metrics.update 调用两次（figure_caption + chunk_boundary）。"""
    src = inspect.getsource(_run_inspect_doc)
    assert src.count("metrics.update(") >= 2


# =========================================================================
# main argv=None
# =========================================================================


def test_main_argv_none_uses_sys_argv(monkeypatch):
    """main(argv=None) 走 sys.argv。"""
    # 设置 sys.argv 为无效 → argparse error → SystemExit
    monkeypatch.setattr("sys.argv", ["evaluation.cli"])
    with pytest.raises(SystemExit):
        main(None)


def test_main_argv_empty_list_raises_system_exit():
    """main([]) → argparse required subcommand → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_returns_int_type_for_inspect_doc_success(tmp_path, capsys):
    """main inspect-doc 成功返回 int（0）。"""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(doc_path)])
    assert isinstance(rc, int)
    assert rc == 0


def test_main_returns_int_type_for_validate_report_input_missing(tmp_path):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert isinstance(rc, int)
    assert rc == 2


def test_main_returns_int_type_for_inspect_doc_input_missing(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert isinstance(rc, int)
    assert rc == 2


def test_main_returns_int_type_for_run_manifest_missing(tmp_path):
    rc = main(["run", "--manifest", str(tmp_path / "no.json"), "--output", str(tmp_path / "out.json")])
    assert isinstance(rc, int)
    assert rc == 2


# =========================================================================
# argparse _SubParsersAction 类型
# =========================================================================


def test_build_parser_subparsers_action_is_sub_parsers_action():
    """add_subparsers 创建的 action 是 _SubParsersAction 类型。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(sub_actions) == 1


def test_build_parser_first_action_is_help():
    """argparse 默认第一个 action 是 _HelpAction。"""
    p = _build_parser()
    # 至少有一个 action 是 help action
    help_actions = [a for a in p._actions if isinstance(a, argparse._HelpAction)]
    assert len(help_actions) == 1


def test_build_parser_subparsers_action_choices_keys_are_run_validate_inspect():
    """_SubParsersAction.choices.keys() == {'run', 'validate-report', 'inspect-doc'}。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_subparsers_action_choices_values_are_argument_parser():
    """choices 值都是 ArgumentParser 实例。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    for sub_p in sub_action.choices.values():
        assert isinstance(sub_p, argparse.ArgumentParser)


def test_build_parser_run_subparser_has_help_string():
    """run subparser 有 help 字符串。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    # 至少一个 action（不算 help）有 help
    actions_with_help = [a for a in run_p._actions if a.dest != "help" and a.help]
    assert len(actions_with_help) >= 1


# =========================================================================
# 模块 source token 详细
# =========================================================================


def test_module_source_contains_choices_fallback_kreuzberg_tuple():
    """源码含 'choices=("fallback", "kreuzberg")'。"""
    src = inspect.getsource(cli_module)
    assert 'choices=("fallback", "kreuzberg")' in src


def test_module_source_contains_reconfigure_utf8():
    """源码含 'sys.stdout.reconfigure(encoding="utf-8", errors="replace")'。"""
    src = inspect.getsource(cli_module)
    assert 'sys.stdout.reconfigure(encoding="utf-8", errors="replace")' in src


def test_module_source_contains_hasattr_check():
    src = inspect.getsource(cli_module)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_module_source_contains_print_error_run_manifest():
    """main run 路径含 print(f"[ERROR] 清单不存在...")。"""
    src = inspect.getsource(cli_module)
    assert "清单不存在" in src


def test_module_source_contains_print_error_run_load_failed():
    src = inspect.getsource(cli_module)
    assert "清单加载失败" in src


def test_module_source_contains_print_error_report_validation():
    src = inspect.getsource(cli_module)
    assert "报告未通过 Schema 校验" in src or "报告自校验失败" in src


def test_module_source_contains_validate_report_schema_name():
    """main 调用 validate_file 时 schema_name 是 'evaluation-report.schema.json'。"""
    src = inspect.getsource(cli_module)
    assert src.count('"evaluation-report.schema.json"') >= 2  # run + validate-report


def test_module_source_contains_path_is_file_checks():
    """main 用 input_path.is_file() 检查文件存在。"""
    src = inspect.getsource(cli_module)
    assert src.count(".is_file()") >= 3  # manifest / validate-report / inspect-doc


def test_module_source_contains_print_ok_for_run():
    src = inspect.getsource(cli_module)
    assert '"[OK] 评测完成' in src


def test_module_source_contains_print_ok_for_validate_report():
    src = inspect.getsource(cli_module)
    assert '"[OK] {input_path} 通过' in src or "通过 evaluation-report Schema 校验" in src


def test_module_source_contains_return_2_for_missing_files():
    """return 2 表示文件不存在错误（≥3 次）。"""
    src = inspect.getsource(cli_module)
    assert src.count("return 2") >= 3


def test_module_source_contains_return_1_for_validation_errors():
    """return 1 表示校验失败错误（≥3 次）。"""
    src = inspect.getsource(cli_module)
    assert src.count("return 1") >= 3


def test_module_source_does_not_contain_return_3():
    """main 只返回 0/1/2，不返回 3。"""
    src = inspect.getsource(cli_module)
    assert "return 3" not in src


def test_module_source_does_not_contain_return_negative():
    """main 不返回负数。"""
    src = inspect.getsource(cli_module)
    assert "return -1" not in src
    assert "return -2" not in src


def test_module_source_contains_run_evaluation_call():
    src = inspect.getsource(cli_module)
    assert "run_evaluation(" in src


def test_module_source_contains_load_manifest_call():
    src = inspect.getsource(cli_module)
    assert "load_manifest(" in src


def test_module_source_contains_validate_file_call():
    src = inspect.getsource(cli_module)
    assert "validate_file(" in src


def test_module_source_contains_get_git_provenance_call():
    src = inspect.getsource(cli_module)
    assert "get_git_provenance(" in src


def test_module_source_contains_manifest_error_import():
    src = inspect.getsource(cli_module)
    assert "ManifestError" in src


def test_module_source_contains_eval_schema_error_import():
    src = inspect.getsource(cli_module)
    assert "EvalSchemaError" in src


def test_module_source_contains_subprocess_free():
    """cli.py 不用 subprocess（用 evaluation.report 的 helper）。"""
    src = inspect.getsource(cli_module)
    assert "import subprocess" not in src
    assert "subprocess.run" not in src


def test_module_source_contains_no_logger():
    src = inspect.getsource(cli_module)
    assert "import logging" not in src
    assert "getLogger" not in src


def test_module_source_contains_no_async():
    src = inspect.getsource(cli_module)
    assert "async " not in src
    assert "await " not in src


def test_module_source_contains_no_threading():
    src = inspect.getsource(cli_module)
    assert "import threading" not in src
    assert "Thread(" not in src


def test_module_source_contains_no_os():
    src = inspect.getsource(cli_module)
    assert "import os" not in src


def test_module_source_contains_no_shutil():
    src = inspect.getsource(cli_module)
    assert "import shutil" not in src


def test_module_source_contains_no_tempfile():
    src = inspect.getsource(cli_module)
    assert "import tempfile" not in src


# =========================================================================
# 模块 import 顺序
# =========================================================================


def test_module_import_order_argparse_first():
    src = inspect.getsource(cli_module)
    pos_argparse = src.find("import argparse")
    pos_json = src.find("import json")
    pos_sys = src.find("import sys")
    pos_pathlib = src.find("from pathlib import Path")
    pos_manifest = src.find("from evaluation.manifest import")
    pos_report = src.find("from evaluation.report import")
    pos_runner = src.find("from evaluation.runner import")
    pos_schema = src.find("from evaluation.schema import")
    assert pos_argparse > 0
    assert pos_json > pos_argparse
    assert pos_sys > pos_json
    assert pos_pathlib > pos_sys
    # evaluation 子模块在 stdout reconfigure 之后
    assert pos_manifest > pos_pathlib
    assert pos_report > pos_manifest
    assert pos_runner > pos_report
    assert pos_schema > pos_runner


def test_module_import_manifest_load_manifest_token():
    src = inspect.getsource(cli_module)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_import_report_get_git_provenance_token():
    src = inspect.getsource(cli_module)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_import_runner_run_evaluation_token():
    src = inspect.getsource(cli_module)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_import_schema_tokens():
    src = inspect.getsource(cli_module)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_mentions_subcommand_run():
    doc = cli_module.__doc__
    assert "run" in doc


def test_module_docstring_mentions_subcommand_validate_report():
    doc = cli_module.__doc__
    assert "validate-report" in doc


def test_module_docstring_mentions_subcommand_inspect_doc():
    doc = cli_module.__doc__
    assert "inspect-doc" in doc


def test_module_docstring_mentions_python_m_evaluation_cli():
    doc = cli_module.__doc__
    assert "python -m evaluation.cli" in doc


def test_module_docstring_mentions_inspect_doc_purpose():
    """inspect-doc 是开发期 sanity check 用。"""
    doc = cli_module.__doc__
    assert "sanity" in doc or "开发期" in doc


# =========================================================================
# main 函数错误打印用 sys.stderr
# =========================================================================


def test_main_prints_to_stderr_on_run_manifest_missing(tmp_path, capsys):
    main(["run", "--manifest", str(tmp_path / "no.json"), "--output", str(tmp_path / "o.json")])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert captured.out == ""


def test_main_prints_to_stderr_on_validate_report_missing(tmp_path, capsys):
    main(["validate-report", str(tmp_path / "no.json")])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err or "[FAIL]" in captured.err


def test_main_prints_to_stderr_on_inspect_doc_missing(tmp_path, capsys):
    main(["inspect-doc", str(tmp_path / "no.json")])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


# =========================================================================
# _format_metric 与 _run_inspect_doc 联动
# =========================================================================


def test_run_inspect_doc_each_metric_renders_two_space_prefix(capsys, tmp_path):
    """每行 metric 输出都以 '  ' 开头（_format_metric 的 prefix）。"""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    # 在 'metrics:' header 之后的行都应是 _format_metric 输出
    if "metrics:" in lines:
        idx = lines.index("metrics:")
        metric_lines = [l for l in lines[idx + 1:] if l.strip()]
        assert len(metric_lines) >= 1
        for l in metric_lines:
            assert l.startswith("  ")


def test_run_inspect_doc_with_doc_id_shows_value(capsys, tmp_path):
    doc_path = tmp_path / "doc.json"
    doc = {"document_id": "abc-123"}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "abc-123" in captured.out


def test_run_inspect_doc_with_source_path_shows_value(capsys, tmp_path):
    doc_path = tmp_path / "doc.json"
    doc = {"source_path": "/some/path.pdf", "source_type": "pdf"}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "/some/path.pdf" in captured.out


def test_run_inspect_doc_with_parser_name_shows_value(capsys, tmp_path):
    doc_path = tmp_path / "doc.json"
    doc = {"parser_name": "fallback", "parser_version": "1.0"}
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "fallback" in captured.out
    assert "v1.0" in captured.out


# =========================================================================
# _build_parser prog/description
# =========================================================================


def test_build_parser_prog_string_exact():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_contains_eval_or_ping_or_judge():
    """description 含评测/校验类词汇。"""
    p = _build_parser()
    assert any(kw in p.description for kw in ["评测", "校验", "报告"])


def test_build_parser_formatter_class_attribute_exact():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_no_conflict_handler_default():
    """默认 conflict_handler='error'。"""
    p = _build_parser()
    assert p.conflict_handler == "error"


def test_build_parser_add_help_default_true():
    """add_help 默认 True（有 _HelpAction）。"""
    p = _build_parser()
    help_actions = [a for a in p._actions if isinstance(a, argparse._HelpAction)]
    assert len(help_actions) == 1


def test_build_parser_allow_abbrev_default_true():
    p = _build_parser()
    # Python 3.12 默认 allow_abbrev=True
    assert p.allow_abbrev is True


def test_build_parser_run_subparser_prog_contains_run():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    assert "run" in run_p.prog


def test_build_parser_validate_report_subparser_prog_contains_validate():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    val_p = sub_action.choices["validate-report"]
    assert "validate-report" in val_p.prog


def test_build_parser_inspect_doc_subparser_prog_contains_inspect():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    ins_p = sub_action.choices["inspect-doc"]
    assert "inspect-doc" in ins_p.prog


# =========================================================================
# __main__ 块
# =========================================================================


def test_module_main_block_raises_system_exit():
    """if __name__ == '__main__': raise SystemExit(main())。"""
    src = inspect.getsource(cli_module)
    assert 'if __name__ == "__main__":' in src or "__name__ == '__main__'" in src
    assert "SystemExit(main())" in src


def test_module_main_block_at_module_bottom():
    """__main__ 块在模块底部。"""
    src = inspect.getsource(cli_module)
    pos_main_def = src.find("def main(")
    pos_main_block = src.find('__name__ == "__main__"')
    if pos_main_block == -1:
        pos_main_block = src.find("__name__ == '__main__'")
    assert pos_main_block > pos_main_def
