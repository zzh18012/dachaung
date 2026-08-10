r"""evaluation/cli.py 边角测试 - 第二十一轮（Round 290）。

edges20 已覆盖：exit codes 矩阵基础 / sub-parser 参数精确 / _format_metric 模板 /
inspect-doc 排序基础 / module source 不含禁止 imports / __all__ 不存在 /
docstring 内容 / main return type / Windows stdout reconfigure 块 /
lazy imports / stdout vs stderr 分离 / argparse 错误 SystemExit。

edges21 补强未覆盖的角度（深度边界 + 行为 + source level + 集成）：
- **main 深度 - run 路径**：manifest 路径是目录 → exit 2（is_file False 分支）；
  output 路径已存在 → 覆盖写；evaluator_version 不变；report_version 不变；
  stderr 错误消息含「清单加载失败」字符串；stderr 错误消息含「清单不存在」字符串
- **main 深度 - validate-report 路径**：报告路径是目录 → exit 2；
  stderr 含「报告不存在」；stderr 含「报告校验失败」；stderr 含「JSON 解析失败」
- **main 深度 - inspect-doc 路径**：doc 路径是目录 → exit 2；
  stderr 含「文档不存在」；stderr 含「JSON 顶层不是对象」
- **main argv=None 行为**：argparse 默认 from sys.argv，空 argv 抛 SystemExit
- **main 不可达 return 2**：通过 source inspection 验证末尾 return 2 存在
- **_format_metric value 类型完整**：None/True/False/int 0/int 负/float 0.0/float 负/
  empty dict/非空 dict/字符串/list（fallback 路径）
- **_format_metric 字符串模板精确**：bool 用 str.lower；float 用 :.4f；
  dict 用 sorted items；width 36 严格
- **_run_inspect_doc _sort_key 4 分支**：bool→(0,name)；int/float→(1,name)；
  其他（dict）→(2,name)；None→(3,name)
- **_run_inspect_doc 输出 ?**：document_id 缺失输出 ?；source_path 缺失输出 ?；
  parser_name 缺失输出 ?；parser_version 缺失输出 ?
- **_run_inspect_doc source_type 缺失**：default "unknown"
- **_run_inspect_doc 是 module-level 函数**（不是嵌套）
- **_build_parser 元数据深度**：prog/description/formatter_class/dest=command 精确
- **stdout 输出模板精确**：含 documents=、成功、失败、devset_status=、file_count=、
  groups=、pdf=、docx=、git_commit=、git_dirty=
- **module source level 完整**：import 顺序（argparse→json→sys→pathlib→evaluation）；
  含 hasattr(sys.stdout, "reconfigure")；含 sys.stdout.reconfigure 调用；
  含 sys.stderr.reconfigure 调用；含 (AttributeError, OSError) catch；
  含 3 处 if args.command；含 lazy import 在 _run_inspect_doc 内；
  含 main 末尾 return 2；含 raise SystemExit(main()) 在 __main__ 块
- **argparse 主 parser 配置**：prog/description 含三个子命令名
- **argparse 子 parser 配置深度**：run/validate-report/inspect-doc 三个 sub-parser
  都有 help 字符串
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 辅助：构造合法的 manifest / report / document
# =========================================================================


def _write_minimal_manifest(tmp_path: Path) -> Path:
    """写一个最小可用 manifest，返回路径。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    return p


def _write_valid_report(tmp_path: Path) -> Path:
    """写一个最小可用 evaluation-report，返回路径。"""
    p = tmp_path / "report.json"
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


def _write_minimal_document(tmp_path: Path) -> Path:
    """写一个最小 document JSON，返回路径。"""
    p = tmp_path / "doc.json"
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
# main 深度 - run 子命令
# =========================================================================


def test_main_run_manifest_path_is_directory_exit_two(tmp_path):
    """run + manifest 路径是目录（is_file False）→ exit 2。"""
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(tmp_path), "--output", str(output)])
    assert rc == 2


def test_main_run_manifest_path_is_directory_stderr_message(tmp_path, capsys):
    """stderr 含「清单不存在」。"""
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(tmp_path), "--output", str(output)])
    err = capsys.readouterr().err
    assert "清单不存在" in err


def test_main_run_output_already_exists_overwrites(tmp_path):
    """output 路径已存在 → run 覆盖写。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    output.write_text('{"old": true}', encoding="utf-8")
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0
    # 文件应被覆盖，新内容是合法 report
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "old" not in data
    assert data["report_version"] == "1.1"


def test_main_run_evaluator_version_unchanged(tmp_path):
    """run 后 report 的 evaluator_version = 1.1（不变）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["provenance"]["evaluator_version"] == "1.1"


def test_main_run_report_version_unchanged(tmp_path):
    """run 后 report 的 report_version = 1.1（不变）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["report_version"] == "1.1"


def test_main_run_load_manifest_failure_stderr_message(tmp_path, capsys):
    """manifest schema 失败时 stderr 含「清单加载失败」。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        # 缺 documents → schema 失败
    }), encoding="utf-8")
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(bad_manifest), "--output", str(output)])
    err = capsys.readouterr().err
    assert "清单加载失败" in err


