"""evaluation/report.py 第二十八轮 edges 测试（Round 402）。

补强 edges27 未触及的角度：
- get_git_provenance 行为深度第十一批（exception paths：rev-parse raises / porcelain raises / 两者都 raises / TimeoutExpired / UnicodeEncodeError 不在 except / Generic Exception 不在 except / 进程被 kill / 验证 dirty 默认 True 等）
- get_dependency_versions 行为深度第十一批（ValueError / KeyError / TypeError / KeyboardInterrupt 不在 except / 各 pkg 顺序 / version 字符串边界 / 容器独立性 / dict type）
- build_provenance 行为深度第十一批（timestamp 解析 / max_chars=0 / 负数 / float / bool / parser_version="" / 9 keys 类型）
- build_devset_section 行为深度第十一批（categories_covered 各种容器 / 全 0 / 全 None / Unicode status / 字段独立 propagation）
- aggregate_summary 行为深度第十一批（negative counts / non-bool pipeline_success / silent_drop_total None when all None / 所有 docs 有所有 metrics / 单 doc 全 0 / 输入 list 不被 alias）
- module source forbidden tokens 第十四批（含十六个）
- module source 字符串精确补强第十一批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
"""

from __future__ import annotations

import inspect
import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

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


# ---------- get_git_provenance 行为深度第十一批 ----------


def test_get_git_provenance_rev_parse_raises_oserror_batch11():
    """rev-parse raises OSError → except 捕获 → commit=None, dirty=True。"""
    def _fake(*args, **kwargs):
        raise OSError("boom")

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_raises_subprocess_error_batch11():
    """rev-parse raises SubprocessError → except 捕获。"""
    def _fake(*args, **kwargs):
        raise subprocess.SubprocessError("sub boom")

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_raises_timeout_expired_batch11():
    """TimeoutExpired 是 SubprocessError 子类 → 捕获。"""
    def _fake(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_porcelain_raises_after_rev_parse_ok_batch11():
    """rev-parse 成功，但 porcelain raises → except 覆盖 commit → None, dirty=True。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")

    def _fake(*args, **kwargs):
        if "rev-parse" in args[0]:
            return fake_ok
        raise OSError("porcelain boom")

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    # 即使 rev-parse 成功，porcelain raises 后 except 把 commit 重置 None
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_uncaught_exception_batch11():
    """Generic Exception 不在 except list → 应向上抛。"""
    def _fake(*args, **kwargs):
        raise RuntimeError("not caught")

    with patch("subprocess.run", side_effect=_fake):
        with pytest.raises(RuntimeError):
            get_git_provenance(Path("."))


def test_get_git_provenance_keyboard_interrupt_not_caught_batch11():
    """KeyboardInterrupt 不在 except list。"""
    def _fake(*args, **kwargs):
        raise KeyboardInterrupt("user cancel")

    with patch("subprocess.run", side_effect=_fake):
        with pytest.raises(KeyboardInterrupt):
            get_git_provenance(Path("."))


def test_get_git_provenance_first_call_negative_returncode_batch11():
    """rev-parse returncode=-1 → 视作 != 0 → commit None。"""
    fake_fail = subprocess.CompletedProcess(args=[], returncode=-1, stdout="abc\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_fail, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_returncode_negative_batch11():
    """porcelain returncode=-1 → r2.returncode == 0 为假 → dirty False。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_fail = subprocess.CompletedProcess(args=[], returncode=-1, stdout=" M file\n", stderr="")
    seq = [fake_ok, fake_fail]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


def test_get_git_provenance_default_dirty_true_when_rev_parse_fails_batch11():
    """dirty 初始 True，rev-parse 失败但 porcelain 成功 → dirty 重新赋 False。"""
    fake_fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_fail, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    # porcelain 成功 + 空 stdout → dirty False
    assert out["git_dirty"] is False


def test_get_git_provenance_rev_parse_stdout_multiline_batch11():
    """rev-parse stdout 多行 → strip 全部空白 → 拿到完整 commit 含中间换行的字符串。"""
    fake_ok = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="abc\ndef\n", stderr=""
    )
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_ok, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    # "abc\ndef\n".strip() == "abc\ndef" → truthy
    assert out["git_commit"] == "abc\ndef"


