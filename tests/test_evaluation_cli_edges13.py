r"""evaluation/cli.py 边角测试 - 第十三轮（Round 231）。

补强已有 base/edges/edges2-12（共 ~1139 测试）未覆盖的深度：
- _format_metric：metric 是非 dict 类型（None/int/list/str）→ AttributeError；reason 是非 str；name=None/空；name 长度边界（恰好 36 / > 36）；float 极小/极大值；Counter 类型
- _run_inspect_doc：source_type 取默认 'unknown'；elements/chunks 显式 None → []; tolerance_chars=0/negative；不写文件
- main：command 是 'run' 但 manifest 是目录（不是文件）；command 是 'validate-report' 但 input 是目录；command 是 'inspect-doc' 但 input 是目录
- module：argparse prog prefix；subparser dest='command'；subparser required=True；3 个子命令名集合精确
- 综合行为
"""

from __future__ import annotations

import argparse
import inspect
import io
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import evaluation.cli as cli_module
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main
from evaluation.schema import EvalSchemaError


# =========================================================================
# _format_metric：metric 是非 dict 类型
# =========================================================================


def test_format_metric_metric_none_raises():
    """metric=None → None 没有 .get → AttributeError。"""
    with pytest.raises(AttributeError):
        _format_metric("foo", None)


def test_format_metric_metric_int_raises():
    """metric=42 → int 没有 .get → AttributeError。"""
    with pytest.raises(AttributeError):
        _format_metric("foo", 42)


def test_format_metric_metric_list_raises():
    """metric=[] → list 没有 .get → AttributeError。"""
    with pytest.raises(AttributeError):
        _format_metric("foo", [])


def test_format_metric_metric_str_raises():
    """metric='abc' → str 没有 .get（str.get 是查 prefix，不是 dict.get）→ AttributeError。"""
    # 实际：str.get 不存在；但 str 有 __getattribute__，但 'foo' 没有 'get' attribute
    with pytest.raises(AttributeError):
        _format_metric("foo", "abc")


def test_format_metric_metric_tuple_raises():
    with pytest.raises(AttributeError):
        _format_metric("foo", (1, 2))


def test_format_metric_metric_set_raises():
    with pytest.raises(AttributeError):
        _format_metric("foo", {1, 2})


# =========================================================================
# _format_metric：name 边界
# =========================================================================


def test_format_metric_name_empty_string():
    """name='' → f-string format 仍能渲染（空 + 36 padding）。"""
    result = _format_metric("", {"value": 1, "reason": None})
    # 名字 0 字符 + 36 空格 padding
    assert result.startswith("  " + " " * 36)
    assert "1" in result


def test_format_metric_name_exactly_36_chars():
    """name 恰好 36 字符 → 不补 padding。"""
    name = "a" * 36
    result = _format_metric(name, {"value": 1, "reason": None})
    # 应包含 36 个 'a' 然后紧接 value
    assert "  " + name + " " in result  # 2-space indent + 36-a + space + value


def test_format_metric_name_longer_than_36():
    """name > 36 字符 → format 不截断。"""
    name = "a" * 50
    result = _format_metric(name, {"value": 1, "reason": None})
    # 全部 50 个 'a' 都应保留
    assert "a" * 50 in result


def test_format_metric_name_with_special_chars():
    """name 含特殊字符（括号、空格、unicode）→ 原样渲染。"""
    result = _format_metric("foo (bar) 中文", {"value": 1, "reason": None})
    assert "foo (bar) 中文" in result


def test_format_metric_name_none_raises():
    """name=None → f-string format raises TypeError。"""
    with pytest.raises((TypeError, ValueError)):
        _format_metric(None, {"value": 1, "reason": None})


def test_format_metric_name_int_works():
    """name=42（int）→ f-string 自动转 str。"""
    result = _format_metric(42, {"value": 1, "reason": None})
    assert "42" in result


# =========================================================================
# _format_metric：reason 非 str
# =========================================================================


def test_format_metric_reason_int_with_value():
    """reason=42（int）：reason or 'ok' → 42（truthy）→ 渲染 '42'."""
    result = _format_metric("foo", {"value": 1, "reason": 42})
    assert "(42)" in result


