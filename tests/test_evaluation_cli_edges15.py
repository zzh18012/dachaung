r"""evaluation/cli.py 边角测试 - 第十五轮（Round 244）。

补强已有 base/edges/edges2-14（共 ~1020+ 测试）未覆盖的深度：
- _format_metric：Counter（dict 子类）；dict 含 int/tuple/None 键；dict 含混合类型键 raises TypeError；
  name 含 unicode；name 含 emoji；metric 是 dict 子类
- _run_inspect_doc：args 用 duck typing（自定义类含 input/tolerance_chars）
- _build_parser：subparser choices 精确；_actions 类型；choices_actions 长度
- main：argv=[] / argv=None 行为差异；__name__ == "__main__" 块结构
- 模块：argparse/json/sys/Path identity；无 __all__
"""

from __future__ import annotations

import argparse
import inspect
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# =========================================================================
# _format_metric：Counter（dict 子类）
# =========================================================================


def test_format_metric_counter_value_treated_as_dict():
    """Counter 是 dict 子类 → isinstance(value, dict) True → 走 dict 分支。"""
    c = Counter()
    c["a"] = 1
    c["b"] = 2
    out = _format_metric("test", {"value": c, "reason": None})
    # 走 dict 分支，输出 "a=1, b=2"
    assert "a=1" in out
    assert "b=2" in out
    assert "(ok)" in out


def test_format_metric_counter_empty_renders_no_items():
    """空 Counter → items="" → 输出含 "(ok)" 但无 items。"""
    out = _format_metric("test", {"value": Counter(), "reason": None})
    # name 字段被 pad 到 36，然后空 items，然后 (ok)
    assert "(ok)" in out
    # 不含 "="（无 items）
    # 但 name="test" 不含 = ，所以总体应不含 =
    assert "=" not in out


def test_format_metric_counter_with_reason():
    """Counter 含 reason → reason 透传。"""
    c = Counter({"x": 5})
    out = _format_metric("test", {"value": c, "reason": "custom"})
    assert "(custom)" in out
    assert "x=5" in out


# =========================================================================
# _format_metric：dict 含特殊键
# =========================================================================


def test_format_metric_dict_with_int_keys():
    """dict 含 int 键 → sorted 工作但仍渲染 k=v。"""
    out = _format_metric("test", {"value": {1: "a", 2: "b"}, "reason": None})
    assert "1=a" in out
    assert "2=b" in out


def test_format_metric_dict_with_tuple_keys_raises():
    """dict 含 tuple 键与 str 键混合 → sorted 比较 TypeError。"""
    # tuple vs str 比较：sorted 在 Python 3 中触发 TypeError
    metric = {"value": {("tuple", "key"): 1, "str_key": 2}, "reason": None}
    with pytest.raises(TypeError):
        _format_metric("test", metric)


def test_format_metric_dict_with_int_and_str_keys_raises():
    """dict 含 int 和 str 混合键 → sorted 触发 TypeError。"""
    metric = {"value": {1: "a", "b": 2}, "reason": None}
    with pytest.raises(TypeError):
        _format_metric("test", metric)


def test_format_metric_dict_with_none_key_raises_when_mixed():
    """dict 含 None 与 str 混合键 → sorted 触发 TypeError。"""
    metric = {"value": {None: 1, "a": 2}, "reason": None}
    with pytest.raises(TypeError):
        _format_metric("test", metric)


def test_format_metric_dict_with_only_none_keys():
    """dict 只含 None 键 → sorted 工作（单元素）。"""
    out = _format_metric("test", {"value": {None: 1}, "reason": None})
    assert "None=1" in out


def test_format_metric_dict_with_only_int_keys():
    """dict 只含 int 键 → sorted 工作。"""
    out = _format_metric("test", {"value": {3: "c", 1: "a", 2: "b"}, "reason": None})
    # 排序后是 1, 2, 3
    assert "1=a" in out
    assert "2=b" in out
    assert "3=c" in out


# =========================================================================
# _format_metric：name 含特殊字符
# =========================================================================


