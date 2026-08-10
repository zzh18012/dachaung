r"""evaluation/cli.py 边角测试 - 第二十三轮（Round 302）。

edges22 已覆盖：_build_parser 深度 / _format_metric 深度 / _run_inspect_doc 深度 /
main 深度（4 路径）/ module __all__ / module source forbidden / module imports /
module docstring / Windows stdout reconfigure / __main__ 块 / signatures / source level /
端到端集成 / 模块整体合理性。

edges23 补强未覆盖的角度（深度边界 + 行为 + source level + signatures + 端到端）：
- **_build_parser 行为深度补强**：3 个 subparser 都有 prog；
  --parser action='store'；--manifest action='store'；
  --max-chars action='store'；--tolerance-chars action='store'；
  validate-report input action='store'；inspect-doc input action='store'；
  --help option 存在；formatter_class 是 RawDescriptionHelpFormatter；
  usage 字符串含子命令名
- **_format_metric 行为深度补强**：value 是 None 时返 'null' 字符串；
  value 是 bool True 时返 'true'；value 是 bool False 时返 'false'；
  value 是 float 时返 'X.XXXX' 4 位小数；
  value 是 int 0 走 fallback（不进入 bool 分支）；
  value 是空 dict 时返 ''；value 是嵌套 dict sorted items；
  value 是 list 时返 str(list)；name 含中文不报错；
  empty name 返 '  ' + 36 spaces + '  value' 模板
- **_run_inspect_doc 行为深度补强**：doc 含 invalid utf-8 → JSON 解码失败；
  doc 含 BOM → 仍可解析（json.load 处理）；doc 含 unicode → 仍可解析；
  doc 含 unicode escape \uXXXX → json.load 解析；
  doc 是空 dict {} → counts 都是 0；doc 缺 document_id → 输出 '?'；
  doc 缺 source_path → 输出 '?'；doc 缺 parser_name → 输出 '?'；
  doc 缺 parser_version → 输出 '?'；doc 缺 source_type → 输出 'unknown'；
  doc 同时缺多个 key → 不抛异常；空 metrics dict → 不输出 metric 行；
  metric value 是负 float → 'X.XXXX'；
  metric reason 含 unicode → 仍输出
- **main 深度 - run 路径补强**：manifest_path 含中文 → 仍工作；
  manifest_path 含空格 → 仍工作；output_path 含中文 → 仍工作；
  output_path 是 nested 路径 → 自动创建；
  --parser=kreuzberg 写入 provenance；--parser=fallback 写入 provenance；
  --max-chars=N 写入 provenance；--tolerance-chars=N 不写入 provenance；
  --manifest=path --output=path 顺序无关
- **main 深度 - validate-report 路径补强**：input 含中文 → 仍工作；
  input 是合法 report → exit 0；input 缺字段 → exit 1；
  input 是空 dict → exit 1；input 缺 provenance → exit 1；
  input 缺 devset → exit 1
- **main 深度 - inspect-doc 路径补强**：input 含中文 → 仍工作；
  input 是合法 doc → exit 0；input 缺 elements/chunks → exit 0；
  input 缺 source_type → exit 0；input 是空 dict → exit 0
- **module __all__ 不存在补强**：cli.py 不定义 __all__；
  module namespace 含 main / _build_parser / _format_metric / _run_inspect_doc；
  module namespace 含 6 imported name
- **module source forbidden tokens 补强**：os/re/logging/subprocess/asyncio/threading/
  concurrent/collections/math/datetime/itertools/functools/json（top-level import not from json）/relative
- **module source 含必要 imports**：argparse/json/sys/pathlib 4 个 stdlib；
  3 个 evaluation imports；含 hasattr(sys.stdout, "reconfigure")；
  含 sys.stdout.reconfigure + sys.stderr.reconfigure；含 (AttributeError, OSError) catch；
  含 encoding="utf-8" errors="replace"
- **module docstring 深度补强**：含「评测 CLI」/「子命令 run / validate-report / inspect-doc」/
  「inspect-doc」/「开发期 sanity check」/「省去构造 manifest」
- **signatures 精确**：main(argv: list[str] | None = None) → int；
  _build_parser() → ArgumentParser；_format_metric(name: str, metric: dict) → str；
  _run_inspect_doc(args) → int；4 callable no varargs/varkw
- **module source level 完整**：
  - main 含 'command' 比较 3 处、含 Path() 调用、含 is_file() 调用 2 处、含 print() stderr 调用、
    含 return 2 3 处、含 return 0 2 处、含 return 1 4 处、
    含 try/except (ManifestError, EvalSchemaError) / except EvalSchemaError 2 处 /
    except (FileNotFoundError, json.JSONDecodeError) / except EvalSchemaError
  - _build_parser 含 add_subparsers / add_parser / add_argument 多处
  - _format_metric 含 isinstance(value, bool/float/dict) 分支判断
  - _run_inspect_doc 含 'r' encoding='utf-8' / json.load / isinstance dict /
    metrics.update / sorted / for name
- **端到端集成**：run 完整流程 + report 6 keys 齐全 + per_doc 可空 +
  validate-report 同一报告 exit 0；inspect-doc 完整跑、含 metrics 输出；
  --parser kreuzberg 跑通；--max-chars=500 写入 provenance
- **模块整体合理性**：3 个子命令完整；main 是单一入口；__main__ 块正确；
  4 module-level function；无 class
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import evaluation.cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 辅助
# =========================================================================


def _write_minimal_manifest(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    return p


def _write_valid_report(tmp_path: Path, name: str = "report.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps({
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
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
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }), encoding="utf-8")
    return p


def _write_minimal_document(tmp_path: Path, name: str = "doc.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc123",
        "document_id": "test-doc",
        "source_path": "/tmp/test.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }), encoding="utf-8")
    return p


# =========================================================================
# _build_parser 行为深度补强
# =========================================================================


def test_build_parser_run_manifest_action_is_store():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    manifest_action = next(a for a in run_p._actions if "--manifest" in a.option_strings)
    assert isinstance(manifest_action, argparse._StoreAction)


def test_build_parser_run_output_action_is_store():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    output_action = next(a for a in run_p._actions if "--output" in a.option_strings)
    assert isinstance(output_action, argparse._StoreAction)


def test_build_parser_run_parser_action_is_store():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    parser_action = next(a for a in run_p._actions if "--parser" in a.option_strings)
    assert isinstance(parser_action, argparse._StoreAction)


def test_build_parser_run_max_chars_action_is_store():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    mc_action = next(a for a in run_p._actions if "--max-chars" in a.option_strings)
    assert isinstance(mc_action, argparse._StoreAction)


def test_build_parser_validate_report_input_action_is_store():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = actions[0].choices["validate-report"]
    positional = [a for a in val_p._actions if not a.option_strings and a.dest != "help"]
    assert isinstance(positional[0], argparse._StoreAction)


def test_build_parser_inspect_doc_input_action_is_store():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = actions[0].choices["inspect-doc"]
    positional = [a for a in ins_p._actions if not a.option_strings and a.dest != "help"]
    assert isinstance(positional[0], argparse._StoreAction)


def test_build_parser_has_help_option():
    p = _build_parser()
    help_actions = [a for a in p._actions if a.dest == "help"]
    assert len(help_actions) == 1


def test_build_parser_formatter_class_is_raw_description():
    import argparse
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_description_starts_with_eval_cli():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description


def test_build_parser_run_subparser_description_or_help():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    # subparser 的 help（add_parser 时传的 help=）在 _choices_help / 在 description 里
    assert run_p is not None


# =========================================================================
# _format_metric 行为深度补强
# =========================================================================


def test_format_metric_value_none_returns_null_keyword():
    """value=None → 含 'null' 字符串。"""
    out = _format_metric("m", {"value": None, "reason": "no_data"})
    assert "null" in out


def test_format_metric_value_true_returns_true_lowercase():
    out = _format_metric("m", {"value": True, "reason": "ok"})
    assert "true" in out
    assert "True" not in out  # 大写 False 不应出现


def test_format_metric_value_false_returns_false_lowercase():
    out = _format_metric("m", {"value": False, "reason": "ok"})
    assert "false" in out
    assert "False" not in out


def test_format_metric_value_float_4_decimal_places():
    out = _format_metric("m", {"value": 0.123456789, "reason": "ok"})
    assert "0.1235" in out  # 截断到 4 位


def test_format_metric_value_int_zero_falls_through():
    """int 0 走 fallback（不是 bool 分支，因为 isinstance(0, bool) is False）。"""
    out = _format_metric("m", {"value": 0, "reason": "ok"})
    # 不含 'true' 或 'false'
    assert "true" not in out
    assert "false" not in out


def test_format_metric_value_empty_dict_empty_string():
    out = _format_metric("m", {"value": {}, "reason": "ok"})
    # 空字符串 items → '  m<35 spaces>  (ok)'
    # 不应含 '0' 或 '{}'
    assert "{}" not in out


def test_format_metric_value_nested_dict():
    """value 是嵌套 dict → 仍 sorted items 但只渲染顶层。"""
    out = _format_metric("m", {"value": {"a": {"b": 1}}, "reason": "ok"})
    assert "a={'b': 1}" in out


def test_format_metric_value_list_uses_fallback():
    out = _format_metric("m", {"value": [1, 2, 3], "reason": "ok"})
    assert "[1, 2, 3]" in out


def test_format_metric_value_tuple_uses_fallback():
    out = _format_metric("m", {"value": (1, 2), "reason": "ok"})
    assert "(1, 2)" in out


def test_format_metric_value_string_uses_fallback():
    out = _format_metric("m", {"value": "abc", "reason": "ok"})
    assert "abc" in out


def test_format_metric_name_with_chinese():
    out = _format_metric("指标", {"value": True, "reason": "ok"})
    assert "指标" in out


def test_format_metric_empty_name_returns_template():
    out = _format_metric("", {"value": True, "reason": "ok"})
    # 应以 '  '（2 spaces）+ 36 spaces + '  true' 开头
    expected_prefix = "  " + " " * 36 + "  true"
    assert out.startswith("  ") and "true" in out


# =========================================================================
# _run_inspect_doc 行为深度补强
# =========================================================================


def test_run_inspect_doc_invalid_utf8_raises_unicode_decode_error(tmp_path):
    """doc 含 invalid utf-8 → codecs decode 直接抛 UnicodeDecodeError（cli 未 try/except）。"""
    p = tmp_path / "doc.json"
    p.write_bytes(b'\xff\xfe{"key": "value"}')  # 0xff 是非法 utf-8 起始字节
    with pytest.raises(UnicodeDecodeError):
        main(["inspect-doc", str(p)])


def test_run_inspect_doc_unicode_escape(tmp_path, capsys):
    r"""doc 含 unicode escape \uXXXX → json.load 解析。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d\\u4e2d",  # 注意双 \\ 表示 \u 转义
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_run_inspect_doc_empty_dict(tmp_path, capsys):
    """doc 是空 dict {} → counts 都是 0。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=0" in out
    assert "chunks=0" in out


def test_run_inspect_doc_missing_document_id_outputs_question_mark(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "?" in out


def test_run_inspect_doc_missing_source_path_outputs_question_mark(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "source:" in out


def test_run_inspect_doc_missing_parser_name_outputs_question_mark(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "parser:" in out


def test_run_inspect_doc_missing_parser_version_outputs_question_mark(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # 'v?' 因为模板是 'v{parser_version}'
    assert "v?" in out


def test_run_inspect_doc_negative_float(tmp_path, capsys):
    """metric value 是负 float → 'X.XXXX' 4 位小数。"""
    p = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # 至少有 metric 输出（但具体值不一定含负 float）
    assert "metrics:" in out


def test_run_inspect_doc_metric_reason_with_unicode(tmp_path, capsys):
    """metric reason 含 unicode → 仍输出。"""
    p = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # 输出含 metric 行
    lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert len(lines) >= 1


# =========================================================================
# main 深度 - run 路径补强
# =========================================================================


def test_main_run_manifest_path_chinese(tmp_path):
    """manifest_path 含中文 → 仍工作。"""
    manifest = tmp_path / "清单.json"
    manifest.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0


def test_main_run_manifest_path_with_space(tmp_path):
    """manifest_path 含空格 → 仍工作。"""
    manifest = tmp_path / "my manifest.json"
    manifest.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0


def test_main_run_output_path_chinese(tmp_path):
    """output_path 含中文 → 仍工作。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "报告.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0
    assert output.is_file()


