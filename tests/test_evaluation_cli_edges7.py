r"""evaluation/cli.py 边角测试 - 第七轮（Round 174）。

补强已有 base/edges/edges2-6（共 571 测试）未覆盖的深度：
- _build_parser 各 subparser 参数精确集合
- _format_metric 各 value 类型分支（None/bool/float/dict/int/str/list）
- _run_inspect_doc 错误路径与 metric 排序
- main() 各退出码（含 sys.exit 路径）
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


class _FakeArgs:
    """模拟 argparse.Namespace 用于 _run_inspect_doc 直接调用。"""

    def __init__(self, input: str, tolerance_chars: int = 30):
        self.input = input
        self.tolerance_chars = tolerance_chars


# =========================================================================
# _build_parser 各 subparser 参数精确集合
# =========================================================================


def test_build_parser_run_subparser_args_exact():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    names = {a.dest for a in run_p._actions if a.dest not in ("help", "command")}
    assert names == {"manifest", "output", "parser", "max_chars", "tolerance_chars"}


def test_build_parser_validate_report_subparser_args_exact():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    val_p = sub_actions.choices["validate-report"]
    names = {a.dest for a in val_p._actions if a.dest not in ("help", "command")}
    assert names == {"input"}


def test_build_parser_inspect_doc_subparser_args_exact():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    ins_p = sub_actions.choices["inspect-doc"]
    names = {a.dest for a in ins_p._actions if a.dest not in ("help", "command")}
    assert names == {"input", "tolerance_chars"}


def test_build_parser_run_manifest_required():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    manifest_action = next(a for a in run_p._actions if a.dest == "manifest")
    assert manifest_action.required is True


def test_build_parser_run_output_required():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    output_action = next(a for a in run_p._actions if a.dest == "output")
    assert output_action.required is True


def test_build_parser_run_parser_not_required():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    parser_action = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_action.required is False


def test_build_parser_run_parser_choices():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    parser_action = next(a for a in run_p._actions if a.dest == "parser")
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_parser_default_fallback():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    parser_action = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_action.default == "fallback"


def test_build_parser_run_max_chars_type_int():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    max_chars_action = next(a for a in run_p._actions if a.dest == "max_chars")
    assert max_chars_action.type is int


def test_build_parser_run_max_chars_default_800():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    max_chars_action = next(a for a in run_p._actions if a.dest == "max_chars")
    assert max_chars_action.default == 800


def test_build_parser_run_tolerance_chars_default_30():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    run_p = sub_actions.choices["run"]
    tol_action = next(a for a in run_p._actions if a.dest == "tolerance_chars")
    assert tol_action.default == 30


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    ins_p = sub_actions.choices["inspect-doc"]
    tol_action = next(a for a in ins_p._actions if a.dest == "tolerance_chars")
    assert tol_action.default == 30


def test_build_parser_inspect_doc_tolerance_chars_type_int():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    ins_p = sub_actions.choices["inspect-doc"]
    tol_action = next(a for a in ins_p._actions if a.dest == "tolerance_chars")
    assert tol_action.type is int


def test_build_parser_subparsers_required_true():
    """add_subparsers(required=True)。"""
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    assert sub_actions.required is True


def test_build_parser_prog_value():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_present():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description or "CLI" in p.description


def test_build_parser_formatter_class_raw():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_three_subcommands():
    p = _build_parser()
    sub_actions = [a for a in p._subparsers._group_actions if hasattr(a, 'choices')][0]
    assert set(sub_actions.choices) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_returns_argument_parser():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


# =========================================================================
# _format_metric 各类型分支
# =========================================================================


def test_format_metric_int_value():
    """int 走 default 分支（不是 float / bool / dict / None）。"""
    out = _format_metric("count", {"value": 5})
    assert "5" in out


def test_format_metric_negative_int_value():
    out = _format_metric("delta", {"value": -3})
    assert "-3" in out


def test_format_metric_zero_int_value():
    out = _format_metric("zero", {"value": 0})
    assert "0" in out


def test_format_metric_zero_float_value():
    """0.0 走 float 分支（isinstance(0.0, float) → True）。"""
    out = _format_metric("ratio", {"value": 0.0})
    assert "0.0000" in out


def test_format_metric_float_precision_4_digits():
    out = _format_metric("m", {"value": 0.123456789})
    assert "0.1235" in out


def test_format_metric_negative_float():
    out = _format_metric("m", {"value": -0.5})
    assert "-0.5000" in out


def test_format_metric_string_value():
    out = _format_metric("name", {"value": "hello"})
    assert "hello" in out


def test_format_metric_list_value_falls_to_default():
    """list 不是 None/bool/float/dict → default 分支。"""
    out = _format_metric("items", {"value": [1, 2, 3]})
    assert "[1, 2, 3]" in out


def test_format_metric_empty_list_value():
    out = _format_metric("items", {"value": []})
    assert "[]" in out


def test_format_metric_dict_value_single_pair():
    out = _format_metric("counts", {"value": {"a": 1}})
    assert "a=1" in out


def test_format_metric_dict_value_multi_pairs_sorted():
    """dict value 时按 key 排序输出。"""
    out = _format_metric("counts", {"value": {"b": 2, "a": 1, "c": 3}})
    # 排序后：a=1, b=2, c=3
    idx_a = out.find("a=1")
    idx_b = out.find("b=2")
    idx_c = out.find("c=3")
    assert 0 <= idx_a < idx_b < idx_c


def test_format_metric_dict_value_with_reason():
    out = _format_metric("m", {"value": {"k": "v"}, "reason": "info"})
    assert "k=v" in out
    assert "info" in out


def test_format_metric_true_with_reason_kept():
    """bool True + 给 reason：用 reason（truthy），不回落 'ok'。"""
    out = _format_metric("m", {"value": True, "reason": "ignored"})
    assert "true" in out
    assert "ignored" in out


def test_format_metric_false_with_reason_kept():
    out = _format_metric("m", {"value": False, "reason": "ignored"})
    assert "false" in out
    assert "ignored" in out


def test_format_metric_float_with_reason_ignored():
    """float 时 reason 缺省显示 'ok'（or reason）。"""
    out = _format_metric("m", {"value": 1.0})
    assert "ok" in out


def test_format_metric_float_with_explicit_reason():
    out = _format_metric("m", {"value": 1.0, "reason": "computed"})
    assert "computed" in out


def test_format_metric_name_padding_36():
    """name 列固定宽 36 字符。"""
    out = _format_metric("short", {"value": 1})
    # "  short" + spaces 直到第 38 列 (2 + 36)
    lines = out.split("\n")
    assert len(lines) == 1
    # 找到 value "1" 的位置
    idx_one = out.rfind("1")
    assert idx_one >= 38  # 至少 2 + 36


def test_format_metric_long_name_exceeds_padding():
    """name 超过 36 字符时仍渲染（不截断）。"""
    long_name = "x" * 50
    out = _format_metric(long_name, {"value": 1})
    assert long_name in out


def test_format_metric_returns_str():
    out = _format_metric("m", {"value": 1})
    assert isinstance(out, str)


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    assert set(sig.parameters) == {"name", "metric"}


def test_format_metric_name_annotation_str():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.parameters["name"].annotation)


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


# =========================================================================
# _run_inspect_doc 错误路径
# =========================================================================


def test_run_inspect_doc_nonexistent_returns_2(tmp_path: Path):
    p = tmp_path / "missing.json"
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_not_dict_returns_1(tmp_path: Path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_empty_dict_returns_0(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_str_path_returns_0(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_path_object_returns_0(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    args = _FakeArgs(p)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    assert set(sig.parameters) == {"args"}


def test_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# =========================================================================
# main() 退出码
# =========================================================================


def test_main_no_args_exits_nonzero():
    """无子命令 → argparse error → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_main_unknown_command_exits_nonzero():
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_run_invalid_parser_choice_exits():
    """--parser 不在 choices → argparse error → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc:
        main(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])
    assert exc.value.code == 2


def test_main_run_missing_manifest_arg_exits():
    with pytest.raises(SystemExit):
        main(["run", "--output", "y"])


def test_main_run_missing_output_arg_exits():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x"])


def test_main_run_nonexistent_manifest_returns_2(tmp_path: Path):
    """manifest 不存在 → return 2（不抛 SystemExit）。"""
    missing = tmp_path / "missing.json"
    rc = main(["run", "--manifest", str(missing), "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_main_validate_report_nonexistent_returns_2(tmp_path: Path):
    missing = tmp_path / "missing.json"
    rc = main(["validate-report", str(missing)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_nonexistent_returns_2(tmp_path: Path):
    missing = tmp_path / "missing.json"
    rc = main(["inspect-doc", str(missing)])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_top_level_list_returns_1(tmp_path: Path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_empty_dict_returns_0(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_validate_report_with_invalid_schema_returns_1(tmp_path: Path, monkeypatch):
    """validate-report 文件存在但 Schema 校验失败 → return 1。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")

    import evaluation.cli as cli_mod
    from evaluation.schema import EvalSchemaError

    def _fake_validate(_p, _schema):
        raise EvalSchemaError("schema failed")

    monkeypatch.setattr(cli_mod, "validate_file", _fake_validate)
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_with_filenotfound_returns_2(tmp_path: Path, monkeypatch):
    """validate-report 文件存在但 validate_file 内部抛 FileNotFoundError → return 2。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")

    import evaluation.cli as cli_mod

    def _fake_validate(_p, _schema):
        raise FileNotFoundError("schema file missing")

    monkeypatch.setattr(cli_mod, "validate_file", _fake_validate)
    rc = main(["validate-report", str(p)])
    assert rc == 2


def test_main_signature():
    sig = inspect.signature(main)
    assert set(sig.parameters) == {"argv"}


def test_main_argv_annotation_optional_list_str():
    sig = inspect.signature(main)
    annotation = sig.parameters["argv"].annotation
    assert "list" in str(annotation) or "None" in str(annotation)


def test_main_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_no_explicit_all():
    """cli.py 不定义 __all__（命令行入口）。"""
    import evaluation.cli as mod
    assert not hasattr(mod, "__all__")


def test_module_uses_future_annotations():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "import argparse" in src


def test_module_imports_json():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_sys():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "import sys" in src


def test_module_imports_path():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_manifest_load():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from evaluation.manifest import" in src
    assert "load_manifest" in src
    assert "ManifestError" in src


def test_module_imports_report_get_git_provenance():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from evaluation.report import" in src
    assert "get_git_provenance" in src


def test_module_imports_runner_run_evaluation():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from evaluation.runner import" in src
    assert "run_evaluation" in src


def test_module_imports_schema_validate_file():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from evaluation.schema import" in src
    assert "validate_file" in src
    assert "EvalSchemaError" in src


def test_module_has_stdout_reconfigure_block():
    """Windows utf-8 reconfigure 块。"""
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "sys.stdout.reconfigure" in src
    assert "errors=" in src


def test_module_stdout_reconfigure_in_try_except():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "except (AttributeError, OSError)" in src


def test_module_docstring_present():
    import evaluation.cli as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_subcommands():
    import evaluation.cli as mod
    doc = mod.__doc__
    for name in ("run", "validate-report", "inspect-doc"):
        assert name in doc


def test_module_docstring_mentions_inspect_doc_purpose():
    """inspect-doc 是开发期 sanity check。"""
    import evaluation.cli as mod
    doc = mod.__doc__
    assert "inspect-doc" in doc
    assert "sanity" in doc.lower() or "不写报告" in doc


def test_module_has_main_function():
    import evaluation.cli as mod
    assert callable(mod.main)


def test_module_has_build_parser_function():
    import evaluation.cli as mod
    assert callable(mod._build_parser)


def test_module_has_format_metric_function():
    import evaluation.cli as mod
    assert callable(mod._format_metric)


def test_module_has_run_inspect_doc_function():
    import evaluation.cli as mod
    assert callable(mod._run_inspect_doc)


def test_module_main_raises_system_exit_at_module_main():
    """if __name__ == '__main__' 时 raise SystemExit(main())。"""
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert 'raise SystemExit(main())' in src
    assert "__main__" in src


# =========================================================================
# 综合行为
# =========================================================================


def test_build_parser_idempotent():
    a = _build_parser()
    b = _build_parser()
    assert isinstance(a, argparse.ArgumentParser)
    assert isinstance(b, argparse.ArgumentParser)
    # 每次返回新实例
    assert a is not b


def test_format_metric_idempotent():
    metric = {"value": 1.5, "reason": "ok"}
    assert _format_metric("m", metric) == _format_metric("m", metric)


def test_format_metric_does_not_mutate_input():
    metric = {"value": {"b": 2, "a": 1}, "reason": "info"}
    before = json.loads(json.dumps(metric))
    _format_metric("m", metric)
    assert metric == before


def test_main_run_then_validate_report_roundtrip(tmp_path: Path, monkeypatch):
    """run 生成报告 → validate-report 校验通过。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text("{}", encoding="utf-8")

    import evaluation.cli as cli_mod

    class _FakeManifest:
        project_root = tmp_path
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        pdf_count = 0
        docx_count = 0
        content_group_count = 0
        categories_covered = []

    def _fake_load(_p):
        return _FakeManifest()

    def _fake_run(manifest, output_path, **kwargs):
        report = {
            "report_version": "1.1",
            "provenance": {"parser_name": kwargs.get("parser_name", "fallback")},
            "devset": {"status": "incomplete", "file_count": 0},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report), encoding="utf-8")
        return report

    def _fake_validate(_p, _schema):
        return None

    monkeypatch.setattr(cli_mod, "load_manifest", _fake_load)
    monkeypatch.setattr(cli_mod, "run_evaluation", _fake_run)
    monkeypatch.setattr(cli_mod, "validate_file", _fake_validate)

    output_p = tmp_path / "out" / "report.json"
    rc1 = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc1 == 0
    assert output_p.is_file()

    rc2 = main(["validate-report", str(output_p)])
    assert rc2 == 0


def test_main_inspect_doc_with_real_doc(tmp_path: Path):
    """inspect-doc 端到端：构造一个最小合法 Document JSON。"""
    p = tmp_path / "doc.json"
    doc = {
        "schema_version": "0.1.0",
        "document_id": "doc-x",
        "source_path": "/tmp/x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "doc-x::e0000", "type": "paragraph", "source_locator": {}, "content": "hello"}
        ],
        "chunks": [
            {"chunk_id": "doc-x::c0000", "text": "hello", "source_element_ids": ["doc-x::e0000"]}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_with_tolerance_chars(tmp_path: Path):
    """inspect-doc --tolerance-chars 不报错。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0
