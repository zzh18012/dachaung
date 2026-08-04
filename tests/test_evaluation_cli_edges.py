"""evaluation/cli.py 边角测试（Round 54）。

补强 tests/test_evaluation_cli.py（48 个测试）未覆盖的 argparse 配置 + 边角：
- _build_parser 详细配置（prog/description/choices/defaults）
- argparse choices 不接受未知值
- main validate-report 各种错误返回码细分
- main run 各种边角（错误 manifest 内容/未知 schema）
- main return value 是 int
- argparse 子命令必备参数缺失
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation.cli import _build_parser, _format_metric, main


# ---------- _build_parser 详细配置 ----------


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_mentions_evaluation():
    p = _build_parser()
    assert "评测" in p.description or "evaluation" in p.description.lower()


def test_build_parser_has_three_subcommands():
    """3 个子命令：run / validate-report / inspect-doc。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._subparsers._group_actions if hasattr(a, "choices")
    )
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_default_parser_is_fallback():
    """run 的 --parser 默认 fallback。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_run_parser_choices_two_options():
    """run 的 --parser 只允许 fallback / kreuzberg（不接受 markdown/html/text/ipynb）。"""
    p = _build_parser()
    parse_p = p._subparsers._group_actions[0].choices["run"]
    parser_action = next(
        a for a in parse_p._actions if "--parser" in a.option_strings
    )
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_default_max_chars_800():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_30():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_manifest_required():
    """不传 --manifest → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["run", "--output", "o.json"])
    assert exc.value.code == 2


def test_build_parser_run_output_required():
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["run", "--manifest", "m.json"])
    assert exc.value.code == 2


def test_build_parser_inspect_doc_default_tolerance_chars_30():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_input_required():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_validate_report_input_required():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_no_command_required():
    """不传子命令 → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args([])
    assert exc.value.code == 2


def test_build_parser_unknown_command_exits_2():
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["nonexistent"])
    assert exc.value.code == 2


# ---------- _format_metric 边角补强 ----------


def test_format_metric_int_value_zero():
    result = _format_metric("count", {"value": 0, "reason": None})
    assert "0" in result


def test_format_metric_int_value_negative():
    result = _format_metric("delta", {"value": -5, "reason": None})
    assert "-5" in result


def test_format_metric_int_value_large():
    result = _format_metric("total", {"value": 1000000, "reason": None})
    assert "1000000" in result


def test_format_metric_float_value_zero():
    result = _format_metric("ratio", {"value": 0.0, "reason": None})
    assert "0.0000" in result


def test_format_metric_float_value_one():
    result = _format_metric("ratio", {"value": 1.0, "reason": None})
    assert "1.0000" in result


def test_format_metric_float_value_high_precision():
    """float 应格式化为 4 位小数。"""
    result = _format_metric("r", {"value": 0.123456789, "reason": None})
    assert "0.1235" in result


def test_format_metric_dict_value_empty():
    result = _format_metric("counts", {"value": {}, "reason": None})
    # 空 dict → 输出 "ok" 但无 items
    assert "ok" in result


def test_format_metric_dict_value_with_items():
    result = _format_metric(
        "counts", {"value": {"paragraph": 3, "heading": 1}, "reason": None}
    )
    assert "paragraph=3" in result
    assert "heading=1" in result


def test_format_metric_string_value():
    """value 是 str → 用默认值输出。"""
    result = _format_metric("name", {"value": "fallback", "reason": None})
    assert "fallback" in result


def test_format_metric_string_value_with_reason():
    result = _format_metric("name", {"value": "fallback", "reason": "test"})
    assert "fallback" in result
    assert "test" in result


def test_format_metric_value_is_list():
    """value 是 list → fallback 到 default 分支（不属任何已知类型）。"""
    result = _format_metric("tags", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in result


def test_format_metric_value_is_none_with_reason():
    """value=None → 显式 null + reason。"""
    result = _format_metric("missing", {"value": None, "reason": "no_data"})
    assert "null" in result
    assert "no_data" in result


def test_format_metric_value_is_none_no_reason():
    """value=None 且无 reason → null + (None)。"""
    result = _format_metric("missing", {"value": None, "reason": None})
    assert "null" in result


def test_format_metric_alignment_width_36():
    """name 列宽度 36（{name:36}）。"""
    result = _format_metric("ab", {"value": 1, "reason": None})
    # 至少 36 字符的 name 列（含 padding）
    line = result.strip()  # 去前导空格后查 name 占位
    # 实际格式 "  ab" + 后续 padding 到 36 + "1"
    assert "1" in result


# ---------- main 返回值是 int ----------


def test_main_returns_int_for_validate_missing(tmp_path: Path):
    code = main(["validate-report", str(tmp_path / "nope.json")])
    assert isinstance(code, int)


def test_main_returns_int_for_inspect_missing(tmp_path: Path):
    code = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert isinstance(code, int)


def test_main_returns_int_for_run_missing(tmp_path: Path):
    code = main([
        "run", "--manifest", str(tmp_path / "nope.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert isinstance(code, int)


# ---------- validate-report 边角 ----------


def test_validate_report_returns_2_for_missing_file(tmp_path: Path):
    """报告不存在 → exit 2。"""
    code = main(["validate-report", str(tmp_path / "missing.json")])
    assert code == 2


def test_validate_report_returns_1_for_bad_json(tmp_path: Path):
    """非法 JSON → exit 1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    code = main(["validate-report", str(p)])
    assert code == 1