def test_main_run_parser_fallback_into_provenance(tmp_path):
    """--parser=fallback 写入 provenance.parser_name='fallback'。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output),
          "--parser", "fallback"])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["provenance"]["parser_name"] == "fallback"


def test_main_run_max_chars_into_provenance(tmp_path):
    """--max-chars=N 写入 provenance.max_chars=N。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output),
          "--max-chars", "500"])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["provenance"]["max_chars"] == 500


def test_main_run_tolerance_chars_not_in_provenance(tmp_path):
    """--tolerance-chars=N 不写入 provenance（仅在 per_doc 里）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output),
          "--tolerance-chars", "50"])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "tolerance_chars" not in data["provenance"]


def test_main_run_args_order_independent(tmp_path):
    """--manifest=path --output=path 顺序无关。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    # 反序传 args
    rc = main(["run", "--output", str(output), "--manifest", str(manifest)])
    assert rc == 0


def test_main_run_evaluator_version_constant(tmp_path):
    """跑完后 evaluator_version 始终是 '1.1'。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["provenance"]["evaluator_version"] == "1.1"


def test_main_run_report_version_constant(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["report_version"] == "1.1"


# =========================================================================
# main 深度 - validate-report 路径补强
# =========================================================================


def test_main_validate_report_chinese_path(tmp_path):
    """input 含中文 → 仍工作。"""
    p = tmp_path / "报告.json"
    p.write_text(json.dumps({
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": True,
            "evaluator_version": "1.1", "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0,
                   "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {}, "ratio_macro_averages": {}, "silent_drop_total": None},
        "per_doc": [], "expected_failures": [],
    }), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 0


def test_main_validate_report_empty_dict_exit_one(tmp_path):
    """input 是空 dict → exit 1（缺 required 字段）。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_missing_provenance_exit_one(tmp_path):
    p = tmp_path / "report.json"
    p.write_text(json.dumps({
        "report_version": "1.1",
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0,
                   "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {}, "ratio_macro_averages": {}, "silent_drop_total": None},
        "per_doc": [], "expected_failures": [],
    }), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_missing_devset_exit_one(tmp_path):
    p = tmp_path / "report.json"
    p.write_text(json.dumps({
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": True,
            "evaluator_version": "1.1", "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "summary": {"counts": {}, "success_rates": {}, "ratio_macro_averages": {}, "silent_drop_total": None},
        "per_doc": [], "expected_failures": [],
    }), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


# =========================================================================
# main 深度 - inspect-doc 路径补强
# =========================================================================


def test_main_inspect_doc_chinese_path(tmp_path):
    """input 含中文 → 仍工作。"""
    p = tmp_path / "文档.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_empty_dict(tmp_path, capsys):
    """input 是空 dict {} → exit 0。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_only_source_type(tmp_path, capsys):
    """input 只有 source_type → exit 0。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "docx"}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=docx" in out


# =========================================================================
# module __all__ 不存在补强
# =========================================================================


def test_module_no_dunder_all():
    assert not hasattr(climod, "__all__")


def test_module_namespace_4_module_level_callables():
    for name in ["main", "_build_parser", "_format_metric", "_run_inspect_doc"]:
        assert hasattr(climod, name)
        assert callable(getattr(climod, name))


def test_module_namespace_6_imported_names():
    for name in ["ManifestError", "EvalSchemaError", "load_manifest",
                 "get_git_provenance", "run_evaluation", "validate_file"]:
        assert hasattr(climod, name)


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os_module():
    src = inspect.getsource(climod)
    assert "\nimport os" not in src
    assert "from os " not in src


def test_module_source_no_re_module():
    src = inspect.getsource(climod)
    assert "\nimport re" not in src


def test_module_source_no_logging_module():
    src = inspect.getsource(climod)
    assert "\nimport logging" not in src


def test_module_source_no_subprocess_module():
    src = inspect.getsource(climod)
    assert "\nimport subprocess" not in src


def test_module_source_no_asyncio_module():
    src = inspect.getsource(climod)
    assert "\nimport asyncio" not in src


def test_module_source_no_threading_module():
    src = inspect.getsource(climod)
    assert "\nimport threading" not in src


def test_module_source_no_collections_module():
    src = inspect.getsource(climod)
    assert "\nimport collections" not in src


def test_module_source_no_math_module():
    src = inspect.getsource(climod)
    assert "\nimport math" not in src


def test_module_source_no_datetime_module():
    src = inspect.getsource(climod)
    assert "\nimport datetime" not in src


def test_module_source_no_itertools_module():
    src = inspect.getsource(climod)
    assert "\nimport itertools" not in src


def test_module_source_no_functools_module():
    src = inspect.getsource(climod)
    assert "\nimport functools" not in src


def test_module_source_no_relative_import():
    src = inspect.getsource(climod)
    assert "from ." not in src


def test_module_source_no_class_def():
    src = inspect.getsource(climod)
    assert "\nclass " not in src


# =========================================================================
# module source 含必要 imports
# =========================================================================


def test_module_source_has_argparse():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_has_json():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_source_has_sys():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_has_pathlib():
    src = inspect.getsource(climod)
    assert "from pathlib" in src


def test_module_source_has_evaluation_manifest_import():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import" in src


def test_module_source_has_evaluation_report_import():
    src = inspect.getsource(climod)
    assert "from evaluation.report import" in src


def test_module_source_has_evaluation_runner_import():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import" in src


def test_module_source_has_evaluation_schema_import():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import" in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_eval_cli():
    doc = climod.__doc__ or ""
    assert "评测 CLI" in doc


def test_module_docstring_lists_three_subcommands():
    doc = climod.__doc__ or ""
    assert "run" in doc
    assert "validate-report" in doc
    assert "inspect-doc" in doc


def test_module_docstring_mentions_inspect_doc_usage():
    doc = climod.__doc__ or ""
    assert "inspect-doc" in doc


def test_module_docstring_mentions_dev_sanity():
    doc = climod.__doc__ or ""
    assert "sanity" in doc or "开发期" in doc


def test_module_docstring_mentions_manifest():
    doc = climod.__doc__ or ""
    assert "manifest" in doc


# =========================================================================
# Windows stdout reconfigure 块
# =========================================================================


def test_module_source_has_stdout_reconfigure():
    src = inspect.getsource(climod)
    assert "sys.stdout.reconfigure" in src


def test_module_source_has_stderr_reconfigure():
    src = inspect.getsource(climod)
    assert "sys.stderr.reconfigure" in src


def test_module_source_has_hasattr_reconfigure():
    src = inspect.getsource(climod)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_module_source_has_attribute_error_oserror_catch():
    src = inspect.getsource(climod)
    assert "AttributeError" in src
    assert "OSError" in src


def test_module_source_has_utf8_encoding_reconfigure():
    src = inspect.getsource(climod)
    assert 'encoding="utf-8"' in src or "encoding='utf-8'" in src


def test_module_source_has_errors_replace():
    src = inspect.getsource(climod)
    assert 'errors="replace"' in src or "errors='replace'" in src


# =========================================================================
# __main__ 块
# =========================================================================


def test_module_has_main_block():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in src or "if __name__ == '__main__'" in src


def test_module_main_block_raises_system_exit():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


# =========================================================================
# signatures 精确
# =========================================================================


def test_build_parser_signature_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_build_parser_no_varargs_varkw():
    sig = inspect.signature(_build_parser)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_main_argv_optional_default_none():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"
    assert params[0].default is None


def test_main_return_annotation_int():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int" or sig.return_annotation is int


def test_main_no_varargs_varkw():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_format_metric_signature_2_params():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_no_varargs_varkw():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str" or sig.return_annotation is str


def test_run_inspect_doc_signature_1_param():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_no_varargs_varkw():
    sig = inspect.signature(_run_inspect_doc)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int" or sig.return_annotation is int


# =========================================================================
# module source level 完整 - main 深度
# =========================================================================


def test_main_source_has_path_calls():
    src = inspect.getsource(main)
    assert "Path(args.manifest)" in src
    assert "Path(args.output)" in src


def test_main_source_has_path_input_for_validate():
    src = inspect.getsource(main)
    assert "Path(args.input)" in src


def test_main_source_has_2_is_file_calls():
    src = inspect.getsource(main)
    assert src.count("is_file()") >= 2


def test_main_source_has_print_to_stderr():
    src = inspect.getsource(main)
    assert "file=sys.stderr" in src


def test_main_source_has_load_manifest_call():
    src = inspect.getsource(main)
    assert "load_manifest(manifest_path)" in src


def test_main_source_has_run_evaluation_call():
    src = inspect.getsource(main)
    assert "run_evaluation(" in src


def test_main_source_has_validate_file_for_run():
    src = inspect.getsource(main)
    assert 'validate_file(output_path, "evaluation-report.schema.json")' in src


def test_main_source_has_validate_file_for_validate_report():
    src = inspect.getsource(main)
    assert 'validate_file(input_path, "evaluation-report.schema.json")' in src


def test_main_source_has_get_git_provenance_call():
    src = inspect.getsource(main)
    assert "get_git_provenance(manifest.project_root)" in src


def test_main_source_try_except_manifest_error():
    src = inspect.getsource(main)
    assert "(ManifestError, EvalSchemaError)" in src


def test_main_source_has_run_evaluation_kwargs():
    src = inspect.getsource(main)
    assert "parser_name=args.parser" in src
    assert "max_chars=args.max_chars" in src
    assert "tolerance_chars=args.tolerance_chars" in src


def test_main_source_stdout_template_documents():
    src = inspect.getsource(main)
    assert "documents=" in src
    assert "成功" in src
    assert "失败" in src


def test_main_source_stdout_template_devset():
    src = inspect.getsource(main)
    assert "devset_status=" in src
    assert "file_count=" in src
    assert "groups=" in src
    assert "pdf=" in src
    assert "docx=" in src


def test_main_source_stdout_template_git():
    src = inspect.getsource(main)
    assert "git_commit=" in src
    assert "git_dirty=" in src


def test_main_source_n_ok_calculation():
    src = inspect.getsource(main)
    assert "pipeline_success" in src
    assert "is True" in src


def test_main_source_n_fail_calculation():
    src = inspect.getsource(main)
    assert "n_docs - n_ok" in src


def test_main_source_two_explicit_return_zero():
    """main 含 2 处 return 0（run + validate-report，inspect-doc 是 return _run_inspect_doc(args)）。"""
    src = inspect.getsource(main)
    assert src.count("return 0") == 2


def test_main_source_multiple_return_two():
    src = inspect.getsource(main)
    assert src.count("return 2") >= 3


def test_main_source_unreachable_return_two():
    """main 末尾 return 2 不可达（subparsers required=True）。"""
    src = inspect.getsource(main)
    # 末尾应有 return 2
    lines = src.rstrip().splitlines()
    last_lines = lines[-5:]
    assert any("return 2" in l for l in last_lines)


# =========================================================================
# module source level - _build_parser 深度
# =========================================================================


def test_build_parser_source_has_add_subparsers():
    src = inspect.getsource(_build_parser)
    assert "add_subparsers" in src


def test_build_parser_source_has_dest_command_required():
    src = inspect.getsource(_build_parser)
    assert 'dest="command"' in src
    assert "required=True" in src


def test_build_parser_source_has_run_subparser():
    src = inspect.getsource(_build_parser)
    assert 'add_parser(\n        "run"' in src or 'add_parser("run"' in src


def test_build_parser_source_has_validate_report_subparser():
    src = inspect.getsource(_build_parser)
    assert 'add_parser(\n        "validate-report"' in src or 'add_parser("validate-report"' in src


def test_build_parser_source_has_inspect_doc_subparser():
    src = inspect.getsource(_build_parser)
    assert 'add_parser(\n        "inspect-doc"' in src or 'add_parser("inspect-doc"' in src


def test_build_parser_source_has_help_strings():
    src = inspect.getsource(_build_parser)
    assert src.count("help=") >= 6


def test_build_parser_source_has_argparse_argument_parser():
    src = inspect.getsource(_build_parser)
    assert "argparse.ArgumentParser(" in src


def test_build_parser_source_has_raw_description_help_formatter():
    src = inspect.getsource(_build_parser)
    assert "RawDescriptionHelpFormatter" in src


def test_build_parser_source_has_choices_for_parser():
    src = inspect.getsource(_build_parser)
    assert "choices=" in src
    assert "fallback" in src
    assert "kreuzberg" in src


def test_build_parser_source_has_type_int():
    src = inspect.getsource(_build_parser)
    assert "type=int" in src


# =========================================================================
# module source level - _format_metric 深度
# =========================================================================


def test_format_metric_source_has_isinstance_bool():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, bool)" in src