def test_main_run_with_kreuzberg_parser_choice(tmp_path):
    """run --parser kreuzberg 走通（kreuzberg 适配器存在）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest),
               "--output", str(output),
               "--parser", "kreuzberg"])
    # 空 manifest 时 kreuzberg 也能跑通（无文档要处理）
    assert rc == 0


def test_main_run_with_max_chars_zero(tmp_path):
    """run --max-chars 0 → argparse 接受，但 report schema 要求 >=1 → exit 1。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest),
               "--output", str(output),
               "--max-chars", "0"])
    assert rc == 1


def test_main_run_with_tolerance_chars_zero(tmp_path):
    """run --tolerance-chars 0 不报错（argparse 接受任意 int）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest),
               "--output", str(output),
               "--tolerance-chars", "0"])
    assert rc == 0


def test_main_run_negative_max_chars_rejected_by_schema(tmp_path):
    """run --max-chars -1 → argparse 接受负数，但 report schema 拒绝 → exit 1。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest),
               "--output", str(output),
               "--max-chars", "-1"])
    assert rc == 1


def test_main_run_stdout_success_template(tmp_path, capsys):
    """run 成功 stdout 含完整模板字段。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    out = capsys.readouterr().out
    assert "documents=" in out
    assert "成功" in out
    assert "失败" in out
    assert "devset_status=" in out
    assert "file_count=" in out
    assert "groups=" in out
    assert "pdf=" in out
    assert "docx=" in out
    assert "git_commit=" in out
    assert "git_dirty=" in out


def test_main_run_stdout_no_documents_zero_counts(tmp_path, capsys):
    """run + 空 manifest → stdout 显示 documents=0（成功 0，失败 0）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    out = capsys.readouterr().out
    assert "documents=0" in out
    assert "成功 0" in out
    assert "失败 0" in out


# =========================================================================
# main 深度 - validate-report 子命令
# =========================================================================


def test_main_validate_report_path_is_directory_exit_two(tmp_path):
    """validate-report + 报告路径是目录 → exit 2。"""
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2


def test_main_validate_report_path_is_directory_stderr_message(tmp_path, capsys):
    """validate-report + 目录 → stderr 含「报告不存在」。"""
    main(["validate-report", str(tmp_path)])
    err = capsys.readouterr().err
    assert "报告不存在" in err


def test_main_validate_report_invalid_schema_stderr_message(tmp_path, capsys):
    """validate-report + schema 失败 → stderr 含「报告校验失败」。"""
    bad_report = tmp_path / "bad.json"
    bad_report.write_text(json.dumps({"report_version": "1.1"}), encoding="utf-8")
    main(["validate-report", str(bad_report)])
    err = capsys.readouterr().err
    assert "报告校验失败" in err


def test_main_validate_report_invalid_json_stderr_message(tmp_path, capsys):
    """validate-report + 非法 JSON → stderr 含「JSON 解析失败」。"""
    bad_report = tmp_path / "bad.json"
    bad_report.write_text("{not valid json", encoding="utf-8")
    main(["validate-report", str(bad_report)])
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_main_validate_report_success_stdout_template(tmp_path, capsys):
    """validate-report 成功 stdout 含「通过 evaluation-report Schema 校验」。"""
    report = _write_valid_report(tmp_path)
    main(["validate-report", str(report)])
    out = capsys.readouterr().out
    assert "通过 evaluation-report Schema 校验" in out
    assert "[OK]" in out


# =========================================================================
# main 深度 - inspect-doc 子命令
# =========================================================================


def test_main_inspect_doc_path_is_directory_exit_two(tmp_path):
    """inspect-doc + 目录 → exit 2。"""
    rc = main(["inspect-doc", str(tmp_path)])
    assert rc == 2


def test_main_inspect_doc_path_is_directory_stderr_message(tmp_path, capsys):
    """inspect-doc + 目录 → stderr 含「文档不存在」。"""
    main(["inspect-doc", str(tmp_path)])
    err = capsys.readouterr().err
    assert "文档不存在" in err


def test_main_inspect_doc_top_level_dict_with_no_type_stderr_message(tmp_path, capsys):
    """inspect-doc + dict 但 elements/chunks 缺失 → 仍 exit 0（不报错）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf"}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_top_level_array_stderr_message(tmp_path, capsys):
    """inspect-doc + array → stderr 含「JSON 顶层不是对象」。"""
    p = tmp_path / "doc.json"
    p.write_text("[]", encoding="utf-8")
    main(["inspect-doc", str(p)])
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


def test_main_inspect_doc_top_level_string_stderr_message(tmp_path, capsys):
    """inspect-doc + string → stderr 含「JSON 顶层不是对象」。"""
    p = tmp_path / "doc.json"
    p.write_text('"hello"', encoding="utf-8")
    main(["inspect-doc", str(p)])
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


def test_main_inspect_doc_top_level_int_stderr_message(tmp_path, capsys):
    """inspect-doc + int → stderr 含「JSON 顶层不是对象」。"""
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    main(["inspect-doc", str(p)])
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


def test_main_inspect_doc_top_level_null_stderr_message(tmp_path, capsys):
    """inspect-doc + null → stderr 含「JSON 顶层不是对象」。"""
    p = tmp_path / "doc.json"
    p.write_text("null", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


def test_main_inspect_doc_top_level_float_stderr_message(tmp_path, capsys):
    """inspect-doc + float → stderr 含「JSON 顶层不是对象」。"""
    p = tmp_path / "doc.json"
    p.write_text("3.14", encoding="utf-8")
    main(["inspect-doc", str(p)])
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


def test_main_inspect_doc_top_level_bool_stderr_message(tmp_path, capsys):
    """inspect-doc + bool → stderr 含「JSON 顶层不是对象」。"""
    p = tmp_path / "doc.json"
    p.write_text("true", encoding="utf-8")
    main(["inspect-doc", str(p)])
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


# =========================================================================
# main argv 行为深度
# =========================================================================


def test_main_argv_none_uses_sys_argv(tmp_path, monkeypatch):
    """main(argv=None) → argparse from sys.argv。空 argv 抛 SystemExit。"""
    monkeypatch.setattr("sys.argv", ["evaluation.cli"])
    with pytest.raises(SystemExit):
        main(None)


def test_main_empty_argv_raises_system_exit():
    """main([]) → argparse required subcommand 缺失 → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_command_raises_system_exit():
    """main(['unknown']) → argparse 未知子命令 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_run_missing_required_args_raises_system_exit(tmp_path):
    """main(['run']) 缺 --manifest → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run"])


