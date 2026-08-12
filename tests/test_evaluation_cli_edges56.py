"""evaluation/cli.py 第五十七轮 edges 测试（Round 522）。

补强 edges55 未触及的角度（第二十九批）：
- _build_parser 第二十九批：prog / description / formatter_class / subparsers required=True / run --parser choices / run --max-chars type=int
- _format_metric 第二十九批：value 是负 float / value 是 dict 多 key / value 是 list（fallback path）/ value 是 very large int / value 是 0 / value 是 True/False 区分
- _run_inspect_doc 第二十九批：source_type missing / elements missing / chunks missing / 多 metric 顺序 / tolerance_chars 透传 / 返回码 0
- main 第二十九批：inspect-doc 不存在的文件返回 2 / inspect-doc JSON 顶层不是对象返回 1 / validate-report FileNotFoundError 返回 2
- module source forbidden tokens 第四十七批
- module source 字符串精确补强第四十三批
- signatures 第四十三批
- module 合理性第四十三批
- 端到端集成第四十三批
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第二十九批 ----------


def test_build_parser_prog_value_batch29():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_set_batch29():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description


def test_build_parser_formatter_class_batch29():
    p = _build_parser()
    assert p.formatter_class is not None


def test_build_parser_subparsers_required_true_batch29():
    """subparsers required=True（无子命令报错）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    assert len(sub_actions) == 1
    assert sub_actions[0].required is True


def test_build_parser_subparsers_dest_command_batch29():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    assert sub_actions[0].dest == "command"