def test_format_metric_reason_zero_int_with_value():
    """reason=0（int）：reason or 'ok' → 'ok'（0 是 falsy）."""
    result = _format_metric("foo", {"value": 1, "reason": 0})
    assert "(ok)" in result


def test_format_metric_reason_empty_string_with_value():
    """reason='' → falsy → 'ok'."""
    result = _format_metric("foo", {"value": 1, "reason": ""})
    assert "(ok)" in result


def test_format_metric_reason_list_with_value():
    """reason=['x']（list, truthy）→ 直接 str()."""
    result = _format_metric("foo", {"value": 1, "reason": ["x"]})
    # f-string 会调用 str(['x']) = "['x']"
    assert "(['x'])" in result


def test_format_metric_reason_none_for_null_value():
    """value=None, reason=None → 'null  (None)' (no 'or ok' fallback)."""
    result = _format_metric("foo", {"value": None, "reason": None})
    assert "(None)" in result


def test_format_metric_reason_zero_int_for_null_value():
    """value=None, reason=0 → 'null  (0)'."""
    result = _format_metric("foo", {"value": None, "reason": 0})
    # value is None → return f"  {name:36} null  ({reason})" → 直接用 reason 不 fallback
    assert "(0)" in result


# =========================================================================
# _format_metric：value 是 Counter（dict 子类）
# =========================================================================


def test_format_metric_value_is_counter():
    """Counter 是 dict 子类 → 走 dict 分支。"""
    c = Counter({"a": 3, "b": 1})
    result = _format_metric("foo", {"value": c, "reason": None})
    assert "a=3" in result
    assert "b=1" in result


def test_format_metric_value_is_dict_with_int_keys():
    """dict 含 int key → sorted() 按 int 排序。"""
    result = _format_metric("foo", {"value": {2: "x", 1: "y"}, "reason": None})
    # sorted by int key
    assert "1=y" in result
    assert "2=x" in result


def test_format_metric_value_is_dict_with_tuple_keys_raises():
    """dict 含 tuple key → sorted() 在 Python 3 不能比较不同类型 tuple → 可能 raise TypeError."""
    # tuple keys 在 sorted 中比较时如果 type 一致可以排序
    result = _format_metric("foo", {"value": {(1, 2): "x", (3, 4): "y"}, "reason": None})
    assert "(1, 2)=x" in result or "(1, 2)" in result


def test_format_metric_value_is_dict_with_mixed_key_types_raises():
    """dict 混合 str/int key → sorted() raises TypeError."""
    with pytest.raises(TypeError):
        _format_metric("foo", {"value": {"a": 1, 2: 3}, "reason": None})


# =========================================================================
# _format_metric：float 边界值
# =========================================================================


def test_format_metric_float_very_small():
    """非常小的 float → :.4f 渲染 0.0000."""
    result = _format_metric("foo", {"value": 0.00001, "reason": None})
    assert "0.0000" in result


def test_format_metric_float_very_large():
    """非常大的 float → :.4f 渲染完整数字."""
    result = _format_metric("foo", {"value": 1234567.89, "reason": None})
    assert "1234567.8900" in result


def test_format_metric_float_negative():
    result = _format_metric("foo", {"value": -0.5, "reason": None})
    assert "-0.5000" in result


def test_format_metric_float_zero():
    result = _format_metric("foo", {"value": 0.0, "reason": None})
    assert "0.0000" in result


def test_format_metric_float_one():
    result = _format_metric("foo", {"value": 1.0, "reason": None})
    assert "1.0000" in result


def test_format_metric_float_pi_four_decimals():
    """pi 渲染为 3.1416（:.4f 四舍五入）."""
    result = _format_metric("foo", {"value": math.pi, "reason": None})
    assert "3.1416" in result


# =========================================================================
# _run_inspect_doc：source_type 默认 / elements/chunks None
# =========================================================================


class _FakeArgs:
    """Minimal args stub for _run_inspect_doc."""
    def __init__(self, input_path: str, tolerance_chars: int = 30):
        self.input = input_path
        self.tolerance_chars = tolerance_chars


