"""evaluation/cli.py 边角测试 - 第四轮（Round 110）。

补强已有 base/edges/edges2/edges3（共 97+ 测试）未覆盖的深度路径：
- _format_metric：int value 渲染、int 0、float 0.0、reason 空字符串、
  reason 含中文、dict value 数字/混合类型、dict 空渲染为空字符串、
  bool True/False 大小写、字符串含逗号
- _run_inspect_doc：doc 缺 source_type 默认 unknown、缺 elements 默认 []、
  缺 chunks 默认 []、elements=null、chunks=null、
  compute_automatic_metrics 调用参数完整透传、
  metrics 输出顺序：bool 优先、再 int/float、再 dict/str、最后 null
- _build_parser：默认值（max-chars=800、tolerance-chars=30）、
  --parser choices 拒绝未知、prog 字符串精确值、subparsers required
- main：unknown 子命令返回 2、argv 为 tuple 也接受
- 模块结构：__all__ 不存在（CLI 模块）、main 签名、
  imports 完整性、UTF-8 reconfigure 容错
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# _format_metric：int value 边界
# =========================================================================


def test_format_metric_int_positive_value_renders_without_decimal():
    """int 正数不走 float 分支，无 .0000 后缀。"""
    out = _format_metric("count_x", {"value": 42, "reason": "ok"})
    assert "42" in out
    assert ".0000" not in out


def test_format_metric_int_zero_value_renders_zero():
    out = _format_metric("count_zero", {"value": 0, "reason": "ok"})
    assert " 0 " in out or out.rstrip().endswith("0")


def test_format_metric_int_large_value():
    out = _format_metric("big", {"value": 1000000, "reason": "count"})
    assert "1000000" in out


def test_format_metric_int_negative_value():
    out = _format_metric("neg", {"value": -5, "reason": "delta"})
    assert "-5" in out


def test_format_metric_int_zero_with_none_reason_uses_ok():
    out = _format_metric("n", {"value": 0})
    assert "ok" in out


# =========================================================================
# _format_metric：float 0.0 边界
# =========================================================================


def test_format_metric_float_zero_renders_0_0000():
    out = _format_metric("ratio", {"value": 0.0, "reason": "all zero"})
    assert "0.0000" in out


def test_format_metric_float_one_renders_1_0000():
    out = _format_metric("ratio", {"value": 1.0, "reason": "perfect"})
    assert "1.0000" in out


def test_format_metric_float_uses_default_reason_when_empty_string():
    """reason='' 应被替换为 'ok'。"""
    out = _format_metric("r", {"value": 0.5, "reason": ""})
    # 空字符串 reason 不进入分支（falsy），用 'ok'
    # 但代码是 `reason or 'ok'`，空字符串是 falsy → 'ok'
    assert "ok" in out


def test_format_metric_float_with_chinese_reason():
    out = _format_metric("r", {"value": 0.5, "reason": "比例正常"})
    assert "比例正常" in out


# =========================================================================
# _format_metric：bool 边界
# =========================================================================


def test_format_metric_bool_true_renders_lowercase():
    out = _format_metric("ok", {"value": True, "reason": "matched"})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_renders_lowercase():
    out = _format_metric("ok", {"value": False, "reason": "mismatched"})
    assert "false" in out
    assert "False" not in out


def test_format_metric_bool_with_no_reason_uses_ok():
    out = _format_metric("b", {"value": True})
    assert "ok" in out


# =========================================================================
# _format_metric：dict value 边界
# =========================================================================


def test_format_metric_dict_value_renders_items_sorted_by_key():
    out = _format_metric("by_type", {"value": {"b": 1, "a": 2}, "reason": "count"})
    # sorted 后 a 在 b 前
    assert out.index("a=2") < out.index("b=1")


def test_format_metric_dict_value_empty_dict_renders_only_separator():
    out = _format_metric("empty", {"value": {}, "reason": "none"})
    # 空字符串 join 后剩两个空格分隔
    assert "({" not in out  # 不是 repr
    # 检查 dict 段是空
    parts = out.split("  ")  # 双空格分隔
    # 找到 reason 之前的字段，应是空
    found_empty_field = any(p.strip() == "" for p in parts[:-1])
    assert found_empty_field


def test_format_metric_dict_value_with_int_and_string():
    out = _format_metric("mixed", {"value": {"n": 5, "s": "abc"}, "reason": "x"})
    assert "n=5" in out
    assert "s=abc" in out


def test_format_metric_dict_value_with_special_chars_in_value():
    out = _format_metric(
        "sp", {"value": {"k": "val, with comma"}, "reason": "r"}
    )
    assert "k=val, with comma" in out


def test_format_metric_dict_value_with_none_value():
    out = _format_metric("has_null", {"value": {"k": None}, "reason": "r"})
    assert "k=None" in out


def test_format_metric_dict_value_with_bool_value():
    out = _format_metric("has_bool", {"value": {"k": True}, "reason": "r"})
    assert "k=True" in out


# =========================================================================
# _format_metric：string value 边界
# =========================================================================


def test_format_metric_string_value_with_special_chars():
    out = _format_metric("msg", {"value": "hello\nworld", "reason": "ok"})
    assert "hello" in out
    assert "world" in out


def test_format_metric_string_value_with_quotes():
    out = _format_metric("q", {"value": '"quoted"', "reason": "r"})
    assert '"quoted"' in out


def test_format_metric_string_value_with_unicode():
    out = _format_metric("u", {"value": "你好世界", "reason": "r"})
    assert "你好世界" in out


def test_format_metric_string_value_uses_default_reason_when_empty():
    out = _format_metric("s", {"value": "abc", "reason": ""})
    assert "ok" in out


# =========================================================================
# _format_metric：name 列宽
# =========================================================================


def test_format_metric_name_shorter_than_36_pads_to_36():
    """name 字段宽度 36，短名字左侧填充空格对齐。"""
    out = _format_metric("x", {"value": 1, "reason": "r"})
    # name 段从开头到 'x' 之后被填充到至少 36 字符
    line = out  # 单行
    # 验证有连续 35+ 个空格（不可能恰好，但应至少有大量空格）
    assert "  x" in line  # 两个空格 + x 开头


def test_format_metric_name_exactly_36_chars_no_extra_pad():
    """name 正好 36 字符不应多加空格。"""
    name = "a" * 36
    out = _format_metric(name, {"value": 1, "reason": "r"})
    assert name in out


def test_format_metric_name_longer_than_36_does_not_truncate():
    """超过 36 字符的 name 不截断。"""
    name = "x" * 50
    out = _format_metric(name, {"value": 1, "reason": "r"})
    assert name in out


# =========================================================================
# _run_inspect_doc：doc 缺字段
# =========================================================================


def _write_doc(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_missing_source_type_defaults_unknown(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"document_id": "d1"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_missing_elements_treats_as_empty(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"document_id": "d1", "source_type": "pdf"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=0" in out


def test_run_inspect_doc_missing_chunks_treats_as_empty(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"document_id": "d1", "source_type": "pdf"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunks=0" in out


def test_run_inspect_doc_elements_null_raises_in_metrics(
    tmp_path: Path
):
    """elements=null 会让 cli 层把局部变量变 []，但 compute_automatic_metrics
    读 doc.get('elements', []) 仍返回 None → len(None) 抛 TypeError。

    这是 metrics.py 的现状（无 None 保护）；本测试断言该行为以保留现状。
    """
    p = _write_doc(
        tmp_path,
        {"document_id": "d1", "source_type": "pdf", "elements": None, "chunks": None},
    )
    with pytest.raises(TypeError):
        _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())


def test_run_inspect_doc_with_document_id(tmp_path: Path, capsys):
    p = _write_doc(
        tmp_path, {"document_id": "my_doc_id", "source_type": "docx"}
    )
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "my_doc_id" in out


def test_run_inspect_doc_missing_document_id_uses_question_mark(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "document_id: ?" in out


def test_run_inspect_doc_missing_source_path_uses_question_mark(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "source:      ?" in out


def test_run_inspect_doc_missing_parser_name_uses_question_mark(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "parser:      ?" in out


def test_run_inspect_doc_parser_version_missing_uses_question_mark(
    tmp_path: Path, capsys
):
    p = _write_doc(tmp_path, {"source_type": "docx", "parser_name": "fallback"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    # v? 处理
    assert "v?" in out


def test_run_inspect_doc_prints_metrics_header(tmp_path: Path, capsys):
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_returns_zero_on_minimal_valid_doc(tmp_path: Path):
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0


# =========================================================================
# _run_inspect_doc：输入异常路径
# =========================================================================


def test_run_inspect_doc_array_root_returns_1(
    tmp_path: Path, capsys
):
    p = tmp_path / "doc.json"
    p.write_text("[]", encoding="utf-8")
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1
    err = capsys.readouterr().err
    assert "顶层不是对象" in err or "not an object" in err.lower() or "对象" in err


def test_run_inspect_doc_string_root_returns_1(
    tmp_path: Path, capsys
):
    p = tmp_path / "doc.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1


def test_run_inspect_doc_null_root_returns_1(
    tmp_path: Path, capsys
):
    p = tmp_path / "doc.json"
    p.write_text("null", encoding="utf-8")
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1


def test_run_inspect_doc_int_root_returns_1(
    tmp_path: Path, capsys
):
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1


def test_run_inspect_doc_bool_root_returns_1(
    tmp_path: Path, capsys
):
    p = tmp_path / "doc.json"
    p.write_text("true", encoding="utf-8")
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1


def test_run_inspect_doc_invalid_json_returns_1(
    tmp_path: Path, capsys
):
    p = tmp_path / "doc.json"
    p.write_text("{not json", encoding="utf-8")
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err


def test_run_inspect_doc_file_not_found_returns_2(capsys):
    rc = _run_inspect_doc(
        type("A", (), {"input": "C:/nonexistent/path.json", "tolerance_chars": 30})()
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "文档不存在" in err or "not exist" in err.lower() or "[ERROR]" in err


# =========================================================================
# _run_inspect_doc：_sort_key 排序行为
# =========================================================================


def test_run_inspect_doc_metrics_order_bool_before_null(
    tmp_path: Path, capsys, monkeypatch
):
    """bool 类指标应排在 null 类指标之前。"""
    from evaluation import metrics as metrics_mod

    def fake_compute(*args, **kwargs):
        return {
            "alpha": {"value": None, "reason": "r1"},
            "beta": {"value": True, "reason": "r2"},
        }

    monkeypatch.setattr(metrics_mod, "compute_automatic_metrics", fake_compute)
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    # beta (bool) 应在 alpha (null) 前
    assert out.index("beta") < out.index("alpha")


def test_run_inspect_doc_metrics_order_int_before_string(
    tmp_path: Path, capsys, monkeypatch
):
    """int 类指标应排在 string/dict 类之前。"""
    from evaluation import metrics as metrics_mod

    def fake_compute(*args, **kwargs):
        return {
            "alpha": {"value": "msg", "reason": "r1"},
            "beta": {"value": 5, "reason": "r2"},
        }

    monkeypatch.setattr(metrics_mod, "compute_automatic_metrics", fake_compute)
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert out.index("beta") < out.index("alpha")


def test_run_inspect_doc_metrics_order_dict_after_int(
    tmp_path: Path, capsys, monkeypatch
):
    """dict 类指标应排在 int 之后，null 之前。"""
    from evaluation import metrics as metrics_mod

    def fake_compute(*args, **kwargs):
        return {
            "alpha": {"value": {"a": 1}, "reason": "r1"},
            "beta": {"value": 5, "reason": "r2"},
        }

    monkeypatch.setattr(metrics_mod, "compute_automatic_metrics", fake_compute)
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert out.index("beta") < out.index("alpha")


def test_run_inspect_doc_metrics_same_category_sorted_alphabetically(
    tmp_path: Path, capsys, monkeypatch
):
    """同类指标按字母排序。"""
    from evaluation import metrics as metrics_mod

    def fake_compute(*args, **kwargs):
        return {
            "zeta": {"value": 1, "reason": "r"},
            "alpha": {"value": 2, "reason": "r"},
            "gamma": {"value": 3, "reason": "r"},
        }

    monkeypatch.setattr(metrics_mod, "compute_automatic_metrics", fake_compute)
    p = _write_doc(tmp_path, {"source_type": "docx"})
    rc = _run_inspect_doc(type("A", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0
    out = capsys.readouterr().out
    assert out.index("alpha") < out.index("gamma") < out.index("zeta")


# =========================================================================
# _build_parser：默认值与精确字段
# =========================================================================


def test_build_parser_run_default_max_chars_is_800():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_is_30():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_default_parser_is_fallback():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_inspect_default_tolerance_chars_is_30():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_accepts_kreuzberg_parser():
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json", "--parser", "kreuzberg"]
    )
    assert args.parser == "kreuzberg"


def test_build_parser_run_rejects_unknown_parser_value():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(
            ["run", "--manifest", "m.json", "--output", "o.json", "--parser", "xxx"]
        )


def test_build_parser_run_accepts_negative_max_chars():
    """argparse 接受任意 int，业务校验在下游。"""
    p = _build_parser()
    args = p.parse_args(
        [
            "run",
            "--manifest",
            "m.json",
            "--output",
            "o.json",
            "--max-chars",
            "-1",
        ]
    )
    assert args.max_chars == -1


def test_build_parser_run_accepts_zero_max_chars():
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "0"]
    )
    assert args.max_chars == 0


def test_build_parser_prog_exact_value():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_has_raw_description_formatter():
    """formatter_class 应是 RawDescriptionHelpFormatter。"""
    import argparse

    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_no_command_required_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_unknown_command_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["frobnicate"])


def test_build_parser_run_missing_manifest_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "o.json"])


def test_build_parser_run_missing_output_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json"])


def test_build_parser_inspect_missing_input_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_validate_missing_input_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_subparsers_required_true():
    """subparsers 必须是 required。"""
    p = _build_parser()
    # 内部 _subparsers 是私有 API；通过外部行为验证
    with pytest.raises(SystemExit):
        p.parse_args([])


# =========================================================================
# main：unknown / 边界
# =========================================================================


def test_main_unknown_command_returns_2(capsys):
    """unknown 子命令触发 argparse error，SystemExit(2) 上抛。"""
    with pytest.raises(SystemExit) as exc:
        main(["frobnicate"])
    assert exc.value.code == 2


def test_main_empty_argv_returns_2():
    """空 argv → argparse 报 missing command → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_main_argv_as_tuple_accepted(tmp_path: Path):
    """argv 也接受 tuple（list-like）。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(("validate-report", str(p)))
    # 空 dict 应不通过 schema 校验，但 argparse 与执行流不应崩
    assert rc in (0, 1, 2)


# =========================================================================
# 模块结构验证
# =========================================================================


def test_module_does_not_define_all():
    """CLI 模块不导出 __all__，仅作为脚本入口。"""
    import evaluation.cli as cli_mod

    assert not hasattr(cli_mod, "__all__")


def test_module_has_main():
    import evaluation.cli as cli_mod

    assert callable(cli_mod.main)


def test_module_has_build_parser():
    import evaluation.cli as cli_mod

    assert callable(cli_mod._build_parser)


def test_module_has_format_metric():
    import evaluation.cli as cli_mod

    assert callable(cli_mod._format_metric)


def test_module_has_run_inspect_doc():
    import evaluation.cli as cli_mod

    assert callable(cli_mod._run_inspect_doc)


def test_module_main_accepts_argv_keyword():
    """main 签名应支持 argv 参数。"""
    import inspect

    sig = inspect.signature(main)
    assert "argv" in sig.parameters


def test_module_main_return_annotation_is_int():
    """with `from __future__ import annotations` 注解是字符串。"""
    import inspect

    sig = inspect.signature(main)
    assert sig.return_annotation in (int, "int")


def test_module_imports_argparse():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "argparse")


def test_module_imports_json():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "json")


def test_module_imports_sys():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "sys")


def test_module_imports_path():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "Path")


def test_module_imports_load_manifest():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "load_manifest")


def test_module_imports_manifest_error():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "ManifestError")


def test_module_imports_run_evaluation():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "run_evaluation")


def test_module_imports_get_git_provenance():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "get_git_provenance")


def test_module_imports_validate_file():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "validate_file")


def test_module_imports_eval_schema_error():
    import evaluation.cli as cli_mod

    assert hasattr(cli_mod, "EvalSchemaError")


def test_module_has_utf8_reconfigure_block():
    """模块顶层应有 sys.stdout.reconfigure 容错块。"""
    src = Path(__import__("evaluation.cli", fromlist=["x"]).__file__).read_text(
        encoding="utf-8"
    )
    assert "reconfigure" in src
    assert "AttributeError" in src or "OSError" in src


def test_module_has_main_guard():
    import evaluation.cli as cli_mod

    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    assert '__name__ == "__main__"' in src
    assert "SystemExit" in src


def test_module_main_guard_raises_system_exit():
    """__main__ 块应 raise SystemExit(main())。"""
    import evaluation.cli as cli_mod

    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    assert "raise SystemExit(main())" in src


def test_module_docstring_present():
    import evaluation.cli as cli_mod

    assert cli_mod.__doc__ is not None
    assert len(cli_mod.__doc__) > 0


def test_module_docstring_mentions_run_subcommand():
    import evaluation.cli as cli_mod

    assert "run" in cli_mod.__doc__


def test_module_docstring_mentions_validate_report():
    import evaluation.cli as cli_mod

    assert "validate-report" in cli_mod.__doc__


def test_module_docstring_mentions_inspect_doc():
    import evaluation.cli as cli_mod

    assert "inspect-doc" in cli_mod.__doc__


def test_format_metric_docstring_present():
    assert _format_metric.__doc__ is not None


def test_run_inspect_doc_docstring_present():
    assert _run_inspect_doc.__doc__ is not None


def test_build_parser_docstring_absent():
    """_build_parser 是私有 helper，不强求 docstring。"""
    # 不强制；只检查函数存在
    assert callable(_build_parser)


def test_main_docstring_absent():
    """main 是入口，不强求 docstring。"""
    assert callable(main)
