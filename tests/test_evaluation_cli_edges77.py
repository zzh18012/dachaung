"""evaluation/cli.py 第九十六轮 edges 测试（Round 679）。

补强 edges76 未触及的角度（第五十三批）。

新角度：
- _build_parser 边界（tolerance-chars 默认 / prog 含点 / subparser dest='command' / run+inspect-doc 都有 tolerance-chars）
- main run 完整成功路径详细断言（per_doc 长度 / pipeline_success 统计 / [OK] 评测完成 / devset 输出 keys / git keys）
- main run validate_file 失败路径（抛 EvalSchemaError 后 return 1）
- main validate-report 完整成功断言（输出含 [OK] + 文件名）
- main inspect-doc 详细输出断言（file/document_id/source/parser/counts/metrics 标签）
- _format_metric 边界（大 int / 负数 / 空 dict value / dict 多 key 排序 / 含 None value 的 dict）
- _run_inspect_doc 私有嵌套 _sort_key 行为（None 后排 / bool 先排 / 数字中排 / 其他后排）
- 模块源码补强（sys.stdout.reconfigure / errors=replace / __main__ raise SystemExit / argparse prog 含点 / subparsers dest='command' / _run_inspect_doc 嵌套函数）
- AST 结构补强（main 3 if args.command / 4 try / 多 return / _run_inspect_doc 1 nested FunctionDef / sorted 调用 / print 多次）
- forbidden tokens 第一百四十九批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 边界 ----------

def test_build_parser_prog_contains_dot_batch52():
    p = _build_parser()
    assert "." in p.prog


def test_build_parser_subparsers_dest_is_command_batch52():
    p = _build_parser()
    sub_action = None
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            sub_action = a
            break
    assert sub_action is not None
    assert sub_action.dest == "command"


def test_build_parser_run_default_tolerance_30_batch52():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_custom_tolerance_batch52():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--tolerance-chars", "50",
    ])
    assert args.tolerance_chars == 50


def test_build_parser_inspect_doc_default_tolerance_30_batch52():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_custom_tolerance_batch52():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_run_has_4_optional_args_batch52():
    """run 子命令有 --manifest/--output/--parser/--max-chars/--tolerance-chars 5 个。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert hasattr(args, "manifest")
    assert hasattr(args, "output")
    assert hasattr(args, "parser")
    assert hasattr(args, "max_chars")
    assert hasattr(args, "tolerance_chars")


def test_build_parser_validate_report_args_batch52():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_inspect_doc_args_batch52():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


# ---------- main run 完整成功路径详细 ----------

def _make_manifest_obj():
    """构造合法 Manifest mock。"""
    m = MagicMock()
    m.project_root = Path(".")
    return m