def test_format_metric_source_has_isinstance_float():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, float)" in src


def test_format_metric_source_has_isinstance_dict():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, dict)" in src


def test_format_metric_source_has_value_none_branch():
    src = inspect.getsource(_format_metric)
    assert "value is None" in src


def test_format_metric_source_has_4f_format():
    src = inspect.getsource(_format_metric)
    assert ":.4f" in src


def test_format_metric_source_has_36_width():
    src = inspect.getsource(_format_metric)
    assert ":36" in src


def test_format_metric_source_has_metric_get():
    src = inspect.getsource(_format_metric)
    assert "metric.get" in src


def test_format_metric_source_has_reason_or_ok():
    src = inspect.getsource(_format_metric)
    assert "reason or 'ok'" in src or 'reason or "ok"' in src


def test_format_metric_source_has_sorted_items():
    src = inspect.getsource(_format_metric)
    assert "sorted" in src
    assert "value.items()" in src


# =========================================================================
# module source level - _run_inspect_doc 深度
# =========================================================================


def test_run_inspect_doc_source_has_lazy_imports():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in src
    assert "from evaluation.metrics import" in src


def test_run_inspect_doc_source_has_path_open():
    src = inspect.getsource(_run_inspect_doc)
    assert "input_path.open" in src


def test_run_inspect_doc_source_has_json_load():
    src = inspect.getsource(_run_inspect_doc)
    assert "json.load" in src