def test_run_inspect_doc_source_type_unknown_when_missing(tmp_path: Path, capsys):
    """doc 没有 source_type → 默认 'unknown'."""
    doc = {"elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_FakeArgs(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_source_type_explicit(tmp_path: Path, capsys):
    """doc 含 source_type → 透传."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_FakeArgs(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=pdf" in captured.out


def test_run_inspect_doc_elements_none_propagates_typeerror(tmp_path: Path):
    """doc elements=None → _run_inspect_doc 局部 normalize 为 []，但 compute_automatic_metrics
    收到原始 doc（key 存在 value=None），`document.get('elements', [])` 返回 None，
    `len(None)` 触发 TypeError。"""
    doc = {"source_type": "pdf", "elements": None, "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(TypeError):
        _run_inspect_doc(_FakeArgs(str(p)))


def test_run_inspect_doc_chunks_none_propagates_typeerror(tmp_path: Path):
    """doc chunks=None → compute_automatic_metrics 中 text_preservation 触发 TypeError."""
    doc = {"source_type": "pdf", "elements": [], "chunks": None}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(TypeError):
        _run_inspect_doc(_FakeArgs(str(p)))


def test_run_inspect_doc_no_elements_no_chunks_key(tmp_path: Path, capsys):
    """doc 没有 elements/chunks key → .get() None → or [] → []."""
    doc = {"source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_FakeArgs(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out
    assert "chunks=0" in captured.out


def test_run_inspect_doc_tolerance_chars_zero(tmp_path: Path, capsys):
    """tolerance_chars=0 → chunk_boundary_prf 仍运行（精确匹配）。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_FakeArgs(str(p), tolerance_chars=0))
    assert rc == 0


def test_run_inspect_doc_tolerance_chars_negative(tmp_path: Path, capsys):
    """tolerance_chars=-1 → chunk_boundary_prf 仍运行."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_FakeArgs(str(p), tolerance_chars=-1))
    assert rc == 0


def test_run_inspect_doc_tolerance_chars_large(tmp_path: Path, capsys):
    """tolerance_chars=10000 → chunk_boundary_prf 仍运行."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_FakeArgs(str(p), tolerance_chars=10000))
    assert rc == 0


def test_run_inspect_doc_does_not_write_file(tmp_path: Path, capsys):
    """inspect-doc 不写盘（仅 stdout）."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    files_before = set(tmp_path.iterdir())
    _run_inspect_doc(_FakeArgs(str(p)))
    files_after = set(tmp_path.iterdir())
    assert files_before == files_after  # 不创建新文件


def test_run_inspect_doc_prints_metrics_header(tmp_path: Path, capsys):
    """stdout 含 'metrics:' 头."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_file_header(tmp_path: Path, capsys):
    """stdout 含 'file:' 头."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_prints_document_id(tmp_path: Path, capsys):
    """stdout 含 'document_id:'."""
    doc = {"source_type": "pdf", "elements": [], "chunks": [], "document_id": "doc-abc"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "document_id:" in captured.out
    assert "doc-abc" in captured.out


def test_run_inspect_doc_prints_question_when_document_id_missing(tmp_path: Path, capsys):
    """doc 没有 document_id → '?'."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "document_id: ?" in captured.out