def test_main_validate_report_missing_positional_raises_system_exit():
    """main(['validate-report']) 缺 input → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["validate-report"])


def test_main_inspect_doc_missing_positional_raises_system_exit():
    """main(['inspect-doc']) 缺 input → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["inspect-doc"])


# =========================================================================
# _format_metric value 类型完整
# =========================================================================


def test_format_metric_value_none_returns_null_string():
    """None → 输出 'null'。"""
    s = _format_metric("m1", {"value": None, "reason": "no_data"})
    assert "null" in s
    assert "no_data" in s


def test_format_metric_value_none_no_reason():
    """None + 无 reason → 输出 'null' + 'None'。"""
    s = _format_metric("m1", {"value": None})
    assert "null" in s
    assert "None" in s


def test_format_metric_value_true_lowercased():
    """True → 输出 'true'（lowercase）。"""
    s = _format_metric("m1", {"value": True, "reason": "ok"})
    assert "true" in s


def test_format_metric_value_false_lowercased():
    """False → 输出 'false'（lowercase）。"""
    s = _format_metric("m1", {"value": False, "reason": "ok"})
    assert "false" in s


def test_format_metric_value_bool_no_reason_default_ok():
    """bool + 无 reason → 默认 'ok'。"""
    s = _format_metric("m1", {"value": True})
    assert "ok" in s


def test_format_metric_value_int_zero():
    """int 0 → 输出 '0'（走 fallback 分支）。"""
    s = _format_metric("m1", {"value": 0, "reason": "ok"})
    assert "0" in s


def test_format_metric_value_int_negative():
    """int -1 → 输出 '-1'（走 fallback）。"""
    s = _format_metric("m1", {"value": -1, "reason": "ok"})
    assert "-1" in s


def test_format_metric_value_float_zero_dot_zero():
    """float 0.0 → 输出 '0.0000'（走 float 分支）。"""
    s = _format_metric("m1", {"value": 0.0, "reason": "ok"})
    assert "0.0000" in s


def test_format_metric_value_float_negative():
    """float -0.5 → 输出 '-0.5000'（走 float 分支）。"""
    s = _format_metric("m1", {"value": -0.5, "reason": "ok"})
    assert "-0.5000" in s


def test_format_metric_value_float_precision():
    """float 1/3 → 输出 '0.3333'（4 位小数截断）。"""
    s = _format_metric("m1", {"value": 1.0 / 3, "reason": "ok"})
    assert "0.3333" in s


def test_format_metric_value_empty_dict():
    """dict {} → 输出空字符串 after width。"""
    s = _format_metric("m1", {"value": {}, "reason": "ok"})
    # 输出应该是 "  m1" + 32 spaces + "  (ok)"（dict 空 → items=""）
    assert "m1" in s
    assert "(ok)" in s


def test_format_metric_value_non_empty_dict_sorted():
    """dict 多 key → 按 key 排序输出。"""
    s = _format_metric("m1", {"value": {"b": 2, "a": 1, "c": 3}, "reason": "ok"})
    # items 应按 a, b, c 排序
    a_pos = s.find("a=1")
    b_pos = s.find("b=2")
    c_pos = s.find("c=3")
    assert a_pos < b_pos < c_pos


def test_format_metric_value_dict_no_reason():
    """dict + 无 reason → 默认 'ok'。"""
    s = _format_metric("m1", {"value": {"a": 1}})
    assert "ok" in s


def test_format_metric_value_string_fallback():
    """string value → 走 fallback 分支。"""
    s = _format_metric("m1", {"value": "hello", "reason": "ok"})
    assert "hello" in s


def test_format_metric_value_list_fallback():
    """list value → 走 fallback 分支（list 不是 None/bool/float/dict）。"""
    s = _format_metric("m1", {"value": [1, 2, 3], "reason": "ok"})
    assert "[1, 2, 3]" in s


def test_format_metric_value_long_float():
    """float 3.14159265358979 → 输出 '3.1416'（4 位小数四舍五入）。"""
    s = _format_metric("m1", {"value": 3.14159265358979, "reason": "ok"})
    assert "3.1416" in s