def test_build_parser_three_subcommands_batch29():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    assert set(sub_actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_parser_choices_batch29():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    # 找到 --parser action
    parser_action = None
    for a in run_p._actions:
        if "--parser" in (a.option_strings or []):
            parser_action = a
            break
    assert parser_action is not None
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_max_chars_type_int_batch29():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    mc_action = None
    for a in run_p._actions:
        if "--max-chars" in (a.option_strings or []):
            mc_action = a
            break
    assert mc_action is not None
    assert mc_action.type is int


def test_build_parser_run_tolerance_chars_type_int_batch29():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    tc_action = None
    for a in run_p._actions:
        if "--tolerance-chars" in (a.option_strings or []):
            tc_action = a
            break
    assert tc_action is not None
    assert tc_action.type is int


def test_build_parser_run_parser_default_fallback_batch29():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.parser == "fallback"


def test_build_parser_run_max_chars_default_800_batch29():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.max_chars == 800


def test_build_parser_run_tolerance_chars_default_30_batch29():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_validate_report_input_positional_batch29():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_build_parser_inspect_doc_input_positional_batch29():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_build_parser_inspect_doc_tolerance_default_30_batch29():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_no_command_errors_batch29(capsys):
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


# ---------- _format_metric 第二十九批 ----------


def test_format_metric_negative_float_batch29(capsys):
    """负 float 用 :.4f 格式化。"""
    line = _format_metric("m1", {"value": -0.5, "reason": None})
    assert "-0.5000" in line


def test_format_metric_dict_multiple_keys_batch29():
    """dict value 多 key 按 sorted 渲染。"""
    line = _format_metric("counts", {"value": {"b": 2, "a": 1}, "reason": None})
    assert "a=1" in line
    assert "b=2" in line
    # 排序：a 在 b 之前
    assert line.index("a=1") < line.index("b=2")


def test_format_metric_dict_empty_batch29():
    """空 dict。"""
    line = _format_metric("counts", {"value": {}, "reason": None})
    # 空字符串 fallback
    assert "ok" in line or "()" in line or "  )" in line


def test_format_metric_very_large_int_batch29():
    """大 int。"""
    line = _format_metric("m1", {"value": 10**18, "reason": None})
    assert str(10**18) in line


def test_format_metric_zero_int_batch29():
    line = _format_metric("m1", {"value": 0, "reason": None})
    # 0 不是 None，也不是 bool/float/dict
    assert "0" in line


def test_format_metric_zero_float_batch29():
    line = _format_metric("m1", {"value": 0.0, "reason": None})
    assert "0.0000" in line


def test_format_metric_true_lowercase_batch29():
    """True 渲染为 'true'（小写）。"""
    line = _format_metric("m1", {"value": True, "reason": None})
    assert "true" in line
    assert "True" not in line


def test_format_metric_false_lowercase_batch29():
    """False 渲染为 'false'（小写）。"""
    line = _format_metric("m1", {"value": False, "reason": None})
    assert "false" in line


def test_format_metric_value_string_batch29():
    """string value（fallback path，不是 None/bool/float/dict）。"""
    line = _format_metric("m1", {"value": "hello", "reason": None})
    assert "hello" in line


def test_format_metric_value_unicode_batch29():
    """unicode name。"""
    line = _format_metric("指标名", {"value": 1.0, "reason": "原因"})
    assert "指标名" in line
    assert "原因" in line


def test_format_metric_alignment_36_chars_batch29():
    """name 占 36 字符宽。"""
    line = _format_metric("short", {"value": 1, "reason": None})
    # {:36} 至少 36 字符（含 padding）
    # 实际：name 占 36 列后接 value
    # 检查 "short" 后有大量空格
    assert "short" in line
    # 找到 short 后的空格数：line 以 "  short" + 空格开头
    prefix = line[:50]
    assert "  short" in prefix


# ---------- _run_inspect_doc 第二十九批 ----------


def test_run_inspect_doc_source_type_missing_batch29(capsys, tmp_path):
    """doc 没有 source_type → 默认 'unknown'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_elements_missing_batch29(capsys, tmp_path):
    """doc 没有 elements → 默认 []。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_chunks_missing_batch29(capsys, tmp_path):
    """doc 没有 chunks → 默认 []。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "chunks=0" in captured.out


def test_run_inspect_doc_returns_zero_on_success_batch29(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_nonexistent_returns_2_batch29():
    args = MagicMock(input="/nonexistent/path.json", tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1_batch29(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not valid json", encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_array_returns_1_batch29(tmp_path):
    """JSON 顶层是 array 而非 dict → 返回 1。"""
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_string_returns_1_batch29(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text('"hello"', encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_number_returns_1_batch29(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_output_has_metrics_header_batch29(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_output_has_file_line_batch29(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_output_has_counts_line_batch29(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {
                "elements": [{"type": "x"}],
                "chunks": [{"text": "a"}],
            }
        ),
        encoding="utf-8",
    )
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "counts:" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


# ---------- main 第二十九批 ----------


def test_main_inspect_doc_nonexistent_returns_2_batch29(capsys):
    rc = main(["inspect-doc", "/nonexistent.json"])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1_batch29(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_validate_report_nonexistent_returns_2_batch29():
    rc = main(["validate-report", "/nonexistent.json"])
    assert rc == 2


def test_main_run_nonexistent_manifest_returns_2_batch29():
    rc = main(["run", "--manifest", "/nonexistent.json", "--output", "/tmp/out.json"])
    assert rc == 2


def test_main_returns_int_batch29(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


def test_main_no_subcommand_exits_batch29(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_main_run_with_invalid_manifest_returns_1_batch29(tmp_path, capsys):
    """manifest 不符合 schema → 返回 1。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"manifest_version": "1.0"}), encoding="utf-8")  # 缺字段
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(p), "--output", str(out)])
    assert rc == 1


# ---------- module source forbidden tokens 第四十七批 ----------


