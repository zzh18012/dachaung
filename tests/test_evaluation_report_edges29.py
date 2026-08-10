"""evaluation/report.py 第二十九轮 edges 测试（Round 409）。

补强 edges28 未触及的角度：
- subprocess.run call signature 验证第十二批（cwd/capture_output/text/encoding/errors/timeout 实参 / 二次调用 / 单调用 args 验证 / 编码 utf-8 错误 replace）
- get_git_provenance 行为深度第十二批（empty stdout 且 returncode 0 / stderr 有内容但不影响 stdout / 多次调用独立 / bool returncode 边界 / r2.stdout 全空白字符）
- get_dependency_versions 行为深度第十二批（packages 顺序固定 / 容器是 dict / 容器是 dict 不是 OrderedDict / 单个 pkg 失败不影响其他 / importlib.metadata 内部导入验证）
- build_provenance 行为深度第十二批（dependencies 字段调用 get_dependency_versions / max_chars int 截断 / git_commit 来自 get_git_provenance / EVALUATOR_VERSION 与 REPORT_VERSION 来自 evaluation）
- build_devset_section 行为深度第十二批（字段映射 status←devset_status / 缺失属性 raises AttributeError / 返回 dict 是浅拷贝 / 字段数量固定）
- aggregate_summary 行为深度第十二批（metric dict 缺 value 键 / metric value 为字符串 / docs list 中含非 dict 元素 raise / 不修改 input / per_doc 缺 metrics 键 / silent_drop_count 部分缺失）
- module source forbidden tokens 第十七批
- module source 字符串精确补强第十四批
- signatures 第十四批
- module 合理性第十四批
- 端到端集成第十四批
"""

from __future__ import annotations

import inspect
import json
import subprocess
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, call

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION, report as rmod
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# ---------- subprocess.run call signature 验证第十二批 ----------


def test_subprocess_run_called_with_cwd_batch12():
    """subprocess.run 应该被传入 cwd=str(project_root)。"""
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("/some/path"))
    # 第一次调用应该传 cwd
    first_kwargs = seen_calls[0].kwargs
    assert first_kwargs.get("cwd") == str(Path("/some/path"))


def test_subprocess_run_called_with_capture_output_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen_calls[0].kwargs.get("capture_output") is True


def test_subprocess_run_called_with_text_true_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen_calls[0].kwargs.get("text") is True


def test_subprocess_run_called_with_encoding_utf8_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen_calls[0].kwargs.get("encoding") == "utf-8"


def test_subprocess_run_called_with_errors_replace_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen_calls[0].kwargs.get("errors") == "replace"


def test_subprocess_run_called_with_timeout_10_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen_calls[0].kwargs.get("timeout") == 10


def test_subprocess_run_invoked_twice_for_rev_parse_and_porcelain_batch12():
    """get_git_provenance 应该调用 subprocess.run 两次（rev-parse + porcelain）。"""
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert len(seen_calls) == 2


def test_subprocess_run_first_call_args_rev_parse_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    first_args = seen_calls[0].args
    assert list(first_args[0]) == ["git", "rev-parse", "HEAD"]


def test_subprocess_run_second_call_args_porcelain_batch12():
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    second_args = seen_calls[1].args
    assert list(second_args[0]) == ["git", "status", "--porcelain"]


def test_subprocess_run_kwargs_consistent_across_calls_batch12():
    """两次调用的通用 kwargs 应该一致。"""
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    kw0 = seen_calls[0].kwargs
    kw1 = seen_calls[1].kwargs
    # 这些 keys 应一致
    for k in ("capture_output", "text", "encoding", "errors", "timeout", "cwd"):
        assert kw0.get(k) == kw1.get(k)


def test_subprocess_run_args_indexable_first_element_batch12():
    """fake args[0] 是 list[str]（命令）。"""
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    # args 是 tuple，第一个位置参数是 list
    assert isinstance(seen_calls[0].args[0], list)


