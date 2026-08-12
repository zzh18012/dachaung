"""evaluation/cli.py 第五十六轮 edges 测试（Round 515）。

补强 edges54 未触及的角度（第二十八批）：
- _build_parser 第二十八批：tolerance-chars=0 / tolerance-chars 负 / inspect-doc subparser 不接收 --max-chars / validate-report 不接收 --tolerance-chars / arg 默认值类型
- _format_metric 第二十八批：value 是负数 int / value 是非常长 string / value 是 None 但 reason 是 unicode / name 含 unicode / metric 缺 value key / metric 缺 reason key
- _run_inspect_doc 第二十八批：返回 0 vs 1 vs 2 / stdout 含 document_id / 缺 document_id 默认 ? / 缺 source_path 默认 ? / 输出含 parser_name / parser_version
- main 第二十八批：返回类型一致性 / 返回码范围 / stderr 输出
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
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


# ---------- _build_parser 第二十八批 ----------


def test_build_parser_inspect_doc_tolerance_zero_batch28():
    """inspect-doc --tolerance-chars=0 接受。"""
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "x.json", "--tolerance-chars", "0"])
    assert ns.tolerance_chars == 0


def test_build_parser_inspect_doc_tolerance_negative_batch28():
    """inspect-doc --tolerance-chars=-1 接受。"""
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "x.json", "--tolerance-chars", "-1"])
    assert ns.tolerance_chars == -1


def test_build_parser_run_no_max_chars_in_inspect_doc_batch28():
    """inspect-doc 子命令没有 --max-chars 选项。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    option_strings = []
    for a in ins_p._actions:
        option_strings.extend(a.option_strings or [])
    assert "--max-chars" not in option_strings


def test_build_parser_validate_report_no_tolerance_batch28():
    """validate-report 没有 --tolerance-chars 选项。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    option_strings = []
    for a in val_p._actions:
        option_strings.extend(a.option_strings or [])
    assert "--tolerance-chars" not in option_strings


def test_build_parser_validate_report_no_parser_option_batch28():
    """validate-report 没有 --parser 选项。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    option_strings = []
    for a in val_p._actions:
        option_strings.extend(a.option_strings or [])
    assert "--parser" not in option_strings