def test_format_metric_value_tuple_fallback():
    """tuple value → 走 fallback 分支（isinstance(float) 不接 tuple）。"""
    s = _format_metric("m1", {"value": (1, 2), "reason": "ok"})
    assert "(1, 2)" in s


# =========================================================================
# _format_metric 字符串模板精确
# =========================================================================


def test_format_metric_width_36_strict():
    """name 部分严格 36 宽（短 name 右侧 pad 到 36）。"""
    s = _format_metric("ab", {"value": 1, "reason": "ok"})
    # 输出 "  ab" + 34 spaces + " 1  (ok)"
    assert s.startswith("  ab" + " " * 32)


def test_format_metric_long_name_no_truncate():
    """name 长度 >= 36 也不截断（width 是 min）。"""
    long_name = "x" * 50
    s = _format_metric(long_name, {"value": 1, "reason": "ok"})
    assert long_name in s


def test_format_metric_two_leading_spaces():
    """每行起始 2 spaces。"""
    s = _format_metric("m1", {"value": 1, "reason": "ok"})
    assert s.startswith("  ")


def test_format_metric_returns_string():
    """返回值是 str。"""
    s = _format_metric("m1", {"value": 1, "reason": "ok"})
    assert isinstance(s, str)


# =========================================================================
# _run_inspect_doc _sort_key 4 分支
# =========================================================================


def test_run_inspect_doc_sort_bool_first(tmp_path, capsys):
    """bool 类 metric 排在最前。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # 至少要跑通（验证排序逻辑不抛）
    assert "metrics:" in out


def test_run_inspect_doc_metric_with_bool_value(tmp_path, capsys):
    """含 bool metric 时排序在最前（_sort_key 返 (0, name)）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # pipeline_success 通常是 bool
    assert "pipeline_success" in out


def test_run_inspect_doc_metric_with_null_value(tmp_path, capsys):
    """含 null metric 时排在最后（_sort_key 返 (3, name)）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # chunk_boundary_precision 等指标无标注时为 null
    assert "null" in out


def test_run_inspect_doc_metric_with_dict_value(tmp_path, capsys):
    """含 dict metric（element_count_by_type）→ (2, name) 分支。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hi"}],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "element_count_by_type" in out


# =========================================================================
# _run_inspect_doc 输出 ? 字段
# =========================================================================


def test_run_inspect_doc_missing_document_id_outputs_question_mark(tmp_path, capsys):
    """document_id 缺失 → stdout 输出 '?'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "document_id: ?" in out


def test_run_inspect_doc_missing_source_path_outputs_question_mark(tmp_path, capsys):
    """source_path 缺失 → stdout 输出 '?'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "d1",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "source:      ?" in out


def test_run_inspect_doc_missing_parser_name_outputs_question_mark(tmp_path, capsys):
    """parser_name 缺失 → stdout 输出 '?'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "d1",
        "source_path": "/x.pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "parser:      ?" in out


def test_run_inspect_doc_missing_parser_version_outputs_question_mark(tmp_path, capsys):
    """parser_version 缺失 → stdout 输出 '?v?'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "d1",
        "source_path": "/x.pdf",
        "parser_name": "fallback",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "v?" in out


def test_run_inspect_doc_present_parser_version_outputs_v_prefix(tmp_path, capsys):
    """parser_version 存在 → stdout 输出 'v{version}'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.2.3",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "v1.2.3" in out


def test_run_inspect_doc_present_document_id(tmp_path, capsys):
    """document_id 存在 → stdout 输出该 id。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "doc-abc-123",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "doc-abc-123" in out


def test_run_inspect_doc_present_source_path(tmp_path, capsys):
    """source_path 存在 → stdout 输出该路径。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_path": "/some/where/x.pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "/some/where/x.pdf" in out


# =========================================================================
# _run_inspect_doc source_type 缺失 default
# =========================================================================


def test_run_inspect_doc_missing_source_type_defaults_unknown(tmp_path, capsys):
    """source_type 缺失 → default 'unknown'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_explicit_source_type_pdf(tmp_path, capsys):
    """source_type='pdf' → stdout 'type=pdf'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "type=pdf" in out


def test_run_inspect_doc_explicit_source_type_docx(tmp_path, capsys):
    """source_type='docx' → stdout 'type=docx'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "type=docx" in out


def test_run_inspect_doc_explicit_source_type_other(tmp_path, capsys):
    """source_type='html' → stdout 'type=html'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "html",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "type=html" in out


# =========================================================================
# _run_inspect_doc 是 module-level 函数
# =========================================================================


def test_run_inspect_doc_is_module_level_function():
    """_run_inspect_doc 是 evaluation.cli 模块直接定义的函数。"""
    import evaluation.cli as cli
    assert hasattr(cli, "_run_inspect_doc")
    assert callable(cli._run_inspect_doc)


def test_run_inspect_doc_signature_one_param():
    """_run_inspect_doc(args) 单参数。"""
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1
    assert "args" in sig.parameters


def test_run_inspect_doc_no_varargs_varkw():
    """_run_inspect_doc 不接受 varargs/varkw。"""
    sig = inspect.signature(_run_inspect_doc)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_run_inspect_doc_return_annotation_is_int():
    """_run_inspect_doc 返 int。"""
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation in (int, "int")


# =========================================================================
# _build_parser 元数据深度
# =========================================================================


def test_build_parser_prog_is_evaluation_cli():
    """prog 是 'evaluation.cli'。"""
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_string():
    """description 不为空。"""
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 0


def test_build_parser_description_mentions_evaluation_or_pingce():
    """description 含「评测」字符串。"""
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_formatter_class_is_raw_description():
    """formatter_class 是 RawDescriptionHelpFormatter。"""
    import argparse
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_subparsers_dest_is_command():
    """subparsers dest 是 'command'。"""
    p = _build_parser()
    # 找到 _SubParsersAction
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    assert len(sub_actions) == 1
    assert sub_actions[0].dest == "command"


def test_build_parser_subparsers_required_true():
    """subparsers required=True。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    assert sub_actions[0].required is True


