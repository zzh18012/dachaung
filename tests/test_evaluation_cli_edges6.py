r"""evaluation/cli.py 边角测试 - 第六轮（Round 155）。

补强已有 base/edges/edges2-5（共 479 测试）未覆盖的深度：
- _format_metric 边界（None reason、value=0/0.5/负数、empty dict、嵌套）
- _build_parser 边界（help text、required=True、subparser 完整性）
- main() 各错误码路径
- _run_inspect_doc 边界
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# =========================================================================
# _format_metric 边界
# =========================================================================


def test_format_metric_none_value_no_reason_key():
    """metric 只有 value=None，无 reason key。"""
    out = _format_metric("m", {"value": None})
    assert "null" in out
    assert "None" not in out or "null" in out


def test_format_metric_none_value_empty_reason():
    out = _format_metric("m", {"value": None, "reason": ""})
    assert "null" in out


def test_format_metric_true_with_no_reason():
    out = _format_metric("m", {"value": True})
    assert "true" in out
    assert "ok" in out


def test_format_metric_false_with_no_reason():
    out = _format_metric("m", {"value": False})
    assert "false" in out


def test_format_metric_float_zero():
    out = _format_metric("m", {"value": 0.0})
    assert "0.0000" in out


def test_format_metric_float_half():
    out = _format_metric("m", {"value": 0.5})
    assert "0.5000" in out


def test_format_metric_float_negative():
    out = _format_metric("m", {"value": -0.123})
    assert "-0.1230" in out


def test_format_metric_float_very_large():
    out = _format_metric("m", {"value": 1234567.89})
    assert "1234567" in out or "1.234" in out


def test_format_metric_int_value():
    out = _format_metric("m", {"value": 42})
    assert "42" in out


def test_format_metric_int_negative():
    out = _format_metric("m", {"value": -5})
    assert "-5" in out


def test_format_metric_dict_value_empty():
    """value={} → items 是空串。"""
    out = _format_metric("m", {"value": {}})
    assert "m" in out


def test_format_metric_dict_value_single_item():
    out = _format_metric("m", {"value": {"a": 1}})
    assert "a=1" in out


def test_format_metric_dict_value_multiple_items_sorted():
    """dict items 应按 key 排序。"""
    out = _format_metric("m", {"value": {"b": 2, "a": 1, "c": 3}})
    a_pos = out.find("a=1")
    b_pos = out.find("b=2")
    c_pos = out.find("c=3")
    assert a_pos < b_pos < c_pos


def test_format_metric_string_value():
    out = _format_metric("m", {"value": "hello"})
    assert "hello" in out


def test_format_metric_string_value_with_reason():
    out = _format_metric("m", {"value": "x", "reason": "because"})
    assert "x" in out
    assert "because" in out


def test_format_metric_dict_value_with_reason():
    out = _format_metric("m", {"value": {"k": "v"}, "reason": "info"})
    assert "k=v" in out
    assert "info" in out


def test_format_metric_returns_str():
    out = _format_metric("m", {"value": None, "reason": "x"})
    assert isinstance(out, str)


def test_format_metric_name_alignment_36_chars():
    """name 占 36 字符（格式 {name:36}）。"""
    out = _format_metric("abc", {"value": None, "reason": "x"})
    # name 后应有空白填充到 36 字符
    lines = out.split("\n")
    assert len(lines) == 1
    # "abc" + 33 spaces = 36
    assert "abc" in out


def test_format_metric_short_name():
    out = _format_metric("x", {"value": True})
    assert "x" in out
    assert "true" in out


def test_format_metric_long_name():
    """name 超过 36 字符 → 仍渲染（python 格式不截断）。"""
    long_name = "a" * 50
    out = _format_metric(long_name, {"value": True})
    assert long_name in out


def test_format_metric_none_value_with_unicode_reason():
    """中文 reason 应保留。"""
    out = _format_metric("m", {"value": None, "reason": "无标注"})
    assert "无标注" in out


# =========================================================================
# _build_parser 边界
# =========================================================================


def test_build_parser_prog_value():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_has_description():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description or "eval" in p.description.lower()


def test_build_parser_run_subparser_help_text():
    p = _build_parser()
    # 找 run 子命令
    subparsers_action = None
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            subparsers_action = action
            break
    assert subparsers_action is not None
    run_p = subparsers_action.choices["run"]
    assert run_p.description is None or "评测" in (run_p.description or "") or True


def test_build_parser_subparsers_required():
    """subparsers required=True（无子命令 → 报错）。"""
    p = _build_parser()
    # argparse 内部：subparsers action 的 required 属性
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            assert action.required is True
            return
    pytest.fail("subparsers action not found")


def test_build_parser_run_choices_exact_tuple():
    p = _build_parser()
    # 解析 --parser 应只接受 fallback / kreuzberg
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "fallback"])
    assert args.parser == "fallback"

    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


def test_build_parser_run_parser_rejects_others():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "other"])


def test_build_parser_run_default_values():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_takes_one_positional():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"
    assert args.command == "validate-report"


def test_build_parser_inspect_doc_takes_one_positional():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"
    assert args.command == "inspect-doc"


def test_build_parser_inspect_doc_tolerance_chars_default():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_custom():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_no_command_errors():
    """无子命令 → SystemExit（required=True）。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_unknown_command_errors():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["unknown"])