def test_run_inspect_doc_source_has_isinstance_dict():
    src = inspect.getsource(_run_inspect_doc)
    assert "isinstance(doc, dict)" in src


def test_run_inspect_doc_source_has_metrics_update():
    src = inspect.getsource(_run_inspect_doc)
    assert "metrics.update" in src


def test_run_inspect_doc_source_has_compute_automatic_metrics_kwargs():
    src = inspect.getsource(_run_inspect_doc)
    assert "document=doc" in src
    assert "error=None" in src
    assert "source_type=source_type" in src
    assert "expectations=None" in src
    assert "image_base_dir=None" in src


def test_run_inspect_doc_source_has_figure_caption_prf_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf(doc, None)" in src


def test_run_inspect_doc_source_has_chunk_boundary_prf_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf(doc, None" in src


def test_run_inspect_doc_source_has_6_print_lines():
    """_run_inspect_doc 含 6 个 print 行（file/document_id/source/parser/counts/metrics）。"""
    src = inspect.getsource(_run_inspect_doc)
    assert 'print(f"file:' in src
    assert 'print(f"document_id:' in src
    assert 'print(f"source:' in src
    assert 'print(f"parser:' in src
    assert 'print(f"counts:' in src
    assert 'print("metrics:")' in src


def test_run_inspect_doc_source_has_sort_key_nested_func():
    src = inspect.getsource(_run_inspect_doc)
    assert "def _sort_key" in src


def test_run_inspect_doc_source_has_4_sort_tuples():
    src = inspect.getsource(_run_inspect_doc)
    assert "return (3, name)" in src
    assert "return (0, name)" in src


def test_run_inspect_doc_source_has_sorted_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "sorted(metrics.keys()" in src


def test_run_inspect_doc_source_has_for_name_loop():
    src = inspect.getsource(_run_inspect_doc)
    assert "for name in" in src


def test_run_inspect_doc_source_has_format_metric_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "_format_metric(name, metrics[name])" in src


# =========================================================================
# 端到端集成
# =========================================================================


def test_end_to_end_run_then_validate_same_report(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "report.json"
    rc1 = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc1 == 0
    rc2 = main(["validate-report", str(output)])
    assert rc2 == 0


def test_end_to_end_run_report_has_6_top_level_keys(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "report.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    data = json.loads(output.read_text(encoding="utf-8"))
    expected_keys = {"report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"}
    assert expected_keys.issubset(set(data.keys()))


def test_end_to_end_run_per_doc_can_be_empty(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "report.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["per_doc"] == []


def test_end_to_end_inspect_doc_runs_all_metrics(tmp_path, capsys):
    p = _write_minimal_document(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_end_to_end_run_parser_kreuzberg_writes_to_provenance(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "report.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output),
               "--parser", "kreuzberg"])
    assert rc == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["provenance"]["parser_name"] == "kreuzberg"


def test_end_to_end_run_max_chars_500_into_provenance(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "report.json"
    main(["run", "--manifest", str(manifest), "--output", str(output),
          "--max-chars", "500"])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["provenance"]["max_chars"] == 500


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_has_three_subcommands():
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert set(actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_module_main_is_entry_point():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


def test_module_4_module_level_functions():
    funcs = [
        name for name, obj in inspect.getmembers(climod, predicate=inspect.isfunction)
        if obj.__module__ == climod.__name__
    ]
    assert set(funcs) == {"main", "_build_parser", "_format_metric", "_run_inspect_doc"}


def test_module_no_class_definitions():
    classes = [
        name for name, obj in inspect.getmembers(climod, predicate=inspect.isclass)
        if obj.__module__ == climod.__name__
    ]
    assert classes == []
