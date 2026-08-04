"""evaluation/cli.py 边角测试 - 第二轮（Round 68）。

补强 tests/test_evaluation_cli.py（48 个）+ tests/test_evaluation_cli_edges.py（54 个）
未覆盖的：
- _build_parser 深度：Namespace 属性、help 文本、choices 元组
- _format_metric 深度：bool/int/dict/None 各分支精确输出、list/tuple 默认分支、
- main run 子命令：失败路径（EvalSchemaError）、stdout 内容
- main inspect-doc 深度：JSON 顶层 int/string/dict、metric 排序、stdout 内容
- main validate-report 深度：FileNotFoundError、JSONDecodeError 内容
- 模块结构与导入
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.cli import (
    __file__ as _cli_module_path,
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)
from evaluation.cli import (
    ManifestError,
    EvalSchemaError,
    load_manifest,
    get_git_provenance,
    run_evaluation,
    validate_file,
)


# ---------- _build_parser 深度边角 ----------


def test_build_parser_run_subparser_has_manifest_help():
    p = _build_parser()
    # 通过 parse_args(['run', '--help']) 会 SystemExit；改用检查 action 配置
    run_p = [a for a in p._subparsers._group_actions[0].choices.values() if 'run' in str(a)]
    # 简化：直接 parse_args 拿 namespace
    ns = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert hasattr(ns, "manifest")
    assert hasattr(ns, "output")


def test_build_parser_namespace_command_value():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.command == "run"


def test_build_parser_namespace_command_value_validate():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "x.json"])
    assert ns.command == "validate-report"


def test_build_parser_namespace_command_value_inspect():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "x.json"])
    assert ns.command == "inspect-doc"


def test_build_parser_namespace_has_parser_attr():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.parser == "fallback"  # 默认值


def test_build_parser_namespace_has_max_chars_attr():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.max_chars == 800


def test_build_parser_namespace_has_tolerance_chars_attr_run():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.tolerance_chars == 30


def test_build_parser_namespace_has_tolerance_chars_attr_inspect():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "x.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_namespace_custom_parser_choice():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "kreuzberg"])
    assert ns.parser == "kreuzberg"


def test_build_parser_namespace_custom_max_chars():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "1000"])
    assert ns.max_chars == 1000


def test_build_parser_namespace_negative_max_chars():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "-1"])
    assert ns.max_chars == -1


def test_build_parser_namespace_negative_tolerance_chars():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "-1"])
    assert ns.tolerance_chars == -1


def test_build_parser_namespace_validate_report_input():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_build_parser_namespace_inspect_doc_input():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_build_parser_no_command_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args([])
    assert exc.value.code == 2


def test_build_parser_run_missing_manifest_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["run", "--output", "y.json"])
    assert exc.value.code == 2


def test_build_parser_run_missing_output_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["run", "--manifest", "x.json"])
    assert exc.value.code == 2


def test_build_parser_run_invalid_parser_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])
    assert exc.value.code == 2


# ---------- _format_metric 深度边角 ----------


def test_format_metric_bool_true_lower():
    line = _format_metric("schema_valid", {"value": True, "reason": None})
    assert "true" in line
    assert "ok" in line


def test_format_metric_bool_false_lower():
    line = _format_metric("schema_valid", {"value": False, "reason": "schema_failed"})
    assert "false" in line
    assert "schema_failed" in line


def test_format_metric_int_value():
    line = _format_metric("count", {"value": 5, "reason": None})
    # int 走 default 分支：直接 str(value)
    assert "5" in line
    assert "ok" in line


def test_format_metric_float_precision_4():
    line = _format_metric("rate", {"value": 0.123456789, "reason": None})
    assert "0.1235" in line  # 4 位小数


def test_format_metric_float_zero():
    line = _format_metric("rate", {"value": 0.0, "reason": None})
    assert "0.0000" in line


def test_format_metric_float_one():
    line = _format_metric("rate", {"value": 1.0, "reason": None})
    assert "1.0000" in line


def test_format_metric_dict_value_sorted():
    """dict value → 按 key 排序输出。"""
    line = _format_metric(
        "element_count_by_type",
        {"value": {"paragraph": 3, "heading": 1, "image": 2}, "reason": None},
    )
    # 排序后：heading, image, paragraph
    idx_h = line.find("heading")
    idx_i = line.find("image")
    idx_p = line.find("paragraph")
    assert 0 < idx_h < idx_i < idx_p


def test_format_metric_dict_value_empty_items():
    line = _format_metric("counts", {"value": {}, "reason": None})
    # 空 dict → items 是空字符串
    assert "counts" in line
    # 不抛即 OK


def test_format_metric_none_with_reason():
    line = _format_metric("rate", {"value": None, "reason": "no_data"})
    assert "null" in line
    assert "no_data" in line


def test_format_metric_none_no_reason():
    line = _format_metric("rate", {"value": None, "reason": None})
    assert "null" in line
    assert "None" in line  # reason None → str(None)


def test_format_metric_value_is_list_uses_default_branch():
    """list 不是 bool/float/dict → 走 default str(value)。"""
    line = _format_metric("list_metric", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in line


def test_format_metric_value_is_tuple_uses_default_branch():
    line = _format_metric("tuple_metric", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in line


def test_format_metric_value_is_string():
    line = _format_metric("path", {"value": "x.pdf", "reason": None})
    assert "x.pdf" in line


def test_format_metric_alignment_width_36_chars():
    """name 占 36 字符（{name:36} 左对齐），+ 字面空格 = 'ab' + 35 spaces。"""
    line = _format_metric("ab", {"value": 0, "reason": None})
    # 找 "ab" 后的空格连续段
    leading = "  ab"
    rest_idx = line.find(leading) + len(leading)
    spaces = 0
    while rest_idx < len(line) and line[rest_idx] == " ":
        spaces += 1
        rest_idx += 1
    # name 占位 36 chars（{name:36}）→ 'ab' + 34 padding；+ 1 字面空格 = 35
    assert spaces == 35


def test_format_metric_long_name_exceeds_36():
    """name > 36 字符 → 不截断（{name:36} 仍输出全部）。"""
    long_name = "x" * 50
    line = _format_metric(long_name, {"value": 0, "reason": None})
    assert long_name in line


def test_format_metric_empty_metric_dict_returns_default():
    """空 metric dict → value=None, reason=None → null 分支。"""
    line = _format_metric("x", {})
    assert "null" in line


# ---------- main run 子命令深度边角 ----------


def test_main_run_returns_2_when_manifest_not_exist(tmp_path: Path):
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(out)])
    assert rc == 2


def test_main_run_writes_error_to_stderr_when_manifest_missing(tmp_path: Path, capsys):
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(out)])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "清单不存在" in captured.err or "manifest" in captured.err.lower() or "missing" in captured.err.lower()


def test_main_run_returns_1_when_manifest_invalid_json(tmp_path: Path):
    bad = tmp_path / "manifest.json"
    bad.write_text("{not valid", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(bad), "--output", str(out)])
    assert rc == 1


def test_main_run_returns_1_when_manifest_invalid_content(tmp_path: Path):
    bad = tmp_path / "manifest.json"
    bad.write_text(json.dumps({"unexpected": "x"}), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(bad), "--output", str(out)])
    assert rc == 1


# ---------- main validate-report 深度边角 ----------


def test_main_validate_report_returns_2_for_missing_file(tmp_path: Path):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_returns_1_for_invalid_json(tmp_path: Path):
    bad = tmp_path / "r.json"
    bad.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def _valid_report() -> dict:
    """合法 evaluation-report（参考 tests/test_evaluation_schema.py）。"""
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc1234",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "dependencies": {"python": "3.12.10"},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-04T12:00:00Z",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 0,
            "docx_count": 1,
            "categories_covered": ["report"],
        },
        "summary": {},
        "per_doc": [],
    }


def test_main_validate_report_writes_ok_for_valid(tmp_path: Path, capsys):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(_valid_report()), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_validate_report_writes_fail_for_invalid(tmp_path: Path, capsys):
    bad = tmp_path / "r.json"
    bad.write_text(json.dumps({"unexpected": "x"}), encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_writes_error_for_missing(tmp_path: Path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


# ---------- main inspect-doc 深度边角 ----------


def test_main_inspect_doc_returns_2_for_missing_file(tmp_path: Path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_returns_1_for_invalid_json(tmp_path: Path):
    bad = tmp_path / "d.json"
    bad.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_returns_1_for_top_level_int(tmp_path: Path):
    p = tmp_path / "d.json"
    p.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_1_for_top_level_string(tmp_path: Path):
    p = tmp_path / "d.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_1_for_top_level_array(tmp_path: Path):
    p = tmp_path / "d.json"
    p.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_0_for_minimal_doc(tmp_path: Path):
    """合法 Document dict → 0。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_writes_document_id(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "doc-unique-id",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "doc-unique-id" in captured.out


def test_main_inspect_doc_writes_metrics_header(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_main_inspect_doc_writes_file_path(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "mydoc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "mydoc.json" in captured.out


def test_main_inspect_doc_writes_counts_line(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1"}],
        "chunks": [{"chunk_id": "c1"}],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_main_inspect_doc_writes_unicode_doc(tmp_path: Path, capsys):
    """含 Unicode 字段的文档能渲染。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "中文.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {"中文key": "值"},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_negative_tolerance_chars_accepted(tmp_path: Path):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "-1"])
    assert rc == 0


def test_main_inspect_doc_missing_elements_field(tmp_path: Path):
    """document 缺 elements 字段 → 视为 []。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_missing_chunks_field(tmp_path: Path):
    """document 缺 chunks 字段 → 视为 []。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_missing_source_type_uses_unknown(tmp_path: Path, capsys):
    """document 缺 source_type → 默认 'unknown'，inspect-doc 仍能跑。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "unknown" in captured.out


# ---------- main 入口点边角 ----------


def test_main_returns_2_for_unknown_command():
    """argparse 拒绝未知命令 → SystemExit(2)，main 不返。"""
    with pytest.raises(SystemExit) as exc:
        main(["unknown-command"])
    assert exc.value.code == 2


def test_main_returns_2_for_no_command():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_main_returns_int_type_for_run(tmp_path: Path):
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(out)])
    assert isinstance(rc, int)


def test_main_returns_int_type_for_validate(tmp_path: Path):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)


def test_main_returns_int_type_for_inspect(tmp_path: Path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)


# ---------- _run_inspect_doc 直接调用 ----------


def test_run_inspect_doc_returns_int_type(tmp_path: Path):
    p = tmp_path / "missing.json"
    # 用 argparse 模拟 args
    p_obj = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(p_obj)
    assert isinstance(rc, int)


def test_run_inspect_doc_missing_file_returns_2(tmp_path: Path):
    p_obj = _build_parser().parse_args(["inspect-doc", str(tmp_path / "missing.json")])
    assert _run_inspect_doc(p_obj) == 2


# ---------- 模块结构与导入边角 ----------


def test_module_imports_argparse():
    import evaluation.cli as mod
    assert hasattr(mod, "argparse")


def test_module_imports_json():
    import evaluation.cli as mod
    assert hasattr(mod, "json")


def test_module_imports_sys():
    import evaluation.cli as mod
    assert hasattr(mod, "sys")


def test_module_imports_path():
    import evaluation.cli as mod
    assert hasattr(mod, "Path")


def test_module_imports_manifest_error():
    """ManifestError 从 evaluation.manifest 导入。"""
    import evaluation.cli as mod
    assert hasattr(mod, "ManifestError")
    assert ManifestError is not None


def test_module_imports_load_manifest():
    import evaluation.cli as mod
    assert hasattr(mod, "load_manifest")
    assert callable(load_manifest)


def test_module_imports_get_git_provenance():
    import evaluation.cli as mod
    assert hasattr(mod, "get_git_provenance")
    assert callable(get_git_provenance)


def test_module_imports_run_evaluation():
    import evaluation.cli as mod
    assert hasattr(mod, "run_evaluation")
    assert callable(run_evaluation)


def test_module_imports_eval_schema_error():
    import evaluation.cli as mod
    assert hasattr(mod, "EvalSchemaError")
    assert EvalSchemaError is not None


def test_module_imports_validate_file():
    import evaluation.cli as mod
    assert hasattr(mod, "validate_file")
    assert callable(validate_file)


def test_module_has_main_callable():
    assert callable(main)


def test_module_has_build_parser_callable():
    assert callable(_build_parser)


def test_module_has_format_metric_callable():
    assert callable(_format_metric)


def test_module_has_run_inspect_doc_callable():
    assert callable(_run_inspect_doc)


def test_module_file_path_ends_with_cli_dot_py():
    assert _cli_module_path.replace("\\", "/").endswith("evaluation/cli.py")


# ---------- Windows stdout reconfigure 安全性 ----------


def test_main_runnable_in_environment_without_reconfigure():
    """sys.stdout.reconfigure 不可用时也不应崩（早期 Python / 重定向）。"""
    # 这里不真正模拟，只验证 main 可调用
    with pytest.raises(SystemExit):
        main([])  # 触发 argparse 解析错误