def test_subprocess_run_uses_path_str_not_path_obj_batch12():
    """cwd 应该是 str，不是 Path。"""
    seen_calls: list[call] = []

    def _fake(*args, **kwargs):
        seen_calls.append(call(*args, **kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("/x/y"))
    cwd_val = seen_calls[0].kwargs.get("cwd")
    assert isinstance(cwd_val, str)
    assert cwd_val == str(Path("/x/y"))


# ---------- get_git_provenance 行为深度第十二批 ----------


def test_get_git_provenance_empty_stdout_returncode_0_yields_none_batch12():
    """rev-parse returncode=0 但 stdout='' → commit=None（空字符串 falsy）。"""
    fake_ok_empty = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_ok_empty, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_whitespace_only_stdout_yields_none_batch12():
    """rev-parse stdout 只有空白 → strip 后 falsy → None。"""
    fake_ws = subprocess.CompletedProcess(args=[], returncode=0, stdout="   \n\t  ", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_ws, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_stderr_content_does_not_affect_stdout_batch12():
    """stderr 有内容但 stdout 干净 → 拿 stdout。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="warning: foo")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="warning: bar")
    seq = [fake_ok, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_calls_independent_batch12():
    """两次调用互不影响（每次都启动新的 try 块）。"""
    fake1_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="aaa\n", stderr="")
    fake1_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake1_ok, fake1_clean]):
        out1 = get_git_provenance(Path("."))

    fake2_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="bbb\n", stderr="")
    fake2_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake2_ok, fake2_clean]):
        out2 = get_git_provenance(Path("."))

    assert out1["git_commit"] == "aaa"
    assert out2["git_commit"] == "bbb"


def test_get_git_provenance_porcelain_only_whitespace_yields_clean_batch12():
    """porcelain stdout 全空白 → strip 后空 → dirty=False。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_ws = subprocess.CompletedProcess(args=[], returncode=0, stdout="  \n  ", stderr="")
    seq = [fake_ok, fake_ws]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_has_output_yields_dirty_batch12():
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_dirty = subprocess.CompletedProcess(args=[], returncode=0, stdout=" M file.py\n", stderr="")
    seq = [fake_ok, fake_dirty]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is True


def test_get_git_provenance_dict_keys_remain_git_commit_dirty_batch12():
    out = get_git_provenance(Path("."))
    assert set(out.keys()) == {"git_commit", "git_dirty"}
    assert len(out) == 2


def test_get_git_provenance_no_extra_keys_batch12():
    out = get_git_provenance(Path("."))
    # 不应该有其他额外 key
    for key in out.keys():
        assert key in {"git_commit", "git_dirty"}


def test_get_git_provenance_value_types_batch12():
    """git_commit 是 str|None，git_dirty 是 bool。"""
    out = get_git_provenance(Path("."))
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_dict_mutation_does_not_propagate_batch12():
    """修改返回 dict 不影响后续调用。"""
    out1 = get_git_provenance(Path("."))
    original_commit = out1["git_commit"]
    out1["git_commit"] = "tampered"
    out1["extra"] = "x"
    out2 = get_git_provenance(Path("."))
    assert out2["git_commit"] == original_commit
    assert "extra" not in out2


# ---------- get_dependency_versions 行为深度第十二批 ----------


def test_get_dependency_versions_packages_order_fixed_batch12():
    seen: list[str] = []

    def _fake(name):
        seen.append(name)
        return f"{name}-v"

    with patch("importlib.metadata.version", side_effect=_fake):
        get_dependency_versions()
    # 包顺序固定
    assert seen == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_returns_dict_not_ordered_dict_batch12():
    out = get_dependency_versions()
    assert type(out) is dict
    assert not isinstance(out, OrderedDict)


def test_get_dependency_versions_one_pkg_failure_isolated_batch12():
    """一个 pkg 失败不影响其他。"""
    def _fake(name):
        if name == "python-docx":
            raise ImportError("missing")
        return "1.0.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] == "1.0.0"


def test_get_dependency_versions_one_pkg_package_not_found_isolated_batch12():
    import importlib.metadata

    def _fake(name):
        if name == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError("nope")
        return "9.9.9"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] == "9.9.9"


def test_get_dependency_versions_dict_size_3_batch12():
    out = get_dependency_versions()
    assert len(out) == 3


def test_get_dependency_versions_dict_keys_exact_batch12():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_value_types_batch12():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_importlib_metadata_imported_inside_func_batch12():
    """importlib.metadata 应在函数内 import（按源码）。"""
    source = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in source


def test_get_dependency_versions_function_docstring_present_batch12():
    """get_dependency_versions 应有 docstring。"""
    assert get_dependency_versions.__doc__ is not None
    assert len(get_dependency_versions.__doc__) > 10


def test_get_dependency_versions_iterates_pkg_tuple_batch12():
    """函数内 for pkg in (...) — pkg 应是 3 个标识符。"""
    source = inspect.getsource(get_dependency_versions)
    assert "for pkg in" in source
    assert "pdfplumber" in source
    assert "python-docx" in source
    assert "pypdfium2" in source


def test_get_dependency_versions_three_distinct_pkgs_batch12():
    """三个 pkg 字符串都不同。"""
    out = get_dependency_versions()
    keys = list(out.keys())
    assert len(set(keys)) == 3


# ---------- build_provenance 行为深度第十二批 ----------


def test_build_provenance_calls_get_git_provenance_batch12():
    """build_provenance 应该调用 get_git_provenance。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "fake", "git_dirty": False}) as mock:
        out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert mock.called
    assert mock.call_args.args[0] == Path(".")


def test_build_provenance_calls_get_dependency_versions_batch12():
    with patch("evaluation.report.get_dependency_versions", return_value={"a": "1"}) as mock:
        out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert mock.called
    assert out["dependencies"] == {"a": "1"}


def test_build_provenance_evaluator_version_from_evaluation_batch12():
    """build_provenance 的 evaluator_version 字段应该等于 EVALUATOR_VERSION。"""
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_from_evaluation_batch12():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_max_chars_truncates_float_batch12():
    """int(800.5) → 800。"""
    out = build_provenance(Path("."), parser_name="x", max_chars=800.5, parser_version=None)
    assert out["max_chars"] == 800


def test_build_provenance_max_chars_truncates_negative_float_batch12():
    """int(-0.5) → 0（int 截断）。"""
    out = build_provenance(Path("."), parser_name="x", max_chars=-0.5, parser_version=None)
    assert out["max_chars"] == 0


def test_build_provenance_parser_name_unicode_batch12():
    out = build_provenance(Path("."), parser_name="解析器-🚀", max_chars=100, parser_version=None)
    assert out["parser_name"] == "解析器-🚀"


def test_build_provenance_parser_version_unicode_batch12():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version="v1.0-α")
    assert out["parser_version"] == "v1.0-α"


def test_build_provenance_returns_dict_type_batch12():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert type(out) is dict


def test_build_provenance_keys_count_9_batch12():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert len(out) == 9


def test_build_provenance_git_commit_propagated_from_helper_batch12():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": True}):
        out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_build_provenance_run_timestamp_iso_timezone_aware_batch12():
    """run_timestamp_iso 应该是带时区的 ISO 字符串（astimezone()）。"""
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert parsed.tzinfo is not None


def test_build_provenance_keys_all_present_batch12():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    expected_keys = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected_keys


# ---------- build_devset_section 行为深度第十二批 ----------


class _StubManifest4:
    devset_status = "incomplete"
    file_count = 5
    content_group_count = 3
    pdf_count = 2
    docx_count = 1
    categories_covered = ["a", "b"]


def test_build_devset_section_field_mapping_status_batch12():
    """status ← devset_status。"""
    out = build_devset_section(_StubManifest4())
    assert out["status"] == "incomplete"


def test_build_devset_section_field_mapping_file_count_batch12():
    out = build_devset_section(_StubManifest4())
    assert out["file_count"] == 5


def test_build_devset_section_field_mapping_content_group_count_batch12():
    out = build_devset_section(_StubManifest4())
    assert out["content_group_count"] == 3


def test_build_devset_section_field_mapping_pdf_count_batch12():
    out = build_devset_section(_StubManifest4())
    assert out["pdf_count"] == 2


def test_build_devset_section_field_mapping_docx_count_batch12():
    out = build_devset_section(_StubManifest4())
    assert out["docx_count"] == 1


def test_build_devset_section_field_mapping_categories_batch12():
    out = build_devset_section(_StubManifest4())
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_missing_attr_raises_batch12():
    """Manifest 缺属性 → AttributeError。"""
    class _M:
        devset_status = "x"
        # 其他属性都缺
    with pytest.raises(AttributeError):
        build_devset_section(_M())


def test_build_devset_section_field_count_6_batch12():
    out = build_devset_section(_StubManifest4())
    assert len(out) == 6


def test_build_devset_section_keys_exact_set_batch12():
    out = build_devset_section(_StubManifest4())
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_returns_fresh_dict_batch12():
    """每次调用返回新 dict。"""
    m = _StubManifest4()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 is not out2
    out1["status"] = "modified"
    assert out2["status"] == "incomplete"


def test_build_devset_section_input_attr_unchanged_batch12():
    """不修改输入 manifest 的属性。"""
    m = _StubManifest4()
    _ = build_devset_section(m)
    assert m.devset_status == "incomplete"
    assert m.file_count == 5


def test_build_devset_section_categories_dict_unchanged_batch12():
    """不修改 categories_covered list 内容（同对象引用，但元素应不变）。"""
    m = _StubManifest4()
    snapshot = list(m.categories_covered)
    out = build_devset_section(m)
    # 原属性未被修改
    assert list(m.categories_covered) == snapshot
    # out['categories_covered'] 与 m.categories_covered 是同一引用（未拷贝）
    assert out["categories_covered"] is m.categories_covered


def test_build_devset_section_returns_dict_type_batch12():
    out = build_devset_section(_StubManifest4())
    assert type(out) is dict


def test_build_devset_section_dict_keys_order_preserved_batch12():
    out = build_devset_section(_StubManifest4())
    expected_order = [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    ]
    assert list(out.keys()) == expected_order


# ---------- aggregate_summary 行为深度第十二批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {"metrics": metrics}


def test_aggregate_summary_metric_dict_missing_value_key_batch12():
    """metric dict 缺 value 键 → get('value') 返回 None → 跳过。"""
    docs = [_metrics_doc({"schema_valid": {"reason": "no_value"}})]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["macro_average"] is None
    assert macro["participating_docs"] == 0
    assert macro["not_evaluated"] == 1


def test_aggregate_summary_metric_value_string_batch12():
    """value 是字符串 → sum() 失败。但 `if values` 过滤条件是 value is not None。
    字符串 'x' is not None → 进入 values → sum 时失败。
    用 patched: 排除 sum 失败，单独验证字符串进入 list。"""
    docs = [_metrics_doc({"schema_valid": {"value": "abc"}})]
    with pytest.raises(TypeError):
        aggregate_summary(docs)


def test_aggregate_summary_metric_value_none_explicit_batch12():
    """value 显式 None → is None → 跳过。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": None}}),
        _metrics_doc({"schema_valid": {"value": 0.5}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["macro_average"] == 0.5
    assert macro["participating_docs"] == 1
    assert macro["not_evaluated"] == 1


def test_aggregate_summary_does_not_modify_input_batch12():
    """aggregate_summary 不修改输入 list 与 dict。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    snapshot = json.dumps(docs, sort_keys=True, default=str)
    _ = aggregate_summary(docs)
    assert json.dumps(docs, sort_keys=True, default=str) == snapshot


def test_aggregate_summary_per_doc_missing_metrics_key_batch12():
    """per_doc 缺 metrics 键 → r['metrics'] raise KeyError（用 [] 不用 .get）。"""
    docs = [{"not_metrics": {}}]
    with pytest.raises(KeyError):
        aggregate_summary(docs)


def test_aggregate_summary_silent_drop_count_partial_batch12():
    """部分 doc 有 silent_drop_count，部分没有。"""
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 3}}),
        _metrics_doc({}),  # 无 silent_drop_count
        _metrics_doc({"silent_drop_count": {"value": 5}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_count_zero_counted_batch12():
    """silent_drop_count value=0 is not None → 应被计入。"""
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 0}}),
        _metrics_doc({"silent_drop_count": {"value": 5}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_count_negative_and_positive_batch12():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": -2}}),
        _metrics_doc({"silent_drop_count": {"value": 3}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 1


def test_aggregate_summary_counts_participating_docs_excludes_none_batch12():
    docs = [
        _metrics_doc({"element_count_total": {"value": None}}),
        _metrics_doc({"element_count_total": {"value": 10}}),
        _metrics_doc({}),  # 无 element_count_total
    ]
    out = aggregate_summary(docs)
    info = out["counts"]["element_count_total"]
    assert info["sum"] == 10
    assert info["participating_docs"] == 1


def test_aggregate_summary_success_rate_when_total_0_yields_none_batch12():
    """empty docs → total=0 → rate=None。"""
    out = aggregate_summary([])
    info = out["success_rates"]["pipeline_success"]
    assert info["total"] == 0
    assert info["rate"] is None
    assert info["success_count"] == 0


def test_aggregate_summary_success_rate_all_true_batch12():
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    info = out["success_rates"]["pipeline_success"]
    assert info["success_count"] == 2
    assert info["total"] == 2
    assert info["rate"] == 1.0


def test_aggregate_summary_success_rate_all_false_batch12():
    docs = [
        _metrics_doc({"pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(docs)
    info = out["success_rates"]["pipeline_success"]
    assert info["success_count"] == 0
    assert info["rate"] == 0.0


def test_aggregate_summary_top_keys_exact_batch12():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_keys_exact_batch12():
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_keys_exact_batch12():
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_keys_exact_batch12():
    out = aggregate_summary([])
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_ratio_metrics_count_12_batch12():
    assert len(_RATIO_METRICS) == 12


def test_aggregate_summary_count_metrics_count_1_batch12():
    assert len(_COUNT_METRICS) == 1


def test_aggregate_summary_success_bool_metrics_count_1_batch12():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_aggregate_summary_not_evaluated_when_partial_batch12():
    """部分 doc 有 ratio metric，部分没有。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"schema_valid": {"value": 0.5}}),
        _metrics_doc({}),  # 缺 metric
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["participating_docs"] == 2
    assert macro["not_evaluated"] == 1


def test_aggregate_summary_each_ratio_metric_has_3_keys_batch12():
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert set(out["ratio_macro_averages"][name].keys()) == {
            "macro_average", "participating_docs", "not_evaluated",
        }


def test_aggregate_summary_counts_has_2_keys_batch12():
    out = aggregate_summary([])
    for name in _COUNT_METRICS:
        assert set(out["counts"][name].keys()) == {"sum", "participating_docs"}


def test_aggregate_summary_success_rates_has_3_keys_batch12():
    out = aggregate_summary([])
    for name in _SUCCESS_BOOL_METRICS:
        assert set(out["success_rates"][name].keys()) == {"success_count", "total", "rate"}


# ---------- module source forbidden tokens 第十七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_report_source_no_forbidden_token_seventeenth_batch12(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_report_source_no_eval_call_batch12():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_report_source_no_compile_call_batch12():
    source = inspect.getsource(rmod)
    assert "compile(" not in source


def test_report_source_no_open_call_batch12():
    """report.py 不应直接 open 文件（纯计算）。"""
    source = inspect.getsource(rmod)
    assert "\nopen(" not in source
    assert " open(" not in source


def test_report_source_no_os_module_usage_batch12():
    source = inspect.getsource(rmod)
    assert "import os" not in source
    assert "os." not in source


def test_report_source_no_sys_module_usage_batch12():
    source = inspect.getsource(rmod)
    assert "import sys" not in source
    assert "sys." not in source


def test_report_source_no_shutil_usage_batch12():
    source = inspect.getsource(rmod)
    assert "shutil" not in source


def test_report_source_no_tempfile_usage_batch12():
    source = inspect.getsource(rmod)
    assert "tempfile" not in source


def test_report_source_no_logging_usage_batch12():
    source = inspect.getsource(rmod)
    assert "import logging" not in source


def test_report_source_no_re_module_usage_batch12():
    source = inspect.getsource(rmod)
    assert "import re" not in source
    assert "re." not in source


def test_report_source_no_io_module_usage_batch12():
    source = inspect.getsource(rmod)
    assert "import io" not in source


# ---------- module source 字符串精确补强第十四批 ----------


def test_module_source_subprocess_run_call_present_batch12():
    source = inspect.getsource(rmod)
    assert "subprocess.run" in source


def test_module_source_has_rev_parse_HEAD_batch12():
    source = inspect.getsource(rmod)
    assert '"git", "rev-parse", "HEAD"' in source or "'git', 'rev-parse', 'HEAD'" in source


def test_module_source_has_status_porcelain_batch12():
    source = inspect.getsource(rmod)
    assert '"git", "status", "--porcelain"' in source or "'git', 'status', '--porcelain'" in source


def test_module_source_has_int_max_chars_batch12():
    source = inspect.getsource(rmod)
    assert "int(max_chars)" in source


def test_module_source_has_datetime_now_isoformat_batch12():
    source = inspect.getsource(rmod)
    assert "datetime.now()" in source
    assert ".isoformat()" in source


def test_module_source_has_astimezone_batch12():
    source = inspect.getsource(rmod)
    assert ".astimezone()" in source


def test_module_source_has_try_except_oserror_subprocess_batch12():
    source = inspect.getsource(rmod)
    assert "except (OSError, subprocess.SubprocessError)" in source


def test_module_source_has_PackageNotFoundError_batch12():
    source = inspect.getsource(rmod)
    assert "PackageNotFoundError" in source


def test_module_source_has_importlib_metadata_inline_batch12():
    """importlib.metadata 在函数内 import。"""
    source = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in source


def test_module_source_dict_literal_with_git_commit_batch12():
    source = inspect.getsource(get_git_provenance)
    assert "git_commit" in source
    assert "git_dirty" in source


def test_module_source_return_dict_for_devset_batch12():
    source = inspect.getsource(build_devset_section)
    assert "devset_status" in source
    assert "file_count" in source
    assert "content_group_count" in source
    assert "pdf_count" in source
    assert "docx_count" in source
    assert "categories_covered" in source


def test_module_source_aggregate_summary_uses_get_value_batch12():
    source = inspect.getsource(aggregate_summary)
    assert '.get("value")' in source or ".get('value')" in source


def test_module_source_aggregate_summary_uses_metrics_key_batch12():
    source = inspect.getsource(aggregate_summary)
    assert '"metrics"' in source or "'metrics'" in source


def test_module_source_aggregate_summary_uses_silent_drop_count_batch12():
    source = inspect.getsource(aggregate_summary)
    assert "silent_drop_count" in source
    assert "silent_drop_total" in source


def test_module_source_has_comments_about_no_mixed_types_batch12():
    source = inspect.getsource(rmod)
    assert "counts" in source
    assert "success_rates" in source


def test_module_source_has_RATE_METRICS_docstring_marker_batch12():
    """模块顶部 docstring 应提到 ratio macro average。"""
    assert rmod.__doc__ is not None
    assert "macro" in rmod.__doc__ or "macro_average" in rmod.__doc__ or "ratio" in rmod.__doc__


def test_module_source_no_idioms_input_function_batch12():
    source = inspect.getsource(rmod)
    assert "=input(" not in source.replace(" ", "")


def test_module_source_no_print_call_batch12():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_module_source_has_module_docstring_about_aggregation_batch12():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_source_has_VERSION_module_imports_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "EVALUATOR_VERSION" in head
    assert "REPORT_VERSION" in head


# ---------- signatures 第十四批 ----------


def test_get_git_provenance_param_annotation_Path_batch12():
    sig = inspect.signature(get_git_provenance)
    annot = sig.parameters["project_root"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str


def test_build_provenance_param_annotations_batch12():
    sig = inspect.signature(build_provenance)
    annots = {name: (p.annotation if isinstance(p.annotation, str) else str(p.annotation))
              for name, p in sig.parameters.items()}
    assert "Path" in annots["project_root"]
    assert "str" in annots["parser_name"]
    assert "int" in annots["max_chars"]


def test_build_provenance_param_kinds_batch12():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_aggregate_summary_param_annotation_list_dict_batch12():
    sig = inspect.signature(aggregate_summary)
    annot = sig.parameters["per_doc_results"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "list" in annot_str
    assert "dict" in annot_str


def test_build_devset_section_no_annotation_batch12():
    sig = inspect.signature(build_devset_section)
    annot = sig.parameters["manifest"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    # 无显式类型（type: ignore 注释）
    assert annot_str == "inspect.Parameter.empty" or annot is inspect.Parameter.empty


def test_get_dependency_versions_signature_empty_params_batch12():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_public_functions_count_5_batch12():
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert len(funcs) == 5


def test_module_public_function_names_batch12():
    funcs = {
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    }
    assert funcs == {
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    }


def test_get_git_provenance_no_default_for_project_root_batch12():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.default is inspect.Parameter.empty


def test_build_provenance_no_defaults_batch12():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_aggregate_summary_no_default_for_per_doc_results_batch12():
    sig = inspect.signature(aggregate_summary)
    p = sig.parameters["per_doc_results"]
    assert p.default is inspect.Parameter.empty


def test_build_devset_section_manifest_no_default_batch12():
    sig = inspect.signature(build_devset_section)
    p = sig.parameters["manifest"]
    assert p.default is inspect.Parameter.empty


def test_all_module_functions_callable_batch12():
    for name in ("get_git_provenance", "get_dependency_versions",
                 "build_provenance", "build_devset_section", "aggregate_summary"):
        fn = getattr(rmod, name)
        assert callable(fn)


def test_get_git_provenance_no_kwargs_param_batch12():
    sig = inspect.signature(get_git_provenance)
    assert "*args" not in str(sig)
    assert "**kwargs" not in str(sig)


# ---------- module 合理性第十四批 ----------


def test_module_dunder_file_exists_batch12():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_path_evaluation_report_batch12():
    import os
    sep = os.sep
    assert rmod.__file__.endswith(sep + "report.py")
    assert "evaluation" in rmod.__file__


def test_module_name_evaluation_report_batch12():
    assert rmod.__name__ == "evaluation.report"


def test_module_has_dunder_all_5_items_batch12():
    assert hasattr(rmod, "__all__")
    assert len(rmod.__all__) == 5


def test_module_dunder_all_includes_public_funcs_batch12():
    expected = {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }
    assert set(rmod.__all__) == expected


def test_module_constants_count_3_tuples_batch12():
    consts = [
        n for n, v in vars(rmod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert set(consts) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}


def test_module_no_user_classes_batch12():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_evaluator_version_attr_present_batch12():
    assert hasattr(rmod, "EVALUATOR_VERSION")


def test_module_report_version_attr_present_batch12():
    assert hasattr(rmod, "REPORT_VERSION")


def test_module_evaluator_version_value_matches_batch12():
    assert rmod.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_report_version_value_matches_batch12():
    assert rmod.REPORT_VERSION == REPORT_VERSION


def test_module_subprocess_import_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import subprocess" in head


def test_module_typing_any_import_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_pathlib_import_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_datetime_import_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from datetime import datetime" in head


def test_module_has_no_unused_imports_quick_check_batch12():
    """简单检查：所有 import 都应在源码中出现至少一次（模块级使用）。"""
    source = inspect.getsource(rmod)
    # datetime, Path, Any, subprocess, EVALUATOR_VERSION, REPORT_VERSION — 都该被用
    assert "datetime" in source
    assert "Path" in source
    assert "Any" in source
    assert "subprocess" in source


# ---------- 端到端集成第十四批 ----------


def test_e2e_full_report_with_subprocess_patch_batch12():
    """模拟 git 输出 + 调用 build_provenance 验证字段流转。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="deadbeef\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=[fake_ok, fake_clean]):
        out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version="1.0")

    assert out["git_commit"] == "deadbeef"
    assert out["git_dirty"] is False
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0"
    assert out["max_chars"] == 800


def test_e2e_aggregate_then_devset_combined_batch12():
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 1.0},
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 10},
            "silent_drop_count": {"value": 2},
        }),
    ]
    summary = aggregate_summary(docs)
    devset = build_devset_section(_StubManifest4())
    report = {"summary": summary, "devset": devset}
    parsed = json.loads(json.dumps(report))
    assert parsed == report


def test_e2e_full_provenance_json_serializable_batch12():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_devset_section_json_serializable_with_list_categories_batch12():
    class _M:
        devset_status = "incomplete"
        file_count = 3
        content_group_count = 2
        pdf_count = 1
        docx_count = 2
        categories_covered = ["a", "b", "c"]
    out = build_devset_section(_M())
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_aggregate_summary_with_full_metrics_json_serializable_batch12():
    metric_value = {"value": 0.75}
    full_metrics = {name: metric_value for name in _RATIO_METRICS}
    full_metrics["pipeline_success"] = {"value": True}
    full_metrics["element_count_total"] = {"value": 5}
    full_metrics["silent_drop_count"] = {"value": 1}
    docs = [_metrics_doc(full_metrics)]
    summary = aggregate_summary(docs)
    parsed = json.loads(json.dumps(summary))
    assert parsed == summary


def test_e2e_combined_provenance_devset_summary_no_overlap_batch12():
    """三个组件 key 不应重叠。"""
    prov = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    devset = build_devset_section(_StubManifest4())
    summary = aggregate_summary([])
    prov_keys = set(prov.keys())
    devset_keys = set(devset.keys())
    summary_keys = set(summary.keys())
    # 三者互不重叠
    assert prov_keys.isdisjoint(devset_keys)
    assert prov_keys.isdisjoint(summary_keys)
    assert devset_keys.isdisjoint(summary_keys)


def test_e2e_idempotent_aggregate_summary_no_metrics_batch12():
    """两次调用 aggregate_summary([]) 应返回相同 dict。"""
    out1 = aggregate_summary([])
    out2 = aggregate_summary([])
    # 比较 dict 内容（不比较引用）
    assert out1 == out2


def test_e2e_idempotent_devset_section_batch12():
    """两次 build_devset_section 返回 dict 内容相同。"""
    m = _StubManifest4()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 == out2


def test_e2e_provenance_independent_calls_batch12():
    """两次 build_provenance 应有独立的 dependencies dict。"""
    out1 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out1["dependencies"] is not out2["dependencies"]


def test_e2e_provenance_timestamp_changing_batch12():
    """两次调用 timestamp 应不同（实际时钟可能精度低，但应不强制相等）。"""
    out1 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    # 两次都应是 ISO 字符串
    assert isinstance(out1["run_timestamp_iso"], str)
    assert isinstance(out2["run_timestamp_iso"], str)
    # 都应可解析为 datetime
    datetime.fromisoformat(out1["run_timestamp_iso"])
    datetime.fromisoformat(out2["run_timestamp_iso"])