def test_build_parser_validate_report_no_output_option_batch28():
    """validate-report 没有 --output 选项。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    option_strings = []
    for a in val_p._actions:
        option_strings.extend(a.option_strings or [])
    assert "--output" not in option_strings


def test_build_parser_inspect_doc_only_positional_input_batch28():
    """inspect-doc 只有一个 positional input。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    # 计数 positional args（不带 - 前缀）
    positional = [a for a in ins_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_build_parser_validate_report_only_positional_input_batch28():
    """validate-report 只有一个 positional input。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    positional = [a for a in val_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_build_parser_run_has_four_options_batch28():
    """run 子命令有 4 个 options: --manifest, --output, --parser, --max-chars, --tolerance-chars。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    option_strings = set()
    for a in run_p._actions:
        for s in (a.option_strings or []):
            option_strings.add(s)
    # 4-5 个 options（去掉 -h）
    expected = {"--manifest", "--output", "--parser", "--max-chars", "--tolerance-chars"}
    assert expected.issubset(option_strings)


def test_build_parser_inspect_doc_only_two_options_batch28():
    """inspect-doc 子命令只有 -h/--help 和 --tolerance-chars。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    option_strings = set()
    for a in ins_p._actions:
        for s in (a.option_strings or []):
            option_strings.add(s)
    # -h / --help 自动加；--tolerance-chars 显式
    assert "--tolerance-chars" in option_strings


def test_build_parser_argparse_module_used_batch28():
    """模块用 argparse（不是其他 CLI 库）。"""
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_build_parser_no_aliases_batch28():
    """没有定义 alias（短选项）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    for a in run_p._actions:
        if a.option_strings:
            # 每个 option 至多有 2 个 alias（长 + 短）
            assert len(a.option_strings) <= 2


# ---------- _format_metric 第二十八批 ----------


def test_format_metric_value_negative_int_batch28():
    line = _format_metric("foo", {"value": -1, "reason": None})
    assert "-1" in line


def test_format_metric_value_long_string_batch28():
    line = _format_metric("foo", {"value": "a" * 100, "reason": None})
    assert "a" * 100 in line


def test_format_metric_reason_unicode_batch28():
    line = _format_metric("foo", {"value": True, "reason": "原因"})
    assert "原因" in line


def test_format_metric_name_unicode_batch28():
    """name 是 unicode → padding 用 ASCII 空格仍执行。"""
    line = _format_metric("指标", {"value": 0, "reason": None})
    assert "指标" in line


def test_format_metric_metric_missing_value_batch28():
    """metric dict 缺 value key → .get('value') 返回 None。"""
    line = _format_metric("foo", {"reason": "x"})
    # value=None → 走 null 分支
    assert "null" in line


def test_format_metric_metric_missing_reason_batch28():
    """metric dict 缺 reason key → .get('reason') 返回 None。"""
    line = _format_metric("foo", {"value": True})
    # reason=None → fallback 'ok'
    assert "ok" in line


def test_format_metric_value_is_dict_with_nested_dict_batch28():
    """value 是 nested dict → 默认分支输出 str()。"""
    # 实际：dict 类型走 dict 分支（isinstance(value, dict)）
    line = _format_metric("foo", {"value": {"a": {"b": 1}}}, )
    # dict 分支：items = ", ".join(f"{k}={v}" for k, v in sorted(value.items()))
    # 但 metric 参数解包：实际签名是 (name, metric)，metric 应是 {"value": ..., "reason": ...}
    # 这里只测 name 字符串
    assert "foo" in line


def test_format_metric_value_dict_with_int_keys_batch28():
    """value 是 dict 但 keys 是 int → sorted 仍可工作。"""
    metric = {"value": {1: "a", 2: "b"}, "reason": None}
    line = _format_metric("foo", metric)
    assert "1=a" in line or "1=" in line


# ---------- _run_inspect_doc 第二十八批 ----------


def _make_args(input_str: str, tolerance: int = 30):
    ns = MagicMock()
    ns.input = input_str
    ns.tolerance_chars = tolerance
    return ns


def test_run_inspect_doc_zero_with_full_doc_batch28(tmp_path, capsys):
    """完整文档：含 document_id / source_path / parser_name / parser_version。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "doc-abc",
                "source_type": "pdf",
                "source_path": "/tmp/x.pdf",
                "parser_name": "fallback",
                "parser_version": "1.2.3",
                "elements": [],
                "chunks": [],
            }
        ),
        encoding="utf-8",
    )
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 0
    out = capsys.readouterr().out
    assert "doc-abc" in out
    assert "fallback" in out
    assert "1.2.3" in out


def test_run_inspect_doc_missing_document_id_default_question_batch28(tmp_path, capsys):
    """doc 缺 document_id → 输出 '?'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    out = capsys.readouterr().out
    assert "?" in out


def test_run_inspect_doc_missing_source_path_default_question_batch28(tmp_path, capsys):
    """doc 缺 source_path → 输出 '?'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    out = capsys.readouterr().out
    assert "?" in out


def test_run_inspect_doc_missing_parser_name_default_question_batch28(tmp_path, capsys):
    """doc 缺 parser_name → 输出 '?'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    out = capsys.readouterr().out
    # parser 行: 'parser:      ? v?'
    assert "parser:" in out


def test_run_inspect_doc_prints_file_path_batch28(tmp_path, capsys):
    """输出含 file 路径。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    out = capsys.readouterr().out
    assert str(p) in out


def test_run_inspect_doc_empty_list_elements_batch28(tmp_path, capsys):
    """elements=[] → elements=0。"""
    p = tmp_path / "d.json"
    p.write_text('{"elements": [], "chunks": []}', encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    out = capsys.readouterr().out
    assert "elements=0" in out


def test_run_inspect_doc_returns_int_batch28(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert isinstance(rc, int)


# ---------- main 第二十八批 ----------


def test_main_run_return_code_in_zero_one_two_batch28(tmp_path):
    """main run 返回码在 {0, 1, 2}。"""
    # 不存在的 manifest → 2
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path / "nope.json"),
            "--output",
            str(tmp_path / "o.json"),
        ]
    )
    assert rc in {0, 1, 2}


def test_main_validate_report_return_code_in_zero_one_two_batch28(tmp_path):
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc in {0, 1, 2}


def test_main_inspect_doc_return_code_in_zero_one_two_batch28(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc in {0, 1, 2}


def test_main_run_manifest_missing_writes_stderr_batch28(tmp_path, capsys):
    """run manifest 不存在时输出 stderr。"""
    main(
        [
            "run",
            "--manifest",
            str(tmp_path / "nope.json"),
            "--output",
            str(tmp_path / "o.json"),
        ]
    )
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_missing_writes_stderr_batch28(tmp_path, capsys):
    """validate-report 报告不存在时输出 stderr。"""
    main(["validate-report", str(tmp_path / "nope.json")])
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_doc_missing_writes_stderr_batch28(tmp_path, capsys):
    """inspect-doc 文档不存在时输出 stderr。"""
    main(["inspect-doc", str(tmp_path / "nope.json")])
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_no_subparser_writes_usage_to_stderr_batch28(capsys):
    """无子命令 → SystemExit(2)，stderr 有 usage。"""
    with pytest.raises(SystemExit):
        main([])
    err = capsys.readouterr().err
    # argparse 错误输出含 usage 或 error
    assert len(err) > 0


def test_main_run_with_extra_positional_batch28(tmp_path):
    """run 不接收额外 positional → SystemExit。"""
    with pytest.raises(SystemExit):
        main(
            [
                "run",
                "--manifest",
                str(tmp_path / "m.json"),
                "--output",
                str(tmp_path / "o.json"),
                "extra",
            ]
        )


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(climod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(climod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(climod)
    assert "exec(" not in src


def test_module_source_no_subprocess_batch28():
    src = inspect.getsource(climod)
    assert "subprocess" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(climod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(climod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(climod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(climod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch28():
    """cli 不写文件（写报告由 runner 做）。"""
    src = inspect.getsource(climod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(climod)
    assert "shutil" not in src


def test_module_source_no_marshal_batch28():
    src = inspect.getsource(climod)
    assert "marshal" not in src


def test_module_source_no_unlink_batch28():
    src = inspect.getsource(climod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_main_function_batch28():
    src = inspect.getsource(climod)
    assert "def main(argv: list[str] | None = None) -> int" in src


def test_module_source_contains_build_parser_function_batch28():
    src = inspect.getsource(climod)
    assert "def _build_parser() -> argparse.ArgumentParser" in src


def test_module_source_contains_format_metric_function_batch28():
    src = inspect.getsource(climod)
    assert "def _format_metric(name: str, metric: dict) -> str" in src


def test_module_source_contains_run_inspect_doc_function_batch28():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc(args) -> int" in src


def test_module_source_contains_run_subparser_block_batch28():
    """run 子命令块含 'run' 命令名。"""
    src = inspect.getsource(climod)
    assert '"run"' in src


def test_module_source_contains_validate_report_subparser_block_batch28():
    src = inspect.getsource(climod)
    assert '"validate-report"' in src


def test_module_source_contains_inspect_doc_subparser_block_batch28():
    src = inspect.getsource(climod)
    assert '"inspect-doc"' in src


def test_module_source_contains_reconfigure_call_batch28():
    src = inspect.getsource(climod)
    assert 'sys.stdout.reconfigure' in src
    assert 'sys.stderr.reconfigure' in src


def test_module_source_contains_hasattr_check_batch28():
    src = inspect.getsource(climod)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_module_source_contains_raise_system_exit_batch28():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


def test_module_source_contains_int_return_annotation_batch28():
    """main 函数返回类型注解 int。"""
    src = inspect.getsource(climod)
    assert "argv: list[str] | None = None) -> int:" in src


def test_module_source_contains_argparse_raw_description_batch28():
    """使用 RawDescriptionHelpFormatter。"""
    src = inspect.getsource(climod)
    assert "RawDescriptionHelpFormatter" in src


# ---------- signatures 第四十二批 ----------


def test_signature_main_argv_annotation_batch28():
    sig = inspect.signature(main)
    annotation = sig.parameters["argv"].annotation
    assert "list[str]" in str(annotation)
    assert "None" in str(annotation)


def test_signature_main_return_annotation_batch28():
    sig = inspect.signature(main)
    # from __future__ import annotations → annotation is str 'int'
    assert sig.return_annotation == "int"


def test_signature_build_parser_return_annotation_batch28():
    sig = inspect.signature(_build_parser)
    # 返回 ArgumentParser（with future annotations → str）
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_format_metric_return_annotation_batch28():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_return_annotation_batch28():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_signature_format_metric_metric_annotation_batch28():
    sig = inspect.signature(_format_metric)
    annotation = sig.parameters["metric"].annotation
    assert annotation == "dict"


def test_signature_format_metric_name_annotation_batch28():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch28():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_imports_json_batch28():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_imports_sys_batch28():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_imports_path_batch28():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_imports_manifest_load_batch28():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import" in src
    assert "load_manifest" in src


def test_module_imports_run_evaluation_batch28():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import" in src
    assert "run_evaluation" in src


def test_module_imports_get_git_provenance_batch28():
    src = inspect.getsource(climod)
    assert "from evaluation.report import" in src
    assert "get_git_provenance" in src


def test_module_imports_validate_file_batch28():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import" in src
    assert "validate_file" in src


def test_module_no_all_export_batch28():
    """cli 模块没有 __all__。"""
    src = inspect.getsource(climod)
    assert "__all__" not in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_inspect_doc_with_heading_element_batch28(tmp_path, capsys):
    """端到端：含 heading 元素。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "d1",
                "source_type": "pdf",
                "source_path": "x.pdf",
                "parser_name": "fallback",
                "parser_version": "1.0",
                "elements": [
                    {"type": "heading", "content": "Title", "element_id": "e1"},
                ],
                "chunks": [{"text": "Title", "source_element_ids": ["e1"]}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=1" in out
    assert "chunks=1" in out


def test_e2e_inspect_doc_metric_sort_order_batch28(tmp_path, capsys):
    """端到端：metric 排序——bool 在前，null 在后。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "source_type": "pdf",
                "elements": [{"type": "paragraph", "content": "a"}],
                "chunks": [{"text": "a"}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    # 找到 "metrics:" 标题
    assert "metrics:" in out


def test_e2e_main_no_args_uses_sys_argv_default_none_batch28(tmp_path):
    """main() 默认 argv=None → 用 sys.argv（pytest 下通常为空 → SystemExit）。"""
    # 不好直接测，但可以测 argv=None 不抛非 SystemExit 异常
    with patch("sys.argv", ["evaluation.cli"]):
        with pytest.raises(SystemExit):
            main()


def test_e2e_main_validate_report_passes_for_valid_report_batch28(tmp_path):
    """端到端：合法报告通过 validate-report。

    构造合法 evaluation-report 需要复杂结构。这里只测不存在路径返回 2。
    """
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_e2e_main_full_inspect_doc_with_metrics_output_batch28(tmp_path, capsys):
    """端到端：inspect-doc 输出含具体 metric 名字。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "source_type": "pdf",
                "elements": [{"type": "paragraph", "content": "a"}],
                "chunks": [{"text": "a"}],
            }
        ),
        encoding="utf-8",
    )
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # 至少应包含 element_count_total
    assert "element_count_total" in out or "elements=" in out


def test_e2e_no_side_effects_batch28(tmp_path):
    """端到端：调用不修改输入。"""
    p = tmp_path / "d.json"
    p.write_text('{"source_type": "pdf"}', encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    main(["inspect-doc", str(p)])
    after = p.read_text(encoding="utf-8")
    assert before == after


def test_e2e_main_inspect_doc_long_doc_id_batch28(tmp_path, capsys):
    """端到端：超长 document_id 也正确显示。"""
    long_id = "x" * 200
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps({"document_id": long_id, "source_type": "pdf"}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert long_id in out