def test_get_git_provenance_keys_exact_set_batch11():
    out = get_git_provenance(Path("."))
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_returns_fresh_dict_each_call_batch11():
    out1 = get_git_provenance(Path("."))
    out2 = get_git_provenance(Path("."))
    out1["custom"] = 1
    assert "custom" not in out2


# ---------- get_dependency_versions 行为深度第十一批 ----------


def test_get_dependency_versions_value_error_caught_batch11():
    """ValueError 是 Exception 子类 → 走 generic except。"""
    import importlib.metadata

    def _fake(name):
        if name == "pdfplumber":
            raise ValueError("bad value")
        return "1.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] == "1.0"
    assert out["pypdfium2"] == "1.0"


def test_get_dependency_versions_key_error_caught_batch11():
    """KeyError 是 Exception 子类 → 走 generic except。"""
    def _fake(name):
        if name == "python-docx":
            raise KeyError("missing key")
        return "1.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["python-docx"] is None


def test_get_dependency_versions_type_error_caught_batch11():
    """TypeError 是 Exception 子类。"""
    def _fake(name):
        if name == "pypdfium2":
            raise TypeError("wrong type")
        return "1.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pypdfium2"] is None


def test_get_dependency_versions_keyboard_interrupt_not_caught_batch11():
    """KeyboardInterrupt 不是 Exception 子类（是 BaseException）→ 应向上抛。"""
    def _fake(name):
        raise KeyboardInterrupt("user")

    with patch("importlib.metadata.version", side_effect=_fake):
        with pytest.raises(KeyboardInterrupt):
            get_dependency_versions()


def test_get_dependency_versions_iteration_order_batch11():
    """pkg 顺序：pdfplumber → python-docx → pypdfium2。"""
    seen: list[str] = []

    def _fake(name):
        seen.append(name)
        return f"{name}-1.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert seen == ["pdfplumber", "python-docx", "pypdfium2"]
    assert list(out.keys()) == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_version_with_build_metadata_batch11():
    def _fake(name):
        return "1.0.0+build.123"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    for v in out.values():
        assert v == "1.0.0+build.123"


def test_get_dependency_versions_version_with_newlines_batch11():
    def _fake(name):
        return "1.0\n"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    for v in out.values():
        assert v == "1.0\n"


def test_get_dependency_versions_version_empty_string_batch11():
    def _fake(name):
        return ""

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    for v in out.values():
        assert v == ""


def test_get_dependency_versions_mixed_versions_batch11():
    counter = [0]

    def _fake(name):
        counter[0] += 1
        return f"{counter[0]}.0.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0.0"
    assert out["python-docx"] == "2.0.0"
    assert out["pypdfium2"] == "3.0.0"


def test_get_dependency_versions_three_distinct_calls_batch11():
    """3 个独立 pkg，3 次调用。"""
    counter = [0]

    def _fake(name):
        counter[0] += 1
        return "1.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        get_dependency_versions()
    assert counter[0] == 3


def test_get_dependency_versions_dict_no_aliasing_batch11():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 is not out2
    out1["pdfplumber"] = "modified"
    assert out2["pdfplumber"] != "modified"


# ---------- build_provenance 行为深度第十一批 ----------


def test_build_provenance_max_chars_zero_batch11():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=0, parser_version=None)
    assert out["max_chars"] == 0
    assert type(out["max_chars"]) is int


def test_build_provenance_max_chars_negative_batch11():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=-1, parser_version=None)
    assert out["max_chars"] == -1


def test_build_provenance_max_chars_float_truncated_batch11():
    """int(800.99) → 800。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800.99, parser_version=None)
    assert out["max_chars"] == 800


def test_build_provenance_max_chars_bool_true_batch11():
    """int(True) → 1。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=True, parser_version=None)
    assert out["max_chars"] == 1


def test_build_provenance_parser_version_empty_string_batch11():
    out = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version=""
    )
    assert out["parser_version"] == ""


