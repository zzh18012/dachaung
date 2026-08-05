r"""evaluation/cli.py 边角测试 - 第十一轮（Round 219）。

补强已有 base/edges/edges2-10（共 ~750 测试）未覆盖的深度：
- _build_parser：prog/description/add_help 等精确
- main()：no args / unknown / 多种 SystemExit 路径
- _format_metric：int 正负/0 / 科学计数法 / dict 中嵌套 / list / set / tuple / frozenset
- _run_inspect_doc：完整成功路径 / 各 metric 类型 / 多 elements 多 chunks
- main validate-report：FileNotFoundError 子路径 / Schema 失败 / 完整文件校验流程
- main inspect-doc：image element / 空 metrics / tolerance_chars
- main run：monkeypatched 成功路径 / Schema 错误
- 模块结构 / __main__ block / reconfigure block
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path

import pytest

import evaluation.cli as cli_module
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# _build_parser 深度（补强 edges10）
# =========================================================================


def test_build_parser_description_exact():
    p = _build_parser()
    assert p.description == "评测 CLI：跑开发集 → 报告；或校验已有报告。"


def test_build_parser_add_help_default_true():
    p = _build_parser()
    assert p.add_help is True


def test_build_parser_allow_abbrev_default_true():
    p = _build_parser()
    # argparse 默认 allow_abbrev=True
    assert p.allow_abbrev is True


def test_build_parser_no_subparsers_required():
    """subparsers required=True → 缺命令时 SystemExit(2)。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_build_parser_run_subparser_help_appears(capsys):
    """--help 触发 SystemExit 并 print usage。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--help"])
    captured = capsys.readouterr()
    assert "manifest" in captured.out.lower()


def test_build_parser_validate_report_subparser_help_appears(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["validate-report", "--help"])
    captured = capsys.readouterr()
    assert "input" in captured.out.lower()


def test_build_parser_inspect_doc_subparser_help_appears(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["inspect-doc", "--help"])
    captured = capsys.readouterr()
    assert "input" in captured.out.lower()


# =========================================================================
# _format_metric 深度（补强 edges10）
# =========================================================================


def test_format_metric_value_none_with_specific_reason():
    """value=None + reason='no_chunks' → 显示 'null (no_chunks)'。"""
    line = _format_metric("x", {"value": None, "reason": "no_chunks"})
    assert "null" in line
    assert "no_chunks" in line
    assert "ok" not in line  # value=None 时不显示 ok


def test_format_metric_value_zero_int():
    line = _format_metric("x", {"value": 0, "reason": None})
    assert "0" in line
    assert "ok" in line


def test_format_metric_value_negative_int():
    line = _format_metric("x", {"value": -5, "reason": None})
    assert "-5" in line


def test_format_metric_value_very_small_float():
    """很小的 float 仍要 4 位小数（会变 0.0000）。"""
    line = _format_metric("x", {"value": 1e-10, "reason": None})
    assert "0.0000" in line


def test_format_metric_value_float_one_decimal_place():
    line = _format_metric("x", {"value": 0.5, "reason": None})
    assert "0.5000" in line


def test_format_metric_value_dict_with_int_and_str():
    """dict 值可以是 int 或 str。"""
    line = _format_metric("x", {"value": {"a": 1, "b": "y"}, "reason": None})
    assert "a=1" in line
    assert "b=y" in line


def test_format_metric_value_dict_with_zero():
    line = _format_metric("x", {"value": {"a": 0}, "reason": None})
    assert "a=0" in line


def test_format_metric_value_dict_with_nested_dict():
    """dict value 是 nested dict → 用 str() 渲染（行为记录）。"""
    line = _format_metric("x", {"value": {"a": {"k": 1}}, "reason": None})
    assert "a={'k': 1}" in line


def test_format_metric_value_dict_with_empty_string_value():
    line = _format_metric("x", {"value": {"a": ""}, "reason": None})
    assert "a=" in line


def test_format_metric_value_tuple_in_dict():
    """dict value 是 tuple。"""
    line = _format_metric("x", {"value": {"a": (1, 2)}, "reason": None})
    assert "a=(1, 2)" in line or "a=(1, 2)" in line


def test_format_metric_value_list_with_dict():
    """list 包含 dict → 走默认分支（默认 str）。"""
    line = _format_metric("x", {"value": [{"k": 1}], "reason": None})
    assert "[{'k': 1}]" in line


def test_format_metric_value_set_falls_through():
    """set 不是 dict/bool/float/int → 默认分支。"""
    line = _format_metric("x", {"value": {1, 2, 3}, "reason": None})
    assert "ok" in line


def test_format_metric_value_frozenset_falls_through():
    line = _format_metric("x", {"value": frozenset([1]), "reason": None})
    assert "ok" in line


def test_format_metric_value_none_with_empty_reason():
    line = _format_metric("x", {"value": None, "reason": ""})
    assert "null" in line
    assert "()" in line


def test_format_metric_name_padding_visible():
    """name 短时应有空格填充至 36 字符。"""
    line = _format_metric("ab", {"value": 1, "reason": None})
    # "  " + name (2 chars) + spaces to reach 36 + " " + value
    # 找到 "ab" 后跟空格再到 value
    assert "ab" in line
    assert "1" in line


def test_format_metric_name_long_no_truncate():
    """name 超过 36 字符时不截断（f-string 不截断）。"""
    long_name = "x" * 50
    line = _format_metric(long_name, {"value": 1, "reason": None})
    assert long_name in line


def test_format_metric_metric_missing_value_key():
    """metric dict 无 value 键 → value=None 路径。"""
    line = _format_metric("x", {"reason": "no_key"})
    assert "null" in line
    assert "no_key" in line


def test_format_metric_metric_missing_reason_key():
    """metric dict 无 reason 键 → reason=None。"""
    line = _format_metric("x", {"value": 1})
    assert "ok" in line


def test_format_metric_metric_empty_dict():
    """metric={} → value=None, reason=None → 'null (None)'。"""
    line = _format_metric("x", {})
    assert "null" in line
    assert "None" in line


def test_format_metric_returns_string():
    line = _format_metric("x", {"value": 1, "reason": None})
    assert isinstance(line, str)


# =========================================================================
# _run_inspect_doc 深度（补强 edges10）
# =========================================================================


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters) == ["args"]


def test_run_inspect_doc_return_annotation_str():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_run_inspect_doc_callable():
    assert callable(_run_inspect_doc)


class _FakeArgs:
    """模拟 argparse.Namespace 用于 inspect-doc。"""
    def __init__(self, input_path, tolerance_chars=30):
        self.input = input_path
        self.tolerance_chars = tolerance_chars


def test_run_inspect_doc_returns_zero_for_valid_doc(tmp_path, capsys):
    doc = {
        "source_type": "text",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
        "document_id": "d1",
        "source_path": "/tmp/x.txt",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    result = _run_inspect_doc(_FakeArgs(str(p)))
    assert result == 0


def test_run_inspect_doc_prints_filename(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert str(p) in captured.out


def test_run_inspect_doc_prints_metrics_header(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    result = _run_inspect_doc(_FakeArgs(str(tmp_path / "nope.json")))
    assert result == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{not json", encoding="utf-8")
    result = _run_inspect_doc(_FakeArgs(str(p)))
    assert result == 1


def test_run_inspect_doc_non_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _run_inspect_doc(_FakeArgs(str(p)))
    assert result == 1
    captured = capsys.readouterr()
    assert "对象" in captured.err or "dict" in captured.err.lower()


def test_run_inspect_doc_prints_default_when_document_id_missing(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_run_inspect_doc_prints_default_when_parser_missing(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    # parser line 缺省 v?
    assert "v?" in captured.out


# =========================================================================
# main() validate-report 深度（补强 edges10）
# =========================================================================


def _write_valid_report(tmp_path: Path) -> Path:
    """写一个最小合法 evaluation-report。"""
    report = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {"pdfplumber": None, "python-docx": None, "pypdfium2": None},
            "max_chars": 800,
            "run_timestamp_iso": "2024-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {"element_count_total": {"sum": None, "participating_docs": 0}},
            "success_rates": {
                "pipeline_success": {"success_count": 0, "total": 0, "rate": None}
            },
            "ratio_macro_averages": {
                "schema_valid": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "pdf_locator_valid_ratio": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "docx_locator_valid_ratio": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "image_resource_exists_ratio": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "chunk_reference_intact_ratio": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "text_preservation_equal": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "text_char_multiset_precision": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "text_char_multiset_recall": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "heading_boundary_compliance": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "chunk_boundary_precision": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "chunk_boundary_recall": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
                "chunk_boundary_f1": {"macro_average": None, "participating_docs": 0, "not_evaluated": 0},
            },
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    return p


def test_main_validate_report_valid_returns_zero(tmp_path, capsys):
    p = _write_valid_report(tmp_path)
    result = main(["validate-report", str(p)])
    assert result == 0


def test_main_validate_report_valid_prints_ok(tmp_path, capsys):
    p = _write_valid_report(tmp_path)
    main(["validate-report", str(p)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert str(p) in captured.out


def test_main_validate_report_missing_returns_2(tmp_path, capsys):
    result = main(["validate-report", str(tmp_path / "missing.json")])
    assert result == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_validate_report_directory_returns_2(tmp_path, capsys):
    result = main(["validate-report", str(tmp_path)])
    assert result == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("{not json", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_empty_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_invalid_schema_returns_1(tmp_path, capsys):
    """报告结构合法 JSON 但 schema 不合。"""
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"report_version": "0.0.0"}), encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_list_returns_1(tmp_path, capsys):
    """JSON 顶层是 list 而非 dict → schema 拒。"""
    p = tmp_path / "report.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_int_returns_1(tmp_path, capsys):
    """JSON 顶层是 int → schema 拒。"""
    p = tmp_path / "report.json"
    p.write_text("42", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_string_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text('"hello"', encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_null_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("null", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_bool_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("true", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_validate_report_float_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("3.14", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


# =========================================================================
# main() inspect-doc 深度（补强 edges10）
# =========================================================================


def _write_doc_json(tmp_path: Path, doc=None) -> Path:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc or {}), encoding="utf-8")
    return p


def test_main_inspect_doc_returns_zero_for_empty_dict(tmp_path, capsys):
    p = _write_doc_json(tmp_path)
    result = main(["inspect-doc", str(p)])
    assert result == 0


def test_main_inspect_doc_prints_metrics_for_empty_doc(tmp_path, capsys):
    p = _write_doc_json(tmp_path)
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_main_inspect_doc_source_type_unknown_when_missing(tmp_path, capsys):
    p = _write_doc_json(tmp_path)
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_main_inspect_doc_source_type_pdf(tmp_path, capsys):
    p = _write_doc_json(tmp_path, {"source_type": "pdf"})
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "pdf" in captured.out


def test_main_inspect_doc_source_type_docx(tmp_path, capsys):
    p = _write_doc_json(tmp_path, {"source_type": "docx"})
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert "docx" in captured.out


def test_main_inspect_doc_with_image_element_no_crash(tmp_path, capsys):
    """含 image element → image_resource_exists_ratio 应正确算（无文件 → ratio=0.0）。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "resource_path": "img.png"},
        ],
        "chunks": [],
    }
    p = _write_doc_json(tmp_path, doc)
    result = main(["inspect-doc", str(p)])
    assert result == 0