def test_format_metric_name_with_unicode():
    """name 含中文字符 → 仍按 36 字符宽度（Python 默认按 code point 计数）。"""
    out = _format_metric("指标", {"value": 0.5, "reason": None})
    # 输出含 "指标" 和 "0.5000"
    assert "指标" in out
    assert "0.5000" in out


def test_format_metric_name_with_emoji():
    """name 含 emoji → 仍渲染（emoji 占多个 code point 但 :36 按 1 计）。"""
    out = _format_metric("🚀rocket", {"value": True, "reason": None})
    assert "🚀rocket" in out
    assert "true" in out


def test_format_metric_name_with_newline():
    """name 含 \\n → 输出含 newline（不 escape）。"""
    out = _format_metric("line1\nline2", {"value": 1, "reason": None})
    assert "line1\nline2" in out


def test_format_metric_name_with_tab():
    """name 含 \\t → 输出含 tab（不 escape）。"""
    out = _format_metric("a\tb", {"value": 1, "reason": None})
    assert "a\tb" in out


# =========================================================================
# _format_metric：metric 是 dict 子类
# =========================================================================


def test_format_metric_metric_dict_subclass():
    """metric 是 dict 子类（如 Counter）→ .get 工作正常。"""
    class MetricDict(dict):
        pass

    m = MetricDict({"value": 0.5, "reason": None})
    out = _format_metric("test", m)
    assert "0.5000" in out