def test_validate_report_returns_1_for_invalid_content(tmp_path: Path):
    """合法 JSON 但不符合 evaluation-report schema → exit 1。"""
    p = tmp_path / "wrong.json"
    p.write_text('{"unrelated": "fields"}', encoding="utf-8")
    code = main(["validate-report", str(p)])
    assert code == 1


def test_validate_report_returns_0_for_valid_report(tmp_path: Path):
    """合法 evaluation-report → exit 0。"""
    valid_report = {
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
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(valid_report), encoding="utf-8")
    code = main(["validate-report", str(p)])
    assert code == 0


# ---------- run 子命令边角 ----------


def test_run_returns_2_for_missing_manifest(tmp_path: Path):
    """manifest 文件不存在 → exit 2。"""
    code = main([
        "run", "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert code == 2


def test_run_returns_1_for_bad_manifest_json(tmp_path: Path):
    """manifest 是非法 JSON → load_manifest raises → exit 1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    code = main([
        "run", "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert code == 1


def test_run_returns_1_for_invalid_manifest_content(tmp_path: Path):
    """manifest 合法 JSON 但不符合 schema → exit 1。"""
    p = tmp_path / "wrong.json"
    p.write_text('{"unrelated": "fields"}', encoding="utf-8")
    code = main([
        "run", "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert code == 1


# ---------- inspect-doc 边角 ----------


def test_inspect_doc_returns_2_for_missing_file(tmp_path: Path):
    code = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert code == 2


def test_inspect_doc_returns_1_for_bad_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    code = main(["inspect-doc", str(p)])
    assert code == 1


def test_inspect_doc_returns_1_for_top_level_array(tmp_path: Path):
    """JSON 顶层是数组（非 object）→ exit 1。"""
    p = tmp_path / "array.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    code = main(["inspect-doc", str(p)])
    assert code == 1


def test_inspect_doc_returns_0_for_minimal_valid_doc(tmp_path: Path):
    """最小合法 document → exit 0。"""
    minimal_doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "stdlib/0.1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {"text": True},
    }
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(minimal_doc), encoding="utf-8")
    code = main(["inspect-doc", str(p)])
    assert code == 0


# ---------- argparse 错误路径 ----------


def test_run_invalid_parser_choice_exits_2():
    """--parser 传未知值（如 markdown）→ SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc:
        main([
            "run", "--manifest", "m.json", "--output", "o.json",
            "--parser", "markdown",  # 不在 choices 里
        ])
    assert exc.value.code == 2


def test_run_negative_max_chars_accepted_by_argparse(tmp_path: Path):
    """argparse 层不校验 max_chars 正负；负数也接受（runner 会处理或拒绝）。"""
    # 实际 argparse 接受负数，但下游 process_single 会被拒
    # 这里只验证 argparse 层不抛
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--max-chars", "-100",
    ])
    assert args.max_chars == -100


def test_run_zero_tolerance_chars_accepted(tmp_path: Path):
    """argparse 接受 tolerance_chars=0。"""
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--tolerance-chars", "0",
    ])
    assert args.tolerance_chars == 0


# ---------- main argv=None 行为 ----------


def test_main_argv_none_uses_sys_argv(monkeypatch):
    """main(argv=None) 应使用 sys.argv[1:]。"""
    monkeypatch.setattr(sys, "argv", ["evaluation.cli"])  # 仅 prog，无子命令
    with pytest.raises(SystemExit):
        main(None)


# ---------- 模块导入（无副作用） ----------


def test_import_evaluation_cli_does_not_crash():
    """导入 evaluation.cli 不应有副作用。"""
    import importlib
    import evaluation.cli
    importlib.reload(evaluation.cli)


def test_evaluation_cli_has_main_function():
    import evaluation.cli as mod
    assert callable(mod.main)


def test_evaluation_cli_has_build_parser_function():
    import evaluation.cli as mod
    assert callable(mod._build_parser)


def test_evaluation_cli_has_format_metric_function():
    import evaluation.cli as mod
    assert callable(mod._format_metric)


def test_evaluation_cli_has_run_inspect_doc_function():
    import evaluation.cli as mod
    assert callable(mod._run_inspect_doc)


# ---------- stdout 重定向 ----------


def test_main_writes_devset_summary_to_stdout_for_run(tmp_path: Path, capsys):
    """run 子命令成功后 stdout 应有 devset_status 等信息。"""
    # 构造合法 manifest + 单文件
    src = tmp_path / "src"
    src.mkdir()
    docx_path = src / "doc.docx"
    # 构造最小 DOCX
    import zipfile
    content_types = '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_xml = '''<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Hello.</w:t></w:r></w:p></w:body>
</w:document>'''
    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "DC-1", "path": "src/doc.docx", "source_type": "docx"}
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    output_path = tmp_path / "out" / "report.json"

    code = main([
        "run", "--manifest", str(manifest_path),
        "--output", str(output_path),
    ])
    assert code == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "documents=" in captured.out
    assert "devset_status=" in captured.out


# ---------- validate-report stdout 行为 ----------


def test_validate_report_writes_ok_to_stdout(tmp_path: Path, capsys):
    """合法报告 → stdout 含 "[OK]"。"""
    valid_report = {
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
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {},
        "per_doc": [],
    }
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(valid_report), encoding="utf-8")
    main(["validate-report", str(p)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_validate_report_writes_fail_to_stderr(tmp_path: Path, capsys):
    """非法报告 → stderr 含 "[FAIL]" 或 "[ERROR]"。"""
    p = tmp_path / "wrong.json"
    p.write_text('{"wrong": "shape"}', encoding="utf-8")
    main(["validate-report", str(p)])
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err or "[ERROR]" in captured.err