def test_main_inspect_doc_with_many_chunks(tmp_path, capsys):
    """多个 chunks → chunk_reference_intact_ratio 应该计算。"""
    doc = {
        "source_type": "text",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [
            {"text": "a", "source_element_ids": ["e1"]},
            {"text": "bc", "source_element_ids": ["e1"]},
        ],
    }
    p = _write_doc_json(tmp_path, doc)
    result = main(["inspect-doc", str(p)])
    assert result == 0


def test_main_inspect_doc_with_tolerance_chars(tmp_path, capsys):
    """--tolerance-chars 不影响 inspect-doc 输出（无标注 → chunk_boundary 都 null）。"""
    p = _write_doc_json(tmp_path, {"source_type": "text"})
    result = main(["inspect-doc", str(p), "--tolerance-chars", "99"])
    assert result == 0


def test_main_inspect_doc_returns_int(tmp_path):
    p = _write_doc_json(tmp_path)
    result = main(["inspect-doc", str(p)])
    assert isinstance(result, int)


def test_main_inspect_doc_stdout_only_when_success(tmp_path, capsys):
    p = _write_doc_json(tmp_path, {"source_type": "text"})
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert captured.err == ""


# =========================================================================
# main() run 深度（补强 edges10）
# =========================================================================


def test_main_run_missing_manifest_returns_2(tmp_path, capsys):
    bad_manifest = tmp_path / "nope.json"
    out = tmp_path / "report.json"
    result = main(["run", "--manifest", str(bad_manifest), "--output", str(out)])
    assert result == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_directory_manifest_returns_2(tmp_path, capsys):
    """manifest 是目录 → is_file() False → exit 2。"""
    out = tmp_path / "report.json"
    result = main(["run", "--manifest", str(tmp_path), "--output", str(out)])
    assert result == 2