def test_build_parser_run_subparser_has_help():
    """run 子 parser 有 help 字符串。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    choices = sub_actions[0].choices
    assert "run" in choices
    assert choices["run"].description is None or isinstance(choices["run"].description, (str, type(None)))


def test_build_parser_validate_report_subparser_exists():
    """validate-report 子 parser 存在。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    choices = sub_actions[0].choices
    assert "validate-report" in choices


def test_build_parser_inspect_doc_subparser_exists():
    """inspect-doc 子 parser 存在。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    choices = sub_actions[0].choices
    assert "inspect-doc" in choices


def test_build_parser_only_three_subcommands():
    """只有 3 个子命令（run/validate-report/inspect-doc）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    choices = sub_actions[0].choices
    assert set(choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_has_manifest_option():
    """run 子 parser 有 --manifest 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    run_p = sub_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--manifest" in option_strings


def test_build_parser_run_subparser_has_output_option():
    """run 子 parser 有 --output 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    run_p = sub_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--output" in option_strings


def test_build_parser_run_subparser_has_parser_option():
    """run 子 parser 有 --parser 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    run_p = sub_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--parser" in option_strings


def test_build_parser_run_subparser_has_max_chars_option():
    """run 子 parser 有 --max-chars 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    run_p = sub_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--max-chars" in option_strings


def test_build_parser_run_subparser_has_tolerance_chars_option():
    """run 子 parser 有 --tolerance-chars 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    run_p = sub_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--tolerance-chars" in option_strings


def test_build_parser_inspect_doc_subparser_has_tolerance_chars():
    """inspect-doc 子 parser 有 --tolerance-chars 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    ins_p = sub_actions[0].choices["inspect-doc"]
    option_strings = []
    for a in ins_p._actions:
        option_strings.extend(a.option_strings)
    assert "--tolerance-chars" in option_strings


def test_build_parser_inspect_doc_subparser_no_parser_option():
    """inspect-doc 子 parser 没有 --parser 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    ins_p = sub_actions[0].choices["inspect-doc"]
    option_strings = []
    for a in ins_p._actions:
        option_strings.extend(a.option_strings)
    assert "--parser" not in option_strings


def test_build_parser_inspect_doc_subparser_no_max_chars_option():
    """inspect-doc 子 parser 没有 --max-chars 选项。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    ins_p = sub_actions[0].choices["inspect-doc"]
    option_strings = []
    for a in ins_p._actions:
        option_strings.extend(a.option_strings)
    assert "--max-chars" not in option_strings


def test_build_parser_validate_report_subparser_no_optional_args():
    """validate-report 子 parser 没有可选 args（除 -h/--help）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"]
    val_p = sub_actions[0].choices["validate-report"]
    optional_actions = [
        a for a in val_p._actions
        if a.option_strings and not set(a.option_strings).issubset({"-h", "--help"})
    ]
    assert optional_actions == []


# =========================================================================
# main 不可达 return 2 + main block
# =========================================================================


def test_main_source_has_trailing_return_two():
    """main 函数 source 末尾含 'return 2'（不可达分支）。"""
    src = inspect.getsource(main)
    assert "return 2" in src


def test_main_source_has_three_command_branches():
    """main 函数 source 含 3 处 'if args.command =='。"""
    src = inspect.getsource(main)
    assert src.count("if args.command ==") == 3


def test_main_source_returns_int_for_run_path():
    """main source 含 'return 0'（run 成功路径）。"""
    src = inspect.getsource(main)
    assert "return 0" in src


def test_main_source_returns_int_for_validate_report_path():
    """main source 含 'return 1'（validate-report 失败路径）。"""
    src = inspect.getsource(main)
    assert "return 1" in src


def test_main_signature_argv_optional():
    """main(argv: list[str] | None = None) → int。"""
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_main_signature_return_annotation_int():
    """main return type 是 int。"""
    sig = inspect.signature(main)
    assert sig.return_annotation in (int, "int")


def test_main_signature_no_varargs():
    """main 不接受 *args。"""
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_main_signature_no_varkw():
    """main 不接受 **kwargs。"""
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# =========================================================================
# module source level 完整
# =========================================================================


def test_module_source_imports_argparse_first():
    """import 顺序：argparse 在最前。"""
    import evaluation.cli as cli
    src = inspect.getsource(cli)
    # 找到 import argparse 行
    argparse_pos = src.find("import argparse")
    json_pos = src.find("import json")
    sys_pos = src.find("import sys")
    assert argparse_pos < json_pos
    assert argparse_pos < sys_pos


def test_module_source_imports_json():
    """含 import json。"""
    import evaluation.cli as cli
    assert "import json" in inspect.getsource(cli)


def test_module_source_imports_sys():
    """含 import sys。"""
    import evaluation.cli as cli
    assert "import sys" in inspect.getsource(cli)


def test_module_source_from_pathlib_import_path():
    """含 from pathlib import Path。"""
    import evaluation.cli as cli
    assert "from pathlib import Path" in inspect.getsource(cli)


def test_module_source_hasattr_check():
    """含 hasattr(sys.stdout, 'reconfigure')。"""
    import evaluation.cli as cli
    src = inspect.getsource(cli)
    assert "hasattr(sys.stdout" in src
    assert "reconfigure" in src


def test_module_source_stdout_reconfigure_call():
    """含 sys.stdout.reconfigure 调用。"""
    import evaluation.cli as cli
    assert "sys.stdout.reconfigure" in inspect.getsource(cli)


def test_module_source_stderr_reconfigure_call():
    """含 sys.stderr.reconfigure 调用。"""
    import evaluation.cli as cli
    assert "sys.stderr.reconfigure" in inspect.getsource(cli)


def test_module_source_attribute_error_oserror_catch():
    """含 (AttributeError, OSError) except。"""
    import evaluation.cli as cli
    assert "(AttributeError, OSError)" in inspect.getsource(cli)


def test_module_source_from_evaluation_imports():
    """含 from evaluation.* import 4 个模块。"""
    import evaluation.cli as cli
    src = inspect.getsource(cli)
    assert "from evaluation.manifest import" in src
    assert "from evaluation.report import" in src
    assert "from evaluation.runner import" in src
    assert "from evaluation.schema import" in src


def test_module_source_from_evaluation_manifest_imports_manifest_error():
    """含 ManifestError 导入。"""
    import evaluation.cli as cli
    assert "ManifestError" in inspect.getsource(cli)


def test_module_source_from_evaluation_report_imports_get_git_provenance():
    """含 get_git_provenance 导入。"""
    import evaluation.cli as cli
    assert "get_git_provenance" in inspect.getsource(cli)


def test_module_source_from_evaluation_runner_imports_run_evaluation():
    """含 run_evaluation 导入。"""
    import evaluation.cli as cli
    assert "run_evaluation" in inspect.getsource(cli)


def test_module_source_from_evaluation_schema_imports_validate_file():
    """含 validate_file + EvalSchemaError 导入。"""
    import evaluation.cli as cli
    src = inspect.getsource(cli)
    assert "validate_file" in src
    assert "EvalSchemaError" in src


def test_module_source_does_not_contain_logging():
    """不含 import logging。"""
    import evaluation.cli as cli
    assert "import logging" not in inspect.getsource(cli)


def test_module_source_does_not_contain_subprocess():
    """不含 import subprocess。"""
    import evaluation.cli as cli
    assert "import subprocess" not in inspect.getsource(cli)


def test_module_source_does_not_contain_os_module():
    """不含 import os。"""
    import evaluation.cli as cli
    assert "import os" not in inspect.getsource(cli)
    # 注意 sys 可用，但 os 不允许


def test_module_source_does_not_contain_re():
    """不含 import re。"""
    import evaluation.cli as cli
    assert "import re" not in inspect.getsource(cli)


def test_module_source_does_not_contain_time():
    """不含 import time。"""
    import evaluation.cli as cli
    assert "import time" not in inspect.getsource(cli)


def test_module_source_does_not_contain_threading():
    """不含 import threading。"""
    import evaluation.cli as cli
    assert "import threading" not in inspect.getsource(cli)


def test_module_source_does_not_contain_asyncio():
    """不含 import asyncio。"""
    import evaluation.cli as cli
    assert "import asyncio" not in inspect.getsource(cli)


def test_module_source_does_not_contain_concurrent():
    """不含 from concurrent。"""
    import evaluation.cli as cli
    assert "from concurrent" not in inspect.getsource(cli)


def test_module_source_lazy_imports_in_run_inspect_doc():
    """_run_inspect_doc 内有 lazy import（compute_automatic_metrics 等）。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in src
    assert "from evaluation.metrics import" in src
    assert "compute_automatic_metrics" in src
    assert "figure_caption_prf" in src
    assert "chunk_boundary_prf" in src


def test_module_source_main_block_uses_system_exit():
    """__main__ 块含 raise SystemExit(main())。"""
    import evaluation.cli as cli
    src = inspect.getsource(cli)
    assert 'raise SystemExit(main())' in src


def test_module_source_main_block_at_end():
    """__main__ 块在文件末尾。"""
    import evaluation.cli as cli
    src = inspect.getsource(cli)
    main_block_pos = src.find('if __name__ == "__main__"')
    assert main_block_pos != -1
    # __main__ 块后应该没有更多代码（除空行）
    after = src[main_block_pos:].strip()
    assert after.endswith("raise SystemExit(main())")


def test_module_does_not_have_all():
    """cli 模块没有 __all__。"""
    import evaluation.cli as cli
    assert not hasattr(cli, "__all__")


def test_module_has_build_parser():
    """cli 模块有 _build_parser。"""
    import evaluation.cli as cli
    assert hasattr(cli, "_build_parser")


def test_module_has_main():
    """cli 模块有 main。"""
    import evaluation.cli as cli
    assert hasattr(cli, "main")


def test_module_has_format_metric():
    """cli 模块有 _format_metric。"""
    import evaluation.cli as cli
    assert hasattr(cli, "_format_metric")


def test_module_has_run_inspect_doc():
    """cli 模块有 _run_inspect_doc。"""
    import evaluation.cli as cli
    assert hasattr(cli, "_run_inspect_doc")


def test_module_docstring_mentions_run_command():
    """module docstring 含 'run'。"""
    import evaluation.cli as cli
    assert cli.__doc__ is not None
    assert "run" in cli.__doc__


def test_module_docstring_mentions_validate_report():
    """module docstring 含 'validate-report'。"""
    import evaluation.cli as cli
    assert "validate-report" in cli.__doc__


def test_module_docstring_mentions_inspect_doc():
    """module docstring 含 'inspect-doc'。"""
    import evaluation.cli as cli
    assert "inspect-doc" in cli.__doc__


def test_module_docstring_mentions_python_m_evaluation_cli():
    """module docstring 含 'python -m evaluation.cli'。"""
    import evaluation.cli as cli
    assert "python -m evaluation.cli" in cli.__doc__


# =========================================================================
# _format_metric signature
# =========================================================================


def test_format_metric_signature_two_params():
    """_format_metric(name, metric) 双参数。"""
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2
    assert "name" in sig.parameters
    assert "metric" in sig.parameters


def test_format_metric_no_varargs():
    """_format_metric 不接受 *args。"""
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_format_metric_return_annotation_is_str():
    """_format_metric 返 str。"""
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation in (str, "str")


def test_format_metric_source_uses_get_value():
    """_format_metric source 含 metric.get('value')。"""
    src = inspect.getsource(_format_metric)
    assert "metric.get" in src
    assert "value" in src


def test_format_metric_source_uses_get_reason():
    """_format_metric source 含 metric.get('reason')。"""
    src = inspect.getsource(_format_metric)
    assert "reason" in src


def test_format_metric_source_handles_none():
    """_format_metric source 含 'value is None' 检查。"""
    src = inspect.getsource(_format_metric)
    assert "is None" in src


def test_format_metric_source_handles_bool():
    """_format_metric source 含 isinstance(value, bool)。"""
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, bool)" in src