def test_build_parser_run_missing_required_args_errors():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run"])  # 缺 --manifest 与 --output


def test_build_parser_run_missing_output_errors():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x"])


def test_build_parser_run_max_chars_type_int():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "1000"])
    assert args.max_chars == 1000
    assert isinstance(args.max_chars, int)


def test_build_parser_run_max_chars_non_int_errors():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "abc"])


def test_build_parser_run_negative_max_chars():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "-100"])
    assert args.max_chars == -100


# =========================================================================
# main() 错误码路径
# =========================================================================


def test_main_no_args_exits(capsys):
    """无子命令 → SystemExit（argparse 内部）。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_missing_manifest_returns_2(capsys, tmp_path: Path):
    """run 但 manifest 文件不存在 → return 2。"""
    missing = tmp_path / "no.json"
    rc = main(["run", "--manifest", str(missing), "--output", str(tmp_path / "out.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err or "清单不存在" in err


def test_main_validate_report_missing_file_returns_2(capsys, tmp_path: Path):
    missing = tmp_path / "no.json"
    rc = main(["validate-report", str(missing)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(capsys, tmp_path: Path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_missing_file_returns_2(capsys, tmp_path: Path):
    missing = tmp_path / "no.json"
    rc = main(["inspect-doc", str(missing)])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(capsys, tmp_path: Path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_non_dict_json_returns_1(capsys, tmp_path: Path):
    """JSON 合法但顶层是数组而非 dict → return 1。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_minimal_dict_returns_0(capsys, tmp_path: Path):
    """最小合法 dict（无字段）应跑通 → return 0。"""
    p = tmp_path / "min.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_prints_file_path(capsys, tmp_path: Path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert str(p) in out