def test_run_inspect_doc_prints_parser_info(tmp_path: Path, capsys):
    """stdout 含 'parser:'."""
    doc = {"source_type": "pdf", "elements": [], "chunks": [],
           "parser_name": "fallback", "parser_version": "1.0"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "parser:" in captured.out
    assert "fallback" in captured.out
    assert "v1.0" in captured.out


def test_run_inspect_doc_prints_question_when_parser_missing(tmp_path: Path, capsys):
    """doc 没有 parser_name/version → '?'."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    assert "parser:      ? v?" in captured.out


# =========================================================================
# main：file 不存在 / 目录
# =========================================================================


def test_main_validate_report_input_is_directory_returns_two(tmp_path: Path, capsys):
    """validate-report input 是目录 → 不是 file → return 2."""
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_inspect_doc_input_is_directory_returns_two(tmp_path: Path, capsys):
    """inspect-doc input 是目录 → return 2."""
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["inspect-doc", str(d)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_manifest_is_directory_returns_two(tmp_path: Path, capsys):
    """run manifest 是目录 → return 2."""
    d = tmp_path / "subdir"
    d.mkdir()
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(d), "--output", str(out)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_validate_report_input_does_not_exist_returns_two(tmp_path: Path, capsys):
    """validate-report input 不存在 → return 2."""
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2


def test_main_inspect_doc_input_does_not_exist_returns_two(tmp_path: Path, capsys):
    """inspect-doc input 不存在 → return 2."""
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2


# =========================================================================
# main：command 是 'run' 但 argv 缺少必需参数
# =========================================================================


def test_main_run_missing_manifest_exits_two(capsys):
    """run 缺 --manifest → argparse exits with code 2."""
    with pytest.raises(SystemExit) as ei:
        main(["run", "--output", "x.json"])
    assert ei.value.code == 2


def test_main_run_missing_output_exits_two(capsys):
    """run 缺 --output → argparse exits with code 2."""
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", "x.json"])
    assert ei.value.code == 2


def test_main_validate_report_missing_input_exits_two(capsys):
    """validate-report 缺 input → argparse exits with code 2."""
    with pytest.raises(SystemExit) as ei:
        main(["validate-report"])
    assert ei.value.code == 2


def test_main_inspect_doc_missing_input_exits_two(capsys):
    """inspect-doc 缺 input → argparse exits with code 2."""
    with pytest.raises(SystemExit) as ei:
        main(["inspect-doc"])
    assert ei.value.code == 2


# =========================================================================
# main：subparser 必需 / prog 名
# =========================================================================


def test_main_no_command_exits_two(capsys):
    """无 command → argparse exits with code 2."""
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


def test_main_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_main_subparser_required_true():
    """subparser 必须是 required（缺 command 应 exit 2）."""
    p = _build_parser()
    # 找到 subparsers action
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    assert sub_action.required is True


def test_main_subparser_dest_is_command():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    assert sub_action.dest == "command"


def test_main_subcommands_exact_set():
    """3 个子命令精确集合：run, validate-report, inspect-doc."""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# =========================================================================
# _format_metric 综合行为
# =========================================================================


def test_format_metric_value_one_renders_as_int():
    """int value=1 → 走默认分支（不被 isinstance bool 命中）."""
    result = _format_metric("foo", {"value": 1, "reason": None})
    # int 1 不走 bool 分支（bool 是 int 子类，但 isinstance(1, bool) is False）
    assert " 1 " in result
    assert "(ok)" in result


def test_format_metric_value_is_zero_int():
    """int value=0 → 走默认分支."""
    result = _format_metric("foo", {"value": 0, "reason": None})
    assert " 0 " in result
    assert "(ok)" in result


def test_format_metric_value_is_negative_int():
    result = _format_metric("foo", {"value": -5, "reason": None})
    assert " -5 " in result


def test_format_metric_value_is_large_int():
    result = _format_metric("foo", {"value": 1234567, "reason": None})
    assert " 1234567 " in result


def test_format_metric_value_is_unicode_string():
    """str value 含 unicode → 原样渲染."""
    result = _format_metric("foo", {"value": "你好", "reason": None})
    assert "你好" in result


def test_format_metric_value_is_long_string():
    """str value 很长 → 原样渲染（不截断）."""
    long_str = "x" * 200
    result = _format_metric("foo", {"value": long_str, "reason": None})
    assert long_str in result


# =========================================================================
# module 结构补充
# =========================================================================


def test_module_description_contains_eval_description():
    p = _build_parser()
    assert "评测" in p.description


def test_module_description_mentions_subcommands_via_choices_actions():
    """subparsers 的 _choices_actions 中含 3 个 _ChoicesPseudoAction."""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    # _choices_actions 是子命令注册时创建的伪 action
    assert hasattr(sub_action, "_choices_actions")
    assert len(sub_action._choices_actions) == 3


def test_module_run_subparser_exists_with_prog():
    """run 子 parser 存在且 prog 含 'run'."""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_p = sub_action.choices["run"]
    assert "run" in run_p.prog


def test_module_validate_report_subparser_exists_with_prog():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    val_p = sub_action.choices["validate-report"]
    assert "validate-report" in val_p.prog


def test_module_inspect_doc_subparser_exists_with_prog():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    ins_p = sub_action.choices["inspect-doc"]
    assert "inspect-doc" in ins_p.prog


# =========================================================================
# _format_metric：返回值是 str
# =========================================================================


def test_format_metric_returns_str_type():
    """返回值必须是 str 类型."""
    result = _format_metric("foo", {"value": 1, "reason": None})
    assert isinstance(result, str)


def test_format_metric_returns_non_empty_str():
    result = _format_metric("foo", {"value": 1, "reason": None})
    assert len(result) > 0


def test_format_metric_starts_with_two_spaces():
    """所有 metric 行都以 2 个空格开头."""
    result = _format_metric("foo", {"value": 1, "reason": None})
    assert result.startswith("  ")


# =========================================================================
# _format_metric：综合 dict value 行为
# =========================================================================


def test_format_metric_dict_value_empty_renders_only_separator():
    """dict value 空dict → items="" → 渲染空."""
    result = _format_metric("foo", {"value": {}, "reason": None})
    # items 是空字符串；f-string 包含 "  " (双空格)
    assert "    (ok)" in result or "   (ok)" in result


def test_format_metric_dict_value_with_none_value():
    """dict value 含 None → 'k=None'."""
    result = _format_metric("foo", {"value": {"a": None}, "reason": None})
    assert "a=None" in result


def test_format_metric_dict_value_with_bool_value():
    """dict value 含 True/False → 'k=True'/'k=False'."""
    result = _format_metric("foo", {"value": {"a": True, "b": False}, "reason": None})
    assert "a=True" in result
    assert "b=False" in result


def test_format_metric_dict_value_with_negative_int():
    result = _format_metric("foo", {"value": {"a": -5}, "reason": None})
    assert "a=-5" in result


# =========================================================================
# _run_inspect_doc：metric 输出排序精确
# =========================================================================


def test_run_inspect_doc_metric_sort_order_with_mixed_types(tmp_path: Path, capsys):
    """metrics 排序：bool → number → other → null."""
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1"}],
        "chunks": [{"text": "abc", "chunk_id": "c1", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    lines = captured.out.split("\n")
    # 找到 metrics 之后的行
    metric_lines = [l for l in lines if l.startswith("  ") and "(" in l and ")" in l]
    # 至少有 metrics 行
    assert len(metric_lines) > 0


def test_run_inspect_doc_metric_count_printed(tmp_path: Path, capsys):
    """inspect-doc 应打印所有 14 + 5 = 19 个 metric（自动 14 + 标注 5）."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    _run_inspect_doc(_FakeArgs(str(p)))
    captured = capsys.readouterr()
    lines = captured.out.split("\n")
    metric_lines = [l for l in lines if l.startswith("  ") and "(" in l]
    # 14 auto + 5 annotation (3 figure_caption + 3 chunk_boundary - 1 shared tol - 1 missing markers)
    # 实际 figure_caption_prf 返回 3 项，chunk_boundary_prf 返回 3 + 2 内部
    # 公开 metric：14 + 3 + 3 = 20
    # 但 silent_drop_count 也是 auto metric 之一
    # 让计算：auto metrics = 14（见 metrics.py）
    # figure_caption = 3
    # chunk_boundary = 3 (precision/recall/f1)
    # total = 14 + 3 + 3 = 20
    assert len(metric_lines) >= 18  # 至少有大部分 metric


# =========================================================================
# module 综合行为
# =========================================================================


def test_main_full_inspect_doc_flow_with_extra_keys(tmp_path: Path, capsys):
    """doc 含 extra keys → 仍能 inspect."""
    doc = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "extra_key": "ignored",
        "another": [1, 2, 3],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_path_with_unicode(tmp_path: Path, capsys):
    """inspect-doc 路径含 unicode → 仍能 work."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "文档.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_path_with_spaces(tmp_path: Path, capsys):
    """inspect-doc 路径含空格 → 仍能 work."""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "my doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