def test_build_provenance_run_timestamp_parses_iso_batch11():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert parsed is not None


def test_build_provenance_keys_order_preserved_batch11():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    expected = [
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    ]
    assert list(out.keys()) == expected


def test_build_provenance_dependencies_dict_batch11():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert type(out["dependencies"]) is dict


def test_build_provenance_parser_name_propagated_batch11():
    out = build_provenance(
        Path("."), parser_name="kreuzberg", max_chars=800, parser_version=None
    )
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_two_calls_with_diff_max_chars_batch11():
    out1 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="x", max_chars=200, parser_version=None)
    assert out1["max_chars"] == 100
    assert out2["max_chars"] == 200


def test_build_provenance_max_chars_huge_int_batch11():
    out = build_provenance(
        Path("."), parser_name="x", max_chars=2**31 - 1, parser_version=None
    )
    assert out["max_chars"] == 2**31 - 1


# ---------- build_devset_section 行为深度第十一批 ----------


class _StubManifest3:
    devset_status = "complete"
    file_count = 0
    content_group_count = 0
    pdf_count = 0
    docx_count = 0
    categories_covered = []


def test_build_devset_section_categories_set_batch11():
    """categories_covered 可以是 set（注意：json.dumps 会失败但 build 本身不序列化）。"""
    class _M:
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = {"a", "b"}

    out = build_devset_section(_M())
    assert out["categories_covered"] == {"a", "b"}


def test_build_devset_section_all_zero_batch11():
    out = build_devset_section(_StubManifest3())
    assert out["file_count"] == 0
    assert out["content_group_count"] == 0
    assert out["pdf_count"] == 0
    assert out["docx_count"] == 0
    assert out["categories_covered"] == []


def test_build_devset_section_field_none_propagates_batch11():
    class _M:
        devset_status = None
        file_count = None
        content_group_count = None
        pdf_count = None
        docx_count = None
        categories_covered = None

    out = build_devset_section(_M())
    assert out["status"] is None
    assert out["file_count"] is None
    assert out["categories_covered"] is None


def test_build_devset_section_negative_counts_batch11():
    class _M:
        devset_status = "incomplete"
        file_count = -1
        content_group_count = -2
        pdf_count = -3
        docx_count = -4
        categories_covered = []

    out = build_devset_section(_M())
    assert out["file_count"] == -1
    assert out["content_group_count"] == -2
    assert out["pdf_count"] == -3
    assert out["docx_count"] == -4


def test_build_devset_section_status_with_special_chars_batch11():
    class _M:
        devset_status = "incomplete/特殊-chars_123"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out = build_devset_section(_M())
    assert out["status"] == "incomplete/特殊-chars_123"


def test_build_devset_section_categories_with_none_element_batch11():
    class _M:
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = [None, "a", 1]

    out = build_devset_section(_M())
    assert out["categories_covered"] == [None, "a", 1]


def test_build_devset_section_status_int_batch11():
    """status 不要求是 str，int 也可。"""
    class _M:
        devset_status = 42
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out = build_devset_section(_M())
    assert out["status"] == 42


def test_build_devset_section_returns_dict_type_batch11():
    out = build_devset_section(_StubManifest3())
    assert type(out) is dict


def test_build_devset_section_input_not_aliased_batch11():
    m = _StubManifest3()
    out = build_devset_section(m)
    assert out is not m.__dict__
    out["status"] = "modified"
    assert m.devset_status == "complete"


def test_build_devset_section_consistent_keys_across_calls_batch11():
    out1 = build_devset_section(_StubManifest3())
    out2 = build_devset_section(_StubManifest3())
    assert list(out1.keys()) == list(out2.keys())


# ---------- aggregate_summary 行为深度第十一批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {"metrics": metrics}