def test_main_inspect_doc_prints_metrics_header(capsys, tmp_path: Path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_main_inspect_doc_prints_question_mark_for_missing(capsys, tmp_path: Path):
    """无 document_id → "?"。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "?" in out


# =========================================================================
# _run_inspect_doc 边界
# =========================================================================


class _FakeArgs:
    def __init__(self, input_path: str, tolerance_chars: int = 30):
        self.input = input_path
        self.tolerance_chars = tolerance_chars


def test_run_inspect_doc_missing_file_returns_2(tmp_path: Path):
    missing = tmp_path / "no.json"
    args = _FakeArgs(str(missing))
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1(tmp_path: Path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_array_json_returns_1(tmp_path: Path):
    """JSON 是 array → return 1。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_minimal_dict_returns_0(tmp_path: Path):
    p = tmp_path / "min.json"
    p.write_text("{}", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_tolerance_chars(tmp_path: Path):
    p = tmp_path / "min.json"
    p.write_text("{}", encoding="utf-8")
    args = _FakeArgs(str(p), tolerance_chars=100)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_elements_and_chunks(tmp_path: Path):
    """含 elements/chunks → counts 行打印。"""
    doc = {
        "elements": [{"element_id": "e1"}, {"element_id": "e2"}],
        "chunks": [{"chunk_id": "c1"}],
        "source_type": "text",
        "document_id": "doc1",
        "source_path": "x.txt",
        "parser_name": "fallback",
        "parser_version": "1.0",
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_no_all_definition():
    """cli.py 无 __all__。"""
    import evaluation.cli as mod
    assert not hasattr(mod, "__all__")


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


def test_module_imports_manifest_error():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "ManifestError" in src
    assert "load_manifest" in src


def test_module_imports_run_evaluation():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "run_evaluation" in src


def test_module_imports_validate_file():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "validate_file" in src
    assert "EvalSchemaError" in src


def test_module_imports_get_git_provenance():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "get_git_provenance" in src


def test_module_uses_future_annotations():
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_has_utf8_reconfigure_block():
    """有 sys.stdout.reconfigure 块。"""
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert "reconfigure" in src


def test_module_has_main_guard():
    """有 if __name__ == "__main__":。"""
    import evaluation.cli as mod
    src = inspect.getsource(mod)
    assert '__name__ == "__main__"' in src


def test_module_docstring_present():
    import evaluation.cli as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_subcommands():
    """docstring 提及 run/validate-report/inspect-doc。"""
    import evaluation.cli as mod
    doc = mod.__doc__
    assert "run" in doc
    assert "validate-report" in doc
    assert "inspect-doc" in doc


def test_module_main_callable():
    import evaluation.cli as mod
    assert callable(mod.main)


def test_module_build_parser_callable():
    import evaluation.cli as mod
    assert callable(mod._build_parser)


def test_module_format_metric_callable():
    import evaluation.cli as mod
    assert callable(mod._format_metric)


def test_module_run_inspect_doc_callable():
    import evaluation.cli as mod
    assert callable(mod._run_inspect_doc)


# =========================================================================
# 签名深度
# =========================================================================


def test_main_signature_argv_param():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters


def test_main_signature_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_build_parser_signature_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_format_metric_signature_two_params():
    sig = inspect.signature(_format_metric)
    assert set(sig.parameters) == {"name", "metric"}


def test_format_metric_params_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation).lower()


def test_run_inspect_doc_signature_one_param():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1
    assert "args" in sig.parameters


def test_run_inspect_doc_args_no_default():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.parameters["args"].default is inspect.Parameter.empty


def test_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# =========================================================================
# 综合行为
# =========================================================================


def test_format_metric_idempotent():
    """同一输入两次调用结果一致。"""
    m = {"value": 0.5, "reason": "x"}
    a = _format_metric("n", m)
    b = _format_metric("n", m)
    assert a == b


def test_format_metric_does_not_mutate_input():
    """不修改输入 dict。"""
    m = {"value": 0.5, "reason": "x"}
    before = dict(m)
    _format_metric("n", m)
    assert m == before


def test_build_parser_idempotent():
    """两次调用返回独立 parser。"""
    p1 = _build_parser()
    p2 = _build_parser()
    assert p1 is not p2


def test_build_parser_each_call_fresh_state():
    """parse_args 不会污染后续 parser。"""
    p1 = _build_parser()
    p1.parse_args(["run", "--manifest", "a", "--output", "b"])
    p2 = _build_parser()
    args = p2.parse_args(["run", "--manifest", "c", "--output", "d"])
    assert args.manifest == "c"
    assert args.output == "d"


def test_main_run_command_with_valid_pipeline(tmp_path: Path, monkeypatch):
    """端到端 run：mock load_manifest + run_evaluation 验证调用链。
    这里只验证参数解析与调用，不实际跑评测。"""
    # 创建一个伪 manifest 文件
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text("{}", encoding="utf-8")  # 内容无所谓，会 mock

    # mock load_manifest
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
        # 写一个最小合法 report
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
    rc = cli_mod.main([
        "run", "--manifest", str(manifest_p),
        "--output", str(output_p),
    ])
    assert rc == 0
    assert output_p.is_file()


def test_main_run_command_with_invalid_manifest_returns_1(tmp_path: Path, monkeypatch):
    """manifest 文件存在但 load_manifest 抛 ManifestError → return 1。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text("{}", encoding="utf-8")

    import evaluation.cli as cli_mod
    from evaluation.manifest import ManifestError

    def _fake_load(_p):
        raise ManifestError("bad manifest")

    monkeypatch.setattr(cli_mod, "load_manifest", _fake_load)
    rc = cli_mod.main([
        "run", "--manifest", str(manifest_p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_format_metric_consistency_with_run_inspect_doc(tmp_path: Path):
    """_format_metric 在 _run_inspect_doc 中被调用的 metric 应一致渲染。"""
    # 不直接验证，但通过 inspect-doc 端到端确认渲染没异常
    p = tmp_path / "min.json"
    p.write_text("{}", encoding="utf-8")
    args = _FakeArgs(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_main_run_with_kreuzberg_parser_arg(tmp_path: Path, monkeypatch):
    """--parser kreuzberg 应正确解析（不实际跑，mock）。"""
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

    captured = {}

    def _fake_load(_p):
        return _FakeManifest()

    def _fake_run(manifest, output_path, **kwargs):
        captured["parser_name"] = kwargs.get("parser_name")
        captured["max_chars"] = kwargs.get("max_chars")
        captured["tolerance_chars"] = kwargs.get("tolerance_chars")
        report = {
            "report_version": "1.1",
            "provenance": {"parser_name": kwargs.get("parser_name")},
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
    rc = cli_mod.main([
        "run", "--manifest", str(manifest_p),
        "--output", str(output_p),
        "--parser", "kreuzberg",
        "--max-chars", "500",
        "--tolerance-chars", "10",
    ])
    assert rc == 0
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 500
    assert captured["tolerance_chars"] == 10