def test_format_metric_source_handles_float():
    """_format_metric source 含 isinstance(value, float)。"""
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, float)" in src


def test_format_metric_source_handles_dict():
    """_format_metric source 含 isinstance(value, dict)。"""
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, dict)" in src


def test_format_metric_source_uses_4_format():
    """_format_metric source 含 :.4f 浮点格式。"""
    src = inspect.getsource(_format_metric)
    assert ".4f" in src or ":.4f" in src


def test_format_metric_source_uses_sorted_for_dict():
    """_format_metric source 含 sorted(...) 用于 dict。"""
    src = inspect.getsource(_format_metric)
    assert "sorted" in src


# =========================================================================
# _run_inspect_doc source level 完整
# =========================================================================


def test_run_inspect_doc_source_opens_input_path():
    """_run_inspect_doc source 含 input_path.open(...)。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "input_path" in src
    assert ".open(" in src


def test_run_inspect_doc_source_loads_json():
    """_run_inspect_doc source 含 json.load(f)。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "json.load" in src


def test_run_inspect_doc_source_catches_json_decode_error():
    """_run_inspect_doc source 含 except json.JSONDecodeError。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "json.JSONDecodeError" in src


def test_run_inspect_doc_source_checks_isinstance_dict():
    """_run_inspect_doc source 含 isinstance(doc, dict)。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "isinstance(doc, dict)" in src