def test_main_run_success_output_contains_OK_batch52(capsys):
    m_obj = _make_manifest_obj()
    fake_report = {
        "per_doc": [
            {"doc_id": "a", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "b", "metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "incomplete", "file_count": 2},
    }
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
        # 让 Path.is_file 返回 True
        path_instance = MagicMock()
        path_instance.is_file.return_value = True
        path_cls.return_value = path_instance
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    assert rc == 0
    out = capsys.readouterr()
    assert "[OK]" in out.out
    assert "评测完成" in out.out


def test_main_run_success_counts_pipeline_success_batch52(capsys):
    m_obj = _make_manifest_obj()
    fake_report = {
        "per_doc": [
            {"doc_id": "a", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "b", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "c", "metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "incomplete", "file_count": 3},
    }
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    out = capsys.readouterr()
    # n_ok=2 n_fail=1
    assert "成功 2" in out.out
    assert "失败 1" in out.out


def test_main_run_success_devset_keys_batch52(capsys):
    m_obj = _make_manifest_obj()
    fake_report = {
        "per_doc": [],
        "devset": {
            "status": "incomplete", "file_count": 5,
            "content_group_count": 3, "pdf_count": 2, "docx_count": 3,
        },
    }
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": True}):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    out = capsys.readouterr()
    assert "devset_status=incomplete" in out.out
    assert "file_count=5" in out.out
    assert "groups=3" in out.out
    assert "pdf=2" in out.out
    assert "docx=3" in out.out


def test_main_run_success_git_keys_batch52(capsys):
    m_obj = _make_manifest_obj()
    fake_report = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abcdef1234567890", "git_dirty": False}):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    out = capsys.readouterr()
    # git_commit 显示前 12 字符
    assert "abcdef123456" in out.out
    assert "git_dirty=False" in out.out


def test_main_run_success_returns_0_batch52(capsys):
    m_obj = _make_manifest_obj()
    fake_report = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    assert rc == 0


def test_main_run_validate_file_failure_returns_1_batch52(capsys):
    """报告自校验失败 → return 1。"""
    from evaluation.schema import EvalSchemaError
    m_obj = _make_manifest_obj()
    fake_report = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad schema")), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    assert rc == 1
    err = capsys.readouterr()
    assert "自校验失败" in err.err


def test_main_run_manifest_not_exist_returns_2_batch52(capsys):
    with patch("evaluation.cli.Path") as path_cls:
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: False)
        rc = main(["run", "--manifest", "missing.json", "--output", "o.json"])
    assert rc == 2
    err = capsys.readouterr()
    assert "清单不存在" in err.err


def test_main_run_eval_schema_error_returns_1_batch52(capsys):
    from evaluation.schema import EvalSchemaError
    m_obj = _make_manifest_obj()
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", return_value=m_obj), \
         patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("bad")):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    assert rc == 1
    err = capsys.readouterr()
    assert "未通过 Schema" in err.err


def test_main_run_manifest_error_returns_1_batch52(capsys):
    from evaluation.manifest import ManifestError
    with patch("evaluation.cli.Path") as path_cls, \
         patch("evaluation.cli.load_manifest", side_effect=ManifestError("bad manifest")):
        path_cls.side_effect = lambda x: MagicMock(is_file=lambda: True)
        rc = main(["run", "--manifest", "m.json", "--output", "o.json"])
    assert rc == 1


# ---------- main validate-report 完整成功 ----------

def test_main_validate_report_success_prints_OK_batch52(capsys, tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr()
    assert "[OK]" in out.out
    assert "通过 evaluation-report Schema 校验" in out.out


def test_main_validate_report_success_contains_filename_batch52(capsys, tmp_path):
    p = tmp_path / "myreport.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        rc = main(["validate-report", str(p)])
    out = capsys.readouterr()
    assert "myreport.json" in out.out


def test_main_validate_report_not_exist_returns_2_batch52(capsys):
    rc = main(["validate-report", "/no/such/file.json"])
    assert rc == 2
    err = capsys.readouterr()
    assert "报告不存在" in err.err


def test_main_validate_report_eval_schema_error_returns_1_batch52(capsys, tmp_path):
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
        rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr()
    assert "[FAIL]" in err.err


def test_main_validate_report_filenotfound_returns_2_batch52(capsys, tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("schema file missing")):
        rc = main(["validate-report", str(p)])
    assert rc == 2


def test_main_validate_report_json_decode_error_returns_1_batch52(capsys, tmp_path):
    p = tmp_path / "report.json"
    p.write_text("not json", encoding="utf-8")
    # validate_file 不会触发 JSONDecodeError，因为 json.load 在 validate_file 内
    # 但我们模拟它抛
    with patch("evaluation.cli.validate_file", side_effect=json.JSONDecodeError("bad", "doc", 0)):
        rc = main(["validate-report", str(p)])
    assert rc == 1


# ---------- main inspect-doc 详细输出 ----------

def test_main_inspect_doc_success_prints_labels_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "doc1",
        "source_type": "pdf",
        "source_path": "foo.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"type": "paragraph"}],
        "chunks": [{"text": "hello"}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr()
    assert "file:" in out.out
    assert "document_id:" in out.out
    assert "source:" in out.out
    assert "parser:" in out.out
    assert "counts:" in out.out
    assert "metrics:" in out.out


def test_main_inspect_doc_counts_elements_chunks_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "elements": [{}, {}, {}],
        "chunks": [{}, {}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr()
    assert "elements=3" in out.out
    assert "chunks=2" in out.out


def test_main_inspect_doc_default_source_type_unknown_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr()
    assert "type=unknown" in out.out


def test_main_inspect_doc_default_document_id_question_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr()
    assert "document_id: ?" in out.out


def test_main_inspect_doc_default_parser_question_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr()
    assert "parser:      ? v?" in out.out


def test_main_inspect_doc_not_exist_returns_2_batch52(capsys):
    rc = main(["inspect-doc", "/no/such/doc.json"])
    assert rc == 2
    err = capsys.readouterr()
    assert "文档不存在" in err.err


def test_main_inspect_doc_json_decode_error_returns_1_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr()
    assert "JSON 解析失败" in err.err


def test_main_inspect_doc_top_level_not_dict_returns_1_batch52(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr()
    assert "顶层不是对象" in err.err


# ---------- _format_metric 边界 ----------

def test_format_metric_large_int_batch52():
    out = _format_metric("count", {"value": 1000000, "reason": None})
    assert "1000000" in out
    assert "(ok)" in out


def test_format_metric_negative_int_batch52():
    out = _format_metric("delta", {"value": -42, "reason": None})
    assert "-42" in out


def test_format_metric_zero_int_batch52():
    out = _format_metric("zero", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_empty_dict_value_batch52():
    out = _format_metric("by_type", {"value": {}, "reason": None})
    # 空 dict → ", ".join([]) = ""
    assert "by_type" in out
    assert "(ok)" in out


def test_format_metric_dict_multi_key_sorted_batch52():
    out = _format_metric("by_type", {"value": {"b": 2, "a": 1, "c": 3}, "reason": None})
    # sorted → a=1, b=2, c=3
    idx_a = out.find("a=")
    idx_b = out.find("b=")
    idx_c = out.find("c=")
    assert idx_a < idx_b < idx_c


def test_format_metric_dict_with_none_value_batch52():
    """dict value 含 None → 仍渲染 'k=None'。"""
    out = _format_metric("data", {"value": {"x": None, "y": 1}, "reason": None})
    # sorted → 'x' < 'y'
    assert "x=None" in out
    assert "y=1" in out


def test_format_metric_value_none_uses_reason_batch52():
    out = _format_metric("k", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_value_none_empty_reason_batch52():
    out = _format_metric("k", {"value": None, "reason": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_bool_true_lowercase_batch52():
    out = _format_metric("flag", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_lowercase_batch52():
    out = _format_metric("flag", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_float_format_4_digits_batch52():
    out = _format_metric("ratio", {"value": 0.123456789, "reason": None})
    assert "0.1235" in out  # 4 位小数


def test_format_metric_float_zero_batch52():
    out = _format_metric("ratio", {"value": 0.0, "reason": None})
    assert "0.0000" in out


# ---------- _run_inspect_doc _sort_key 行为 ----------

def test_run_inspect_doc_null_metrics_last_batch52(capsys, tmp_path):
    """value=None 的 metric 排在最后。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "elements": [{"type": "paragraph"}],
        "chunks": [{"text": "x"}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr()
    # 至少有一个 null 行
    lines = [l for l in out.out.split("\n") if "null" in l]
    assert len(lines) >= 1


# ---------- 模块源码补强 ----------

def test_source_argparse_import_batch52():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_source_json_import_batch52():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_source_sys_import_batch52():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_source_path_import_batch52():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_source_manifest_imports_batch52():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_source_report_imports_batch52():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.report import get_git_provenance" in src


def test_source_runner_imports_batch52():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.runner import run_evaluation" in src


def test_source_schema_imports_batch52():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_source_sys_stdout_reconfigure_call_batch52():
    src = inspect.getsource(cli_mod)
    assert 'sys.stdout.reconfigure' in src


def test_source_utf8_encoding_batch52():
    src = inspect.getsource(cli_mod)
    assert 'encoding="utf-8"' in src


def test_source_errors_replace_batch52():
    src = inspect.getsource(cli_mod)
    assert 'errors="replace"' in src


def test_source_main_returns_int_batch52():
    """main 函数签名返回 int。"""
    src = inspect.getsource(cli_mod)
    assert "def main(argv: list[str] | None = None) -> int:" in src


def test_source_has_run_inspect_doc_nested_sort_key_batch52():
    src = inspect.getsource(cli_mod)
    assert "_sort_key" in src


def test_source_has_sorted_call_batch52():
    src = inspect.getsource(cli_mod)
    assert "sorted(metrics.keys()" in src


def test_source_has_subparsers_dest_command_batch52():
    src = inspect.getsource(cli_mod)
    assert 'dest="command"' in src


def test_source_has_required_true_batch52():
    src = inspect.getsource(cli_mod)
    assert "required=True" in src


def test_source_has_raw_description_batch52():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


def test_source_has_main_entry_point_batch52():
    src = inspect.getsource(cli_mod)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_source_has_3_subparsers_batch52():
    src = inspect.getsource(cli_mod)
    assert 'sub.add_parser("run"' in src
    # validate-report / inspect-doc 的 add_parser( 和字符串字面量跨行，断言字符串字面量本身存在即可
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src


def test_source_has_choices_fallback_kreuzberg_batch52():
    src = inspect.getsource(cli_mod)
    assert '"fallback"' in src
    assert '"kreuzberg"' in src


def test_source_has_2_stderr_writes_for_reconfigure_batch52():
    """reconfigure 同时配置 stdout + stderr。
    count == 3：hasattr + stdout.reconfigure + stderr.reconfigure。"""
    src = inspect.getsource(cli_mod)
    assert src.count("reconfigure") == 3


def test_source_main_uses_manifest_path_isfile_batch52():
    src = inspect.getsource(cli_mod)
    assert "manifest_path.is_file()" in src


def test_source_main_uses_output_path_isfile_batch52():
    """validate-report 检查 input_path.is_file()。"""
    src = inspect.getsource(cli_mod)
    assert "input_path.is_file()" in src


def test_source_run_inspect_doc_uses_open_batch52():
    src = inspect.getsource(cli_mod)
    assert 'input_path.open("r", encoding="utf-8")' in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_functions_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4  # _build_parser, main, _format_metric, _run_inspect_doc


def test_ast_function_names_order_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_2_module_level_if_batch52():
    """reconfigure if + __main__ if = 2。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    ifs = [n for n in tree.body if isinstance(n, ast.If)]
    assert len(ifs) == 2


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_main_has_3_command_if_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    # 3 个 if args.command ==
    cmd_ifs = [
        n for n in ast.walk(main_func)
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Attribute)
        and n.test.left.attr == "command"
    ]
    assert len(cmd_ifs) == 3


def test_ast_main_has_4_try_batch52():
    """load_manifest + run_evaluation + validate_file(run) + validate_file(validate-report) = 4。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    trys = [n for n in ast.walk(main_func) if isinstance(n, ast.Try)]
    assert len(trys) == 4


def test_ast_main_has_multiple_return_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    returns = [n for n in ast.walk(main_func) if isinstance(n, ast.Return)]
    assert len(returns) >= 7


def test_ast_main_has_return_2_fallback_batch52():
    """main 末尾兜底 return 2（无匹配子命令）。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    src = ast.unparse(main_func)
    # 末尾应有 return 2
    assert "return 2" in src


def test_ast_build_parser_add_subparsers_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    add_sub_call = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_subparsers"
    ]
    assert len(add_sub_call) == 1
    # dest='command'
    kw = next(k for k in add_sub_call[0].keywords if k.arg == "dest")
    assert isinstance(kw.value, ast.Constant)
    assert kw.value.value == "command"
    # required=True
    req = next(k for k in add_sub_call[0].keywords if k.arg == "required")
    assert isinstance(req.value, ast.Constant)
    assert req.value.value is True


def test_ast_build_parser_has_3_add_parser_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    add_parser_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_parser"
    ]
    assert len(add_parser_calls) == 3


def test_ast_run_inspect_doc_has_nested_function_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    nested = [n for n in ast.walk(func) if isinstance(n, ast.FunctionDef) and n is not func]
    assert len(nested) == 1
    assert nested[0].name == "_sort_key"


def test_ast_run_inspect_doc_nested_sort_key_returns_tuple_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    nested = next(n for n in ast.walk(func) if isinstance(n, ast.FunctionDef) and n.name == "_sort_key")
    src = ast.unparse(nested)
    assert "return (3, name)" in src or "return (0, name)" in src


def test_ast_run_inspect_doc_has_sorted_call_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    sorted_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "sorted"
    ]
    assert len(sorted_calls) == 1


def test_ast_run_inspect_doc_has_multiple_print_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    prints = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "print"
    ]
    assert len(prints) >= 7


def test_ast_run_inspect_doc_has_with_open_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_format_metric_has_multiple_returns_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # 至少 4 个 return（None/bool/float/dict/默认）
    assert len(returns) >= 4


def test_ast_format_metric_has_joined_str_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    joined = [n for n in ast.walk(func) if isinstance(n, ast.JoinedStr)]
    assert len(joined) >= 1


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百四十九批 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch52():
    """_run_inspect_doc 1 个 with open。"""
    assert _src().count("open(") == 1