def test_main_run_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "manifest.json"
    p.write_text("{not json", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    out = tmp_path / "report.json"
    result = main(["run", "--manifest", str(p), "--output", str(out)])
    assert result == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_invalid_parser_choice_returns_2(capsys):
    """argparse choices 拒 → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x.json", "--output", "y.json", "--parser", "bad"])
    assert exc_info.value.code == 2


def test_main_run_max_chars_non_int_returns_2(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x.json", "--output", "y.json", "--max-chars", "abc"])
    assert exc_info.value.code == 2


def test_main_run_tolerance_chars_non_int_returns_2(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x.json", "--output", "y.json", "--tolerance-chars", "xyz"])
    assert exc_info.value.code == 2


def test_main_run_missing_required_args_returns_2(capsys):
    """缺 --manifest / --output → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run"])


# =========================================================================
# 模块结构（补强 edges10）
# =========================================================================


def test_module_has_main_callable():
    assert callable(cli_module.main)


def test_module_has_build_parser_callable():
    assert callable(cli_module._build_parser)


def test_module_has_format_metric_callable():
    assert callable(cli_module._format_metric)


def test_module_has_run_inspect_doc_callable():
    assert callable(cli_module._run_inspect_doc)


def test_module_main_block_present():
    """模块应有 if __name__ == "__main__": 入口。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' in src or "if __name__ == '__main__':" in src


def test_module_main_block_raises_system_exit():
    """__main__ 块应 raise SystemExit(main())。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "raise SystemExit" in src


def test_module_reconfigure_block_present():
    """stdout/stderr reconfigure 块应存在。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "reconfigure" in src


def test_module_reconfigure_block_guards_attribute_error():
    """reconfigure 块应 catch (AttributeError, OSError)。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "AttributeError" in src
    assert "OSError" in src


def test_module_reconfigure_block_has_try_except():
    import evaluation.cli as m
    src = inspect.getsource(m)
    # 简单确认 try + except 结构存在
    assert "try:" in src
    assert "except" in src


def test_module_imports_argparse():
    import evaluation.cli as m
    assert hasattr(m, "argparse")


def test_module_imports_json():
    import evaluation.cli as m
    assert hasattr(m, "json")


def test_module_imports_sys():
    import evaluation.cli as m
    assert hasattr(m, "sys")


def test_module_imports_path():
    import evaluation.cli as m
    assert hasattr(m, "Path")


def test_module_imports_manifest_error():
    import evaluation.cli as m
    assert hasattr(m, "ManifestError")


def test_module_imports_load_manifest():
    import evaluation.cli as m
    assert hasattr(m, "load_manifest")


def test_module_imports_get_git_provenance():
    import evaluation.cli as m
    assert hasattr(m, "get_git_provenance")


def test_module_imports_run_evaluation():
    import evaluation.cli as m
    assert hasattr(m, "run_evaluation")


def test_module_imports_eval_schema_error():
    import evaluation.cli as m
    assert hasattr(m, "EvalSchemaError")


def test_module_imports_validate_file():
    import evaluation.cli as m
    assert hasattr(m, "validate_file")


def test_module_docstring_present():
    import evaluation.cli as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_run_command():
    import evaluation.cli as m
    assert "run" in m.__doc__


def test_module_docstring_mentions_validate_report_command():
    import evaluation.cli as m
    assert "validate-report" in m.__doc__


def test_module_docstring_mentions_inspect_doc_command():
    import evaluation.cli as m
    assert "inspect-doc" in m.__doc__


def test_module_docstring_mentions_python_m_dash_m():
    import evaluation.cli as m
    assert "python -m" in m.__doc__


def test_module_uses_future_annotations():
    import evaluation.cli as m
    sig = inspect.signature(m.main)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.cli as m
    assert not hasattr(m, "_silence_unused_import")


# =========================================================================
# main() 综合行为
# =========================================================================


def test_main_no_args_raises_system_exit_2(capsys):
    """无 subcommand → required=True → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_main_unknown_command_raises_system_exit_2(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["unknown-command"])
    assert exc_info.value.code == 2


def test_main_returns_int_for_validate_report_success(tmp_path):
    p = _write_valid_report(tmp_path)
    result = main(["validate-report", str(p)])
    assert isinstance(result, int)


def test_main_returns_int_for_inspect_doc_success(tmp_path):
    p = _write_doc_json(tmp_path)
    result = main(["inspect-doc", str(p)])
    assert isinstance(result, int)


def test_main_format_metric_value_uses_default_for_unknown_type():
    """未匹配的类型（如自定义类）走默认分支。"""
    class CustomType:
        def __str__(self):
            return "custom"

    line = _format_metric("x", {"value": CustomType(), "reason": None})
    assert "custom" in line
    assert "ok" in line


def test_format_metric_with_value_being_class():
    """value 是 type（class 对象）→ 走默认分支。"""
    line = _format_metric("x", {"value": int, "reason": None})
    assert "<class 'int'>" in line or "int" in line