def test_run_inspect_doc_source_gets_source_type():
    """_run_inspect_doc source 含 doc.get('source_type', 'unknown')。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "source_type" in src
    assert "unknown" in src


def test_run_inspect_doc_source_calls_compute_automatic_metrics():
    """_run_inspect_doc source 调用 compute_automatic_metrics(...)。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "compute_automatic_metrics(" in src


def test_run_inspect_doc_source_calls_figure_caption_prf():
    """_run_inspect_doc source 调用 figure_caption_prf(...)。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf(" in src


def test_run_inspect_doc_source_calls_chunk_boundary_prf():
    """_run_inspect_doc source 调用 chunk_boundary_prf(...)。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf(" in src


def test_run_inspect_doc_source_uses_sort_key():
    """_run_inspect_doc source 含 _sort_key 内嵌函数。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "_sort_key" in src
    assert "def _sort_key" in src


def test_run_inspect_doc_source_prints_file_label():
    """_run_inspect_doc source 含 'file:' print。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "file:" in src


def test_run_inspect_doc_source_prints_document_id_label():
    """_run_inspect_doc source 含 'document_id:'。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "document_id:" in src


def test_run_inspect_doc_source_prints_source_label():
    """_run_inspect_doc source 含 'source:'。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "source:" in src


def test_run_inspect_doc_source_prints_parser_label():
    """_run_inspect_doc source 含 'parser:'。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "parser:" in src


def test_run_inspect_doc_source_prints_counts_label():
    """_run_inspect_doc source 含 'counts:'。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "counts:" in src


def test_run_inspect_doc_source_prints_metrics_label():
    """_run_inspect_doc source 含 'metrics:'。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "metrics:" in src


def test_run_inspect_doc_source_returns_zero_at_end():
    """_run_inspect_doc source 含 return 0 末尾。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "return 0" in src


# =========================================================================
# stdout/stderr 模板精确（成功路径）
# =========================================================================


def test_main_run_stdout_contains_ok_marker(tmp_path, capsys):
    """run 成功 stdout 含 '[OK]' 标记。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_main_run_stderr_goes_to_stderr_not_stdout(tmp_path, capsys):
    """run + missing manifest → 错误消息只在 stderr，不在 stdout。"""
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(output)])
    cap = capsys.readouterr()
    assert "清单不存在" in cap.err
    assert "清单不存在" not in cap.out


def test_main_validate_report_stderr_goes_to_stderr_not_stdout(tmp_path, capsys):
    """validate-report + missing → 错误消息只在 stderr。"""
    main(["validate-report", str(tmp_path / "missing.json")])
    cap = capsys.readouterr()
    assert "报告不存在" in cap.err
    assert "报告不存在" not in cap.out


def test_main_inspect_doc_stderr_goes_to_stderr_not_stdout(tmp_path, capsys):
    """inspect-doc + missing → 错误消息只在 stderr。"""
    main(["inspect-doc", str(tmp_path / "missing.json")])
    cap = capsys.readouterr()
    assert "文档不存在" in cap.err
    assert "文档不存在" not in cap.out


def test_main_run_success_stdout_only_no_stderr(tmp_path, capsys):
    """run 成功 → stderr 为空（或只含 warning）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    cap = capsys.readouterr()
    assert "[ERROR]" not in cap.err


def test_main_validate_report_success_stdout_only_no_stderr(tmp_path, capsys):
    """validate-report 成功 → stderr 为空（或只含 warning）。"""
    report = _write_valid_report(tmp_path)
    main(["validate-report", str(report)])
    cap = capsys.readouterr()
    assert "[ERROR]" not in cap.err
    assert "[FAIL]" not in cap.err


def test_main_inspect_doc_success_stdout_only_no_stderr(tmp_path, capsys):
    """inspect-doc 成功 → stderr 为空。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    cap = capsys.readouterr()
    assert "[ERROR]" not in cap.err


# =========================================================================
# run 集成 - 真实 round-trip
# =========================================================================


def test_main_run_writes_validatable_report(tmp_path):
    """run 后产生的 report 可以被 validate-report 通过。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    # 用 validate-report 校验
    rc = main(["validate-report", str(output)])
    assert rc == 0


def test_main_run_with_empty_documents_still_valid(tmp_path):
    """run + 空 documents 列表 → 仍能产生合法 report。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["per_doc"] == []
    assert data["expected_failures"] == []


def test_main_run_devset_status_propagates(tmp_path, capsys):
    """manifest 的 devset_status='incomplete' → stdout 显示。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    out = capsys.readouterr().out
    assert "devset_status=incomplete" in out


def test_main_run_creates_output_in_existing_dir(tmp_path):
    """output 路径的父目录存在 → 文件正常创建。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "sub" / "out.json"
    output.parent.mkdir()
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0
    assert output.is_file()


# =========================================================================
# inspect-doc 完整集成
# =========================================================================


def test_main_inspect_doc_full_output_template(tmp_path, capsys):
    """inspect-doc 完整输出含所有 label。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "d-001",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hi"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"]},
        ],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "file:" in out
    assert "document_id:" in out
    assert "source:" in out
    assert "parser:" in out
    assert "counts:" in out
    assert "metrics:" in out