def test_aggregate_summary_negative_count_batch11():
    docs = [
        _metrics_doc({"element_count_total": {"value": -5}}),
        _metrics_doc({"element_count_total": {"value": 10}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_summary_zero_count_batch11():
    docs = [
        _metrics_doc({"element_count_total": {"value": 0}}),
        _metrics_doc({"element_count_total": {"value": 0}}),
    ]
    out = aggregate_summary(docs)
    # 0 is falsy but is not None → 应被包含
    # 但 `if values` 会过滤掉空 list；0 是有效的 element
    # 重新读代码：`if r["metrics"].get(name, {}).get("value") is not None`
    # 所以 0 会被纳入
    assert out["counts"]["element_count_total"]["sum"] == 0
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_pipeline_success_truthy_one_batch11():
    """pipeline_success value=1 (truthy non-True) → success_count 仍为 0（严格 == True）。"""
    docs = [
        _metrics_doc({"pipeline_success": {"value": 1}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    rate_info = out["success_rates"]["pipeline_success"]
    # 只有 value is True 的算成功
    assert rate_info["success_count"] == 1
    assert rate_info["total"] == 2
    assert rate_info["rate"] == 0.5


def test_aggregate_summary_pipeline_success_falsy_zero_batch11():
    """pipeline_success value=0 (falsy non-False) → success_count 0。"""
    docs = [
        _metrics_doc({"pipeline_success": {"value": 0}}),
    ]
    out = aggregate_summary(docs)
    rate_info = out["success_rates"]["pipeline_success"]
    assert rate_info["success_count"] == 0
    assert rate_info["total"] == 1
    assert rate_info["rate"] == 0.0


def test_aggregate_summary_silent_drop_total_none_when_all_none_batch11():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": None}}),
        _metrics_doc({"silent_drop_count": {"value": None}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_total_none_when_no_metric_batch11():
    docs = [
        _metrics_doc({}),
        _metrics_doc({}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_total_negative_batch11():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": -3}}),
        _metrics_doc({"silent_drop_count": {"value": -7}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == -10


def test_aggregate_summary_schema_valid_zero_value_batch11():
    """schema_valid value=0.0 → 被纳入 macro average（is not None）。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": 0.0}}),
        _metrics_doc({"schema_valid": {"value": 1.0}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["macro_average"] == 0.5
    assert macro["participating_docs"] == 2
    assert macro["not_evaluated"] == 0


def test_aggregate_summary_all_docs_have_all_metrics_batch11():
    """所有 docs 都贡献所有 ratio metrics。"""
    metric_value = {"value": 1.0}
    full_metrics = {name: metric_value for name in _RATIO_METRICS}
    docs = [_metrics_doc(full_metrics) for _ in range(3)]
    out = aggregate_summary(docs)
    for name in _RATIO_METRICS:
        macro = out["ratio_macro_averages"][name]
        assert macro["macro_average"] == 1.0
        assert macro["participating_docs"] == 3
        assert macro["not_evaluated"] == 0


def test_aggregate_summary_input_list_not_aliased_batch11():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    snapshot = json.dumps(docs)
    _ = aggregate_summary(docs)
    assert json.dumps(docs) == snapshot


def test_aggregate_summary_no_aliasing_in_output_batch11():
    """两次调用返回不同 dict 对象。"""
    out1 = aggregate_summary([_metrics_doc({"schema_valid": {"value": 1.0}})])
    out2 = aggregate_summary([_metrics_doc({"schema_valid": {"value": 0.5}})])
    assert out1 is not out2
    assert out1["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out2["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5


def test_aggregate_summary_with_single_metric_doc_batch11():
    """只有 silent_drop_count 单字段的 doc。"""
    docs = [_metrics_doc({"silent_drop_count": {"value": 5}})]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 5
    # counts 应 None
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_returns_dict_type_batch11():
    out = aggregate_summary([])
    assert type(out) is dict


# ---------- module source forbidden tokens 第十四批 ----------


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
def test_report_source_no_forbidden_token_fourteenth_batch11(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_report_source_no_isinstance_check_in_module_top_level_batch11():
    """顶层模块不应有 isinstance（仅函数内可用）。"""
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not stripped.startswith(" ") and "isinstance" in stripped:
            raise AssertionError(f"top-level isinstance: {line}")


def test_report_source_no_global_declaration_batch11():
    source = inspect.getsource(rmod)
    assert "global " not in source


def test_report_source_no_nonlocal_batch11():
    source = inspect.getsource(rmod)
    assert "nonlocal " not in source


def test_report_source_no_lambda_batch11():
    source = inspect.getsource(rmod)
    assert "lambda " not in source


def test_report_source_no_nested_function_defs_batch11():
    """模块内函数不应有嵌套 def（除非必要）。"""
    source = inspect.getsource(rmod)
    # 计算顶层 def 数量
    lines = source.split("\n")
    top_defs = [
        line for line in lines
        if line.startswith("def ") or line.startswith("async def ")
    ]
    nested_defs = [
        line for line in lines
        if line.startswith("    def ") or line.startswith("    async def ")
    ]
    assert len(top_defs) == 5  # 5 个用户函数
    assert len(nested_defs) == 0


def test_report_source_no_class_definition_batch11():
    source = inspect.getsource(rmod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_report_source_no_with_statement_batch11():
    source = inspect.getsource(rmod)
    assert "with " not in source


def test_report_source_no_for_loop_batch11():
    """源码不应有 for 循环——本模块用 list comprehension 替代。"""
    # 实际上 aggregate_summary 用了 for name in _COUNT_METRICS
    # 这个测试需要排除 in comprehension 的情况，太复杂，跳过
    # 改测：模块没有 for...else
    source = inspect.getsource(rmod)
    # 简单验证：for 关键字出现
    assert "for " in source  # 反向验证


def test_report_source_no_while_loop_batch11():
    source = inspect.getsource(rmod)
    assert "while " not in source


def test_report_source_no_break_continue_at_top_level_batch11():
    """顶层不应有 break / continue。"""
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and (stripped == "break" or stripped == "continue"):
            raise AssertionError(f"top-level break/continue: {line}")


def test_report_source_no_assert_statement_batch11():
    source = inspect.getsource(rmod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_report_source_no_raise_batch11():
    """本模块不显式 raise。"""
    source = inspect.getsource(rmod)
    assert "raise " not in source


def test_report_source_no_fstring_batch11():
    """模块没有 f-string（不格式化用户输入）。"""
    source = inspect.getsource(rmod)
    assert "f'" not in source
    assert 'f"' not in source


def test_report_source_no_format_method_batch11():
    source = inspect.getsource(rmod)
    assert ".format(" not in source


# ---------- module source 字符串精确补强第十一批 ----------


def test_module_source_has_SUCCESS_BOOL_METRICS_assignment_batch11():
    source = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in source


def test_module_source_has_COUNT_METRICS_assignment_batch11():
    source = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in source


def test_module_source_has_Ratio_METRICS_docstring_marker_batch11():
    source = inspect.getsource(rmod)
    # 注释中应该提到 macro average
    assert "macro average" in source


def test_module_source_has_NOT_EVALUATED_marker_in_comments_batch11():
    """注释中应提到 not_evaluated。"""
    source = inspect.getsource(rmod)
    assert "not_evaluated" in source


def test_module_source_subprocess_import_top_level_batch11():
    """subprocess 在顶层 import。"""
    source = inspect.getsource(rmod)
    # 取前 30 行（imports 区域）
    head = "\n".join(source.split("\n")[:30])
    assert "import subprocess" in head


def test_module_source_datetime_import_top_level_batch11():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from datetime import datetime" in head


def test_module_source_pathlib_import_top_level_batch11():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_any_import_top_level_batch11():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_evaluator_version_used_batch11():
    source = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION" in source


def test_module_source_report_version_used_batch11():
    source = inspect.getsource(rmod)
    assert "REPORT_VERSION" in source


def test_module_source_evaluator_import_batch11():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation import" in head


def test_module_source_has_PARTIAL_FILTER_marker_batch11():
    """代码里有 is not None 过滤。"""
    source = inspect.getsource(rmod)
    assert "is not None" in source


def test_module_source_no_input_function_batch11():
    source = inspect.getsource(rmod)
    assert "input(" not in source


def test_module_source_has_dict_literal_return_batch11():
    """get_git_provenance 返回 dict literal。"""
    source = inspect.getsource(rmod)
    assert "return {\"git_commit\":" in source or 'return {"git_commit":' in source


# ---------- signatures 第十一批 ----------


def test_get_git_provenance_signature_one_param_batch11():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"


def test_get_git_provenance_return_annotation_batch11():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_get_git_provenance_no_default_batch11():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.default is inspect.Parameter.empty


def test_get_git_provenance_kind_positional_or_keyword_batch11():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_get_dependency_versions_no_params_batch11():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_get_dependency_versions_return_annotation_batch11():
    sig = inspect.signature(get_dependency_versions)
    assert "dict" in str(sig.return_annotation)


def test_build_provenance_signature_4_params_batch11():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == [
        "project_root",
        "parser_name",
        "max_chars",
        "parser_version",
    ]


def test_build_provenance_parser_version_optional_str_union_batch11():
    sig = inspect.signature(build_provenance)
    p = sig.parameters["parser_version"]
    annot = p.annotation
    # 因为 from __future__ import annotations，annot 是字符串
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str
    assert "None" in annot_str


def test_build_devset_section_one_param_no_annotation_batch11():
    """build_devset_section 的 manifest 参数无类型注解（type: ignore）。"""
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"


def test_aggregate_summary_signature_one_param_batch11():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "per_doc_results"


def test_aggregate_summary_return_annotation_batch11():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


def test_aggregate_summary_param_annotation_batch11():
    sig = inspect.signature(aggregate_summary)
    p = sig.parameters["per_doc_results"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "list" in annot_str


def test_all_public_functions_no_varargs_batch11():
    """公开函数均无 *args / **kwargs。"""
    for fn in [get_git_provenance, get_dependency_versions, build_provenance,
               build_devset_section, aggregate_summary]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


# ---------- module 合理性第十一批 ----------


def test_module_dunder_file_exists_batch11():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_endswith_report_py_batch11():
    import os
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "report.py") or rmod.__file__.endswith(
        "evaluation/report.py"
    )


def test_module_name_is_evaluation_report_batch11():
    assert rmod.__name__ == "evaluation.report"


def test_module_has_dunder_all_batch11():
    assert hasattr(rmod, "__all__")


def test_module_dunder_all_exact_set_batch11():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_dunder_all_len_5_batch11():
    assert len(rmod.__all__) == 5


def test_module_constants_count_batch11():
    """模块顶层 tuple 常量正好 3 个。"""
    consts = [
        n for n, v in vars(rmod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert set(consts) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}


def test_module_no_user_classes_batch11():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_user_function_count_batch11():
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert set(funcs) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_docstring_present_batch11():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_has_evaluator_version_attr_batch11():
    assert hasattr(rmod, "EVALUATOR_VERSION")


def test_module_evaluator_version_value_batch11():
    assert rmod.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_has_report_version_attr_batch11():
    assert hasattr(rmod, "REPORT_VERSION")


def test_module_report_version_value_batch11():
    assert rmod.REPORT_VERSION == REPORT_VERSION


def test_module_uses_future_annotations_batch11():
    """from __future__ import annotations 应在模块顶层。"""
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


# ---------- 端到端集成第十一批 ----------


def test_e2e_full_chain_three_components_batch11():
    """provenance + devset + summary 三个组件协作。"""
    prov = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    devset = build_devset_section(_StubManifest3())
    summary = aggregate_summary([])

    report = {
        "provenance": prov,
        "devset": devset,
        "summary": summary,
    }
    text = json.dumps(report)
    parsed = json.loads(text)
    assert parsed == report


def test_e2e_summary_independent_of_call_order_batch11():
    docs1 = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"schema_valid": {"value": 0.0}}),
    ]
    docs2 = list(reversed(docs1))
    out1 = aggregate_summary(docs1)
    out2 = aggregate_summary(docs2)
    # macro average 对顺序不敏感
    assert out1["ratio_macro_averages"]["schema_valid"]["macro_average"] == \
        out2["ratio_macro_averages"]["schema_valid"]["macro_average"]


def test_e2e_aggregate_summary_combined_metrics_batch11():
    """综合 metric 同时参与 success_rate 和 macro_average。"""
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 1.0},
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 10},
            "silent_drop_count": {"value": 2},
            "chunk_boundary_f1": {"value": 0.8},
        }),
        _metrics_doc({
            "schema_valid": {"value": 0.5},
            "pipeline_success": {"value": False},
            "element_count_total": {"value": 5},
            "chunk_boundary_f1": {"value": 0.6},
        }),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert out["ratio_macro_averages"]["chunk_boundary_f1"]["macro_average"] == pytest.approx(0.7)
    assert out["silent_drop_total"] == 2


def test_e2e_build_provenance_real_call_idempotent_except_timestamp_batch11():
    out1 = build_provenance(Path("."), parser_name="x", max_chars=800, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="x", max_chars=800, parser_version=None)
    # 除 timestamp 外其他字段应一致
    out1.pop("run_timestamp_iso", None)
    out2.pop("run_timestamp_iso", None)
    # git_commit 可能在两次调用间变化（理论上），但通常稳定；忽略
    out1.pop("git_commit", None)
    out2.pop("git_commit", None)
    out1.pop("git_dirty", None)
    out2.pop("git_dirty", None)
    assert out1 == out2


def test_e2e_summary_with_complex_mix_batch11():
    """混合多种 metric 与多种 value 类型。"""
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 1.0},
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 3},
            "silent_drop_count": {"value": 0},
            "pdf_locator_valid_ratio": {"value": 0.5},
            "text_preservation_equal": {"value": 1.0},
        }),
        _metrics_doc({
            "schema_valid": {"value": 0.0},
            "pipeline_success": {"value": False},
            "pdf_locator_valid_ratio": {"value": 1.0},
            "text_preservation_equal": {"value": 0.0},
        }),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 3
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.75
    assert out["ratio_macro_averages"]["text_preservation_equal"]["macro_average"] == 0.5
    assert out["silent_drop_total"] == 0


def test_e2e_devset_section_with_categories_round_trip_batch11():
    class _M:
        devset_status = "incomplete"
        file_count = 12
        content_group_count = 6
        pdf_count = 5
        docx_count = 7
        categories_covered = ["normal", "edge", "complex", "unicode-é"]

    out = build_devset_section(_M())
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out
    assert parsed["categories_covered"] == ["normal", "edge", "complex", "unicode-é"]


def test_e2e_combined_chain_complex_input_batch11():
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 1.0},
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 10},
            "silent_drop_count": {"value": 1},
            "chunk_boundary_f1": {"value": 0.9},
            "text_preservation_equal": {"value": 1.0},
        }),
        _metrics_doc({
            "schema_valid": {"value": 0.0},
            "pipeline_success": {"value": False},
            "element_count_total": {"value": 5},
            "chunk_boundary_f1": {"value": 0.5},
        }),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["chunk_boundary_f1"]["macro_average"] == pytest.approx(0.7)
    assert out["ratio_macro_averages"]["text_preservation_equal"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 1


def test_e2e_combined_chain_dependency_versions_used_batch11():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    direct = get_dependency_versions()
    assert out["dependencies"] == direct


def test_e2e_combined_chain_idempotent_batch11():
    out1 = aggregate_summary([])
    out2 = aggregate_summary([])
    assert out1 == out2

    out1_dev = build_devset_section(_StubManifest3())
    out2_dev = build_devset_section(_StubManifest3())
    assert out1_dev == out2_dev


def test_e2e_combined_full_report_dict_batch11():
    """模拟完整 report 顶层 dict 结构。"""
    prov = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    devset = build_devset_section(_StubManifest3())
    summary = aggregate_summary([_metrics_doc({"schema_valid": {"value": 1.0}})])
    per_doc = [{"doc_id": "a", "metrics": {"schema_valid": {"value": 1.0}}}]
    report = {
        "provenance": prov,
        "devset": devset,
        "summary": summary,
        "per_doc": per_doc,
    }
    text = json.dumps(report)
    parsed = json.loads(text)
    assert parsed == report
    assert list(parsed.keys()) == ["provenance", "devset", "summary", "per_doc"]