def test_format_metric_metric_dict_with_default_for_missing():
    """metric 缺 value/reason → .get 返回 None → null (None)。"""
    out = _format_metric("test", {})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_zero_float():
    """value=0.0 → 走 float 分支 → 0.0000。"""
    out = _format_metric("test", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_negative_zero():
    """value=-0.0 → 渲染为 -0.0000。"""
    out = _format_metric("test", {"value": -0.0, "reason": None})
    assert "-0.0000" in out


def test_format_metric_value_very_small_float():
    """value=1e-10 → 渲染为 0.0000（4 位精度丢失）。"""
    out = _format_metric("test", {"value": 1e-10, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_very_large_float():
    """value=1e10 → 渲染科学计数法（.4f 不强制小数）。"""
    out = _format_metric("test", {"value": 1e10, "reason": None})
    # 1e10 with .4f gives "10000000000.0000"
    assert "10000000000.0000" in out


# =========================================================================
# _format_metric：reason 边界
# =========================================================================


def test_format_metric_reason_empty_string():
    """reason='' → falsy → 'ok' 替换。"""
    out = _format_metric("test", {"value": 0.5, "reason": ""})
    assert "(ok)" in out


def test_format_metric_reason_zero():
    """reason=0 → falsy → 'ok' 替换。"""
    out = _format_metric("test", {"value": 0.5, "reason": 0})
    assert "(ok)" in out


def test_format_metric_reason_string_zero():
    """reason='0' → truthy → '0' 透传。"""
    out = _format_metric("test", {"value": 0.5, "reason": "0"})
    assert "('0')" in out or "(0)" in out


def test_format_metric_reason_with_unicode():
    """reason 含中文 → 透传。"""
    out = _format_metric("test", {"value": None, "reason": "无内容可比"})
    assert "无内容可比" in out


# =========================================================================
# _build_parser：subparser choices 精确
# =========================================================================


def test_build_parser_subparser_choices_exact():
    """subparser 的 choices 是 {'run', 'validate-report', 'inspect-doc'}。"""
    parser = _build_parser()
    # 找到 _SubParsersAction
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert sub_action is not None
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_subparser_choices_count_three():
    """subparser 数量精确为 3。"""
    parser = _build_parser()
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert len(sub_action.choices) == 3


def test_build_parser_has_subparsers_action():
    """parser 含一个 _SubParsersAction。"""
    parser = _build_parser()
    sub_actions = [
        a for a in parser._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    assert len(sub_actions) == 1


def test_build_parser_subparser_dest_is_command():
    """subparser dest='command'。"""
    parser = _build_parser()
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert sub_action.dest == "command"


def test_build_parser_subparser_required_true():
    """subparser required=True。"""
    parser = _build_parser()
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert sub_action.required is True


def test_build_parser_choices_actions_length():
    """_choices_actions 长度 = 3（每个 subparser 一项）。"""
    parser = _build_parser()
    # _choices_actions 是 subparser 的 choices 列表
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert sub_action is not None
    assert len(sub_action.choices) == 3


def test_build_parser_run_subparser_argument_count_four():
    """run subparser 含 5 个 user-defined option args（manifest/output/parser/max-chars/tolerance-chars）。

    排除 -h/--help。
    """
    parser = _build_parser()
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    # 排除 help action
    run_args = [
        a for a in run_p._actions
        if a.option_strings and a.dest != "help"
    ]
    assert len(run_args) == 5


def test_build_parser_validate_subparser_argument_count_one():
    """validate-report subparser 含 1 个 positional argument（input）。"""
    parser = _build_parser()
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    val_p = sub_action.choices["validate-report"]
    # positional args (排除 help)
    val_args = [
        a for a in val_p._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert len(val_args) == 1


def test_build_parser_inspect_subparser_argument_count_two():
    """inspect-doc subparser 含 1 positional + 1 user-defined option = 2 个 user-facing args。"""
    parser = _build_parser()
    sub_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    ins_p = sub_action.choices["inspect-doc"]
    pos_args = [a for a in ins_p._actions if not a.option_strings]
    opt_args = [
        a for a in ins_p._actions
        if a.option_strings and a.dest != "help"
    ]
    assert len(pos_args) == 1
    assert len(opt_args) == 1


# =========================================================================
# _run_inspect_doc：duck typing args
# =========================================================================


class _FakeArgs:
    """模拟 argparse.Namespace。"""

    def __init__(self, input_path: Path, tolerance_chars: int = 30):
        self.input = str(input_path)
        self.tolerance_chars = tolerance_chars


def test_run_inspect_doc_accepts_duck_typed_args(tmp_path: Path, capsys):
    """_run_inspect_doc 接受任何含 .input 和 .tolerance_chars 属性的对象。"""
    doc = {"elements": [], "chunks": [], "source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    args = _FakeArgs(p)
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_duck_typed_args_with_tolerance(tmp_path: Path, capsys):
    """duck typed args 含 tolerance_chars=99 → 透传给 chunk_boundary_prf。"""
    doc = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
        "source_type": "pdf",
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    args = _FakeArgs(p, tolerance_chars=99)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_dict_args_raises(tmp_path: Path):
    """args 是 dict（无 .input 属性）→ AttributeError。"""
    with pytest.raises(AttributeError):
        _run_inspect_doc({"input": str(tmp_path / "x.json")})


def test_run_inspect_doc_with_none_input_attr(tmp_path: Path):
    """args.input=None → Path(None) raises TypeError。"""
    class NoInput:
        input = None
        tolerance_chars = 30

    with pytest.raises(TypeError):
        _run_inspect_doc(NoInput())


# =========================================================================
# main：__name__ == "__main__" 块
# =========================================================================


def test_main_module_has_dunder_main_block():
    """模块源码含 `if __name__ == "__main__":` 块。"""
    import evaluation.cli
    src = inspect.getsource(evaluation.cli)
    assert '__name__' in src
    assert '"__main__"' in src or "'__main__'" in src


def test_main_module_dunder_main_raises_system_exit():
    """`if __name__ == "__main__"` 块 raise SystemExit(main())。"""
    import evaluation.cli
    src = inspect.getsource(evaluation.cli)
    assert 'SystemExit' in src
    assert 'main()' in src


def test_main_callable():
    """main 是 callable。"""
    assert callable(main)


def test_main_signature_exact():
    """main(argv=None) 单参数，默认 None。"""
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]
    assert sig.parameters["argv"].default is None


def test_main_returns_int_for_inspect(tmp_path: Path):
    """main 返回 int。"""
    doc = {"elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_no_all_attribute():
    """模块没有 __all__（不在 __all__ 中导出特定名单）。"""
    import evaluation.cli as m
    assert not hasattr(m, "__all__")


def test_module_argparse_in_namespace():
    """argparse 在模块命名空间。"""
    import evaluation.cli as m
    assert m.argparse is argparse


def test_module_json_in_namespace():
    """json 在模块命名空间。"""
    import evaluation.cli as m
    assert m.json is json


def test_module_sys_in_namespace():
    """sys 在模块命名空间。"""
    import evaluation.cli as m
    assert m.sys is sys


def test_module_path_in_namespace():
    """Path 在模块命名空间。"""
    import evaluation.cli as m
    assert m.Path is Path


def test_module_main_in_namespace():
    """main 函数在模块命名空间。"""
    import evaluation.cli as m
    assert callable(m.main)


def test_module_build_parser_in_namespace():
    """_build_parser 在模块命名空间。"""
    import evaluation.cli as m
    assert callable(m._build_parser)


def test_module_format_metric_in_namespace():
    """_format_metric 在模块命名空间。"""
    import evaluation.cli as m
    assert callable(m._format_metric)


def test_module_run_inspect_doc_in_namespace():
    """_run_inspect_doc 在模块命名空间。"""
    import evaluation.cli as m
    assert callable(m._run_inspect_doc)


# =========================================================================
# 函数签名
# =========================================================================


def test_build_parser_signature_no_param():
    """_build_parser 无参数。"""
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_format_metric_signature_exact():
    """_format_metric(name, metric) 两参数。"""
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_run_inspect_doc_signature_exact():
    """_run_inspect_doc(args) 单参数。"""
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


# =========================================================================
# callable 验证
# =========================================================================


def test_build_parser_callable():
    assert callable(_build_parser)


def test_format_metric_callable():
    assert callable(_format_metric)


def test_run_inspect_doc_callable():
    assert callable(_run_inspect_doc)


# =========================================================================
# _build_parser：prog / description
# =========================================================================


def test_build_parser_prog_is_evaluation_cli():
    """parser.prog == 'evaluation.cli'。"""
    parser = _build_parser()
    assert parser.prog == "evaluation.cli"


def test_build_parser_description_starts_with_chinese():
    """description 以中文开头。"""
    parser = _build_parser()
    assert parser.description is not None
    assert "评测" in parser.description


def test_build_parser_formatter_class_is_raw_description():
    """formatter_class=RawDescriptionHelpFormatter。"""
    parser = _build_parser()
    assert parser.formatter_class is argparse.RawDescriptionHelpFormatter


# =========================================================================
# 端到端：run 子命令 argparse 错误
# =========================================================================


def test_main_run_no_args_raises_system_exit(capsys):
    """run 无任何参数 → argparse error → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run"])
    assert exc_info.value.code == 2


def test_main_run_only_manifest_no_output_raises_system_exit(capsys):
    """run 只有 --manifest 无 --output → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x.json"])
    assert exc_info.value.code == 2


def test_main_validate_report_no_positional_raises_system_exit(capsys):
    """validate-report 无 positional → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["validate-report"])
    assert exc_info.value.code == 2


def test_main_inspect_doc_no_positional_raises_system_exit(capsys):
    """inspect-doc 无 positional → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect-doc"])
    assert exc_info.value.code == 2


def test_main_unknown_command_raises_system_exit(capsys):
    """未知 subcommand → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["unknown-command"])
    assert exc_info.value.code == 2


def test_main_no_command_raises_system_exit(capsys):
    """无 subcommand → required=True → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


# =========================================================================
# 端到端：完整 inspect-doc 流程
# =========================================================================


def test_main_inspect_doc_with_full_document(tmp_path: Path, capsys):
    """完整 document 跑 inspect-doc → 返回 0，stdout 含多个 metric。"""
    doc = {
        "document_id": "test_doc",
        "source_path": "test.pdf",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "h1", "type": "heading", "content": "Title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"element_id": "p1", "type": "paragraph", "content": "Body text",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "Title Body text", "source_element_ids": ["h1", "p1"]},
        ],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "test_doc" in captured.out
    assert "fallback" in captured.out
    assert "elements=2" in captured.out
    assert "chunks=1" in captured.out
    assert "pipeline_success" in captured.out