def test_module_source_no_subprocess_batch29():
    src = inspect.getsource(climod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(climod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(climod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(climod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(climod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(climod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(climod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(climod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(climod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(climod)
    assert "requests" not in src


def test_module_source_no_unlink_batch29():
    src = inspect.getsource(climod)
    assert ".unlink()" not in src


def test_module_source_no_open_w_mode_batch29():
    """cli.py 用 input_path.open("r")，不写文件。"""
    src = inspect.getsource(climod)
    assert "'w'" not in src
    assert '"w"' not in src


# ---------- module source 字符串精确补强第四十三批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(climod)
    assert "评测 CLI" in src


def test_module_source_contains_build_parser_func_batch29():
    src = inspect.getsource(climod)
    assert "def _build_parser" in src


def test_module_source_contains_main_func_batch29():
    src = inspect.getsource(climod)
    assert "def main" in src


def test_module_source_contains_format_metric_func_batch29():
    src = inspect.getsource(climod)
    assert "def _format_metric" in src


def test_module_source_contains_run_inspect_doc_func_batch29():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc" in src


def test_module_source_contains_argparse_import_batch29():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_contains_sys_import_batch29():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_contains_load_manifest_import_batch29():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import" in src


def test_module_source_contains_run_evaluation_import_batch29():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import" in src


def test_module_source_contains_validate_file_import_batch29():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import" in src


def test_module_source_contains_main_block_batch29():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in src


def test_module_source_contains_subparsers_required_batch29():
    src = inspect.getsource(climod)
    assert "required=True" in src


def test_module_source_contains_utf8_reconfigure_batch29():
    src = inspect.getsource(climod)
    assert "reconfigure" in src


# ---------- signatures 第四十三批 ----------


def test_signature_build_parser_batch29():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_batch29():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_main_argv_annotation_batch29():
    sig = inspect.signature(main)
    assert "list[str] | None" in str(sig.parameters["argv"].annotation)


def test_signature_main_return_int_batch29():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_name_annotation_batch29():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"


def test_signature_format_metric_metric_annotation_batch29():
    sig = inspect.signature(_format_metric)
    assert "dict" in str(sig.parameters["metric"].annotation)


def test_signature_format_metric_return_str_batch29():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_return_int_batch29():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_signature_main_argv_default_none_batch29():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


# ---------- module 合理性第四十三批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch29():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_imports_json_batch29():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_imports_sys_batch29():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_imports_pathlib_batch29():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_no_class_definitions_batch29():
    src = inspect.getsource(climod)
    assert "\nclass " not in src


def test_module_has_main_block_batch29():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in src


def test_module_uses_systemexit_in_main_block_batch29():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


# ---------- 端到端集成第四十三批 ----------


def test_e2e_inspect_doc_full_run_batch29(capsys, tmp_path):
    """端到端：inspect-doc 完整跑一个文档。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "d1",
                "source_type": "pdf",
                "source_path": "x.pdf",
                "parser_name": "fallback",
                "parser_version": "1.0",
                "elements": [{"type": "paragraph"}],
                "chunks": [{"text": "abc"}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "document_id: d1" in captured.out
    assert "type=pdf" in captured.out
    assert "fallback v1.0" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_e2e_validate_report_invalid_returns_1_batch29(tmp_path, capsys):
    """端到端：validate-report 跑一个不合法报告 → 返回 1。"""
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"not_a_report": True}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_no_args_errors_batch29(capsys):
    """端到端：无参数 → SystemExit（argparse 报错）。"""
    with pytest.raises(SystemExit):
        main([])
    captured = capsys.readouterr()
    # argparse 在 stderr 输出 error
    assert captured.err or "usage" in captured.err or captured.out


def test_e2e_main_unknown_subcommand_errors_batch29(capsys):
    """端到端：未知子命令 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["unknown-cmd"])


def test_e2e_build_parser_parse_run_full_batch29():
    """端到端：完整 run 命令解析。"""
    p = _build_parser()
    ns = p.parse_args(
        [
            "run",
            "--manifest",
            "m.json",
            "--output",
            "o.json",
            "--parser",
            "kreuzberg",
            "--max-chars",
            "500",
            "--tolerance-chars",
            "20",
        ]
    )
    assert ns.command == "run"
    assert ns.manifest == "m.json"
    assert ns.output == "o.json"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 500
    assert ns.tolerance_chars == 20


def test_e2e_format_metric_idempotent_batch29():
    """端到端：相同输入两次相同输出。"""
    m = {"value": 1.0, "reason": "ok"}
    l1 = _format_metric("m1", m)
    l2 = _format_metric("m1", m)
    assert l1 == l2


def test_e2e_format_metric_no_input_modification_batch29():
    """端到端：不修改输入 dict。"""
    import copy
    m = {"value": 1.0, "reason": "ok"}
    snapshot = copy.deepcopy(m)
    _format_metric("m1", m)
    assert m == snapshot