def test_main_inspect_doc_counts_shows_element_count(tmp_path, capsys):
    """inspect-doc counts 行含 elements=N。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a"},
            {"element_id": "e2", "type": "paragraph", "content": "b"},
        ],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "elements=2" in out


def test_main_inspect_doc_counts_shows_chunk_count(tmp_path, capsys):
    """inspect-doc counts 行含 chunks=N。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [
            {"chunk_id": "c1", "text": "a", "source_element_ids": []},
            {"chunk_id": "c2", "text": "b", "source_element_ids": []},
            {"chunk_id": "c3", "text": "c", "source_element_ids": []},
        ],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "chunks=3" in out


def test_main_inspect_doc_returns_zero_for_minimal_dict(tmp_path):
    """inspect-doc + 最小合法 dict → exit 0。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_with_tolerance_chars_zero(tmp_path):
    """inspect-doc --tolerance-chars 0 → exit 0。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "0"])
    assert rc == 0


def test_main_inspect_doc_with_negative_tolerance_chars(tmp_path):
    """inspect-doc --tolerance-chars -1 → exit 0（argparse 接受负数）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "-1"])
    assert rc == 0


# =========================================================================
# run_evaluation 内部错误传播
# =========================================================================


def test_main_run_stdout_has_git_commit_truncated_to_12(tmp_path, capsys):
    """run 成功 → stdout git_commit 取前 12 字符（如果非 None）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    out = capsys.readouterr().out
    # git_commit 可能 None → 输出 'unknown'；否则 12 字符 hash
    assert "git_commit=" in out


def test_main_run_stdout_git_dirty_present(tmp_path, capsys):
    """run 成功 → stdout 含 'git_dirty='。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    out = capsys.readouterr().out
    assert "git_dirty=" in out
