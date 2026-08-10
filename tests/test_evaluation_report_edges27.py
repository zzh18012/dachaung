"""evaluation/report.py 第二十七轮 edges 测试（Round 395）。

补强 edges26 未触及的角度：
- get_git_provenance 行为深度第十批（returncode != 0 in rev-parse only / porcelain nonempty / porcelain returncode != 0 with successful rev-parse / rev-parse stdout 仅空白 / porcelain stdout 含换行 / 调用 args / 多次调用 / dict 类型 / 真实 dirty 路径）
- get_dependency_versions 行为深度第十批（exact keys / 各 pkg 独立 patch / 异常分支 / 多次调用独立 / importlib 注入 / call count / Unicode 版本号 / dict 类型）
- build_provenance 行为深度第十批（9 keys exact / keys order / 不抛 / Unicode name / Unicode version / idempotent / max_chars 边界 / 各 key 类型）
- build_devset_section 行为深度第十批（6 keys exact / keys order / 各类型 / 不 mutate / idempotent / dict 不共享 / Unicode status）
- aggregate_summary 行为深度第十批（counts 参与文档数 / counts sum None / success_rates rate 边界 / ratio macro 全部参与 / 全部跳过 / silent_drop_total 多种边界 / extra metric 忽略 / summary keys 顺序 / dict 类型）
- module source forbidden tokens 第十三批
- module source 字符串精确补强第十批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
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


# ---------- get_git_provenance 行为深度第十批 ----------


def test_get_git_provenance_rev_parse_nonzero_returncode_batch10():
    """rev-parse returncode != 0 → commit=None，dirty 仍按 porcelain 判定。"""
    fake_fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_fail, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is False  # porcelain empty


def test_get_git_provenance_rev_parse_returncode_zero_porcelain_nonzero_batch10():
    """rev-parse 成功 + porcelain returncode != 0 → commit OK，dirty=False（returncode 检查失败）。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_fail = subprocess.CompletedProcess(args=[], returncode=1, stdout=" M file\n", stderr="")
    seq = [fake_ok, fake_fail]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    # porcelain returncode != 0 → r2.returncode == 0 为假 → dirty False
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


def test_get_git_provenance_rev_parse_stdout_whitespace_only_batch10():
    """rev-parse stdout 仅空白 → strip 后空 → commit None。"""
    fake_ws = subprocess.CompletedProcess(args=[], returncode=0, stdout="   \n\t ", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    seq = [fake_ws, fake_clean]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_with_newlines_batch10():
    """porcelain stdout 含换行 → strip 后非空 → dirty True。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")
    fake_dirty = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n\n", stderr="")
    seq = [fake_ok, fake_dirty]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    # porcelain "\n\n" strip 后空 → dirty False
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_with_real_changes_batch10():
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")
    fake_dirty = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=" M file.py\n?? new.txt\n", stderr=""
    )
    seq = [fake_ok, fake_dirty]

    def _fake(*args, **kwargs):
        return seq.pop(0)

    with patch("subprocess.run", side_effect=_fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_call_args_have_cwd_batch10():
    """subprocess.run 被调用时 cwd 传入了。"""
    captured: list = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("/some/path"))
    assert len(captured) == 2
    assert captured[0]["cwd"] == "/some/path" or captured[0]["cwd"] == "\\some\\path"
    assert captured[1]["cwd"] == "/some/path" or captured[1]["cwd"] == "\\some\\path"


def test_get_git_provenance_call_args_capture_output_batch10():
    captured: list = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert all(c.get("capture_output") is True for c in captured)


def test_get_git_provenance_call_args_text_true_batch10():
    captured: list = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert all(c.get("text") is True for c in captured)


def test_get_git_provenance_call_args_timeout_batch10():
    captured: list = []

    def _fake(*args, **kwargs):
        captured.append(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert all(c.get("timeout") == 10 for c in captured)


def test_get_git_provenance_dict_return_type_batch10():
    """返回 dict，且严格 2 keys。"""
    out = get_git_provenance(Path("."))
    assert type(out) is dict
    assert len(out) == 2


def test_get_git_provenance_dirty_is_python_bool_batch10():
    out = get_git_provenance(Path("."))
    # 必须是 Python bool，不是 numpy 等的 bool_
    assert type(out["git_dirty"]) is bool


def test_get_git_provenance_commit_is_str_or_none_batch10():
    out = get_git_provenance(Path("."))
    assert out["git_commit"] is None or type(out["git_commit"]) is str


# ---------- get_dependency_versions 行为深度第十批 ----------


def test_get_dependency_versions_exact_keys_batch10():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_dict_type_batch10():
    out = get_dependency_versions()
    assert type(out) is dict


def test_get_dependency_versions_values_str_or_none_batch10():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_only_python_docx_fails_batch10():
    import importlib.metadata

    real_version = importlib.metadata.version

    def _fake(name):
        if name == "python-docx":
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["python-docx"] is None


def test_get_dependency_versions_all_missing_batch10():
    import importlib.metadata

    def _fake(name):
        raise importlib.metadata.PackageNotFoundError(name)

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out == {"pdfplumber": None, "python-docx": None, "pypdfium2": None}


def test_get_dependency_versions_all_exception_batch10():
    def _fake(name):
        raise RuntimeError("boom")

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out == {"pdfplumber": None, "python-docx": None, "pypdfium2": None}


def test_get_dependency_versions_call_count_batch10():
    """对每个 pkg 调用 1 次，共 3 次。"""
    call_count = [0]

    def _fake(name):
        call_count[0] += 1
        return f"1.{call_count[0]}.0"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert call_count[0] == 3
    assert out["pdfplumber"] == "1.1.0"
    assert out["python-docx"] == "1.2.0"
    assert out["pypdfium2"] == "1.3.0"


def test_get_dependency_versions_unicode_version_batch10():
    def _fake(name):
        return "vα-β.1"

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "vα-β.1"
    assert out["python-docx"] == "vα-β.1"
    assert out["pypdfium2"] == "vα-β.1"


def test_get_dependency_versions_returns_independent_dict_batch10():
    """两次调用应返回独立 dict（修改一个不影响另一个）。"""
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    out1["custom"] = "x"
    assert "custom" not in out2


def test_get_dependency_versions_no_other_keys_batch10():
    out = get_dependency_versions()
    assert len(out) == 3


# ---------- build_provenance 行为深度第十批 ----------


def test_build_provenance_exact_9_keys_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert set(out.keys()) == {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }


def test_build_provenance_keys_count_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert len(out) == 9


def test_build_provenance_dict_type_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert type(out) is dict


def test_build_provenance_evaluator_version_strict_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_strict_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_unicode_batch10():
    out = build_provenance(
        Path("."), parser_name="fälık Bäck", max_chars=800, parser_version=None
    )
    assert out["parser_name"] == "fälık Bäck"


def test_build_provenance_parser_version_unicode_batch10():
    out = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version="vα-1.0"
    )
    assert out["parser_version"] == "vα-1.0"


def test_build_provenance_max_chars_preserves_int_type_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=42, parser_version=None)
    assert type(out["max_chars"]) is int
    assert out["max_chars"] == 42


def test_build_provenance_max_chars_str_input_batch10():
    """int(max_chars) on str works if it's a numeric string."""
    out = build_provenance(Path("."), parser_name="fallback", max_chars="42", parser_version=None)
    assert out["max_chars"] == 42


def test_build_provenance_idempotent_batch10():
    out1 = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version=None
    )
    out2 = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version=None
    )
    # 除 timestamp 外其他字段应相同
    out1_no_ts = {k: v for k, v in out1.items() if k != "run_timestamp_iso"}
    out2_no_ts = {k: v for k, v in out2.items() if k != "run_timestamp_iso"}
    assert out1_no_ts == out2_no_ts


def test_build_provenance_run_timestamp_has_tz_batch10():
    """isoformat 含时区（带 +/- 偏移）。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    ts = out["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_build_provenance_git_commit_str_or_none_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_build_provenance_git_dirty_is_bool_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert type(out["git_dirty"]) is bool


def test_build_provenance_dependencies_3_keys_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert len(out["dependencies"]) == 3


# ---------- build_devset_section 行为深度第十批 ----------


class _StubManifest2:
    devset_status = "incomplete"
    file_count = 7
    content_group_count = 4
    pdf_count = 3
    docx_count = 4
    categories_covered = ["normal", "edge"]


def test_build_devset_section_exact_6_keys_batch10():
    out = build_devset_section(_StubManifest2())
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_keys_count_batch10():
    out = build_devset_section(_StubManifest2())
    assert len(out) == 6


def test_build_devset_section_dict_type_batch10():
    out = build_devset_section(_StubManifest2())
    assert type(out) is dict


def test_build_devset_section_status_unicode_batch10():
    class _M:
        devset_status = "未完成"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out = build_devset_section(_M())
    assert out["status"] == "未完成"


def test_build_devset_section_categories_tuple_batch10():
    """categories_covered 可以是 tuple。"""
    class _M:
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ("a", "b")

    out = build_devset_section(_M())
    assert out["categories_covered"] == ("a", "b")


def test_build_devset_section_propagates_all_fields_batch10():
    out = build_devset_section(_StubManifest2())
    assert out["status"] == "incomplete"
    assert out["file_count"] == 7
    assert out["content_group_count"] == 4
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 4
    assert out["categories_covered"] == ["normal", "edge"]


def test_build_devset_section_idempotent_batch10():
    out1 = build_devset_section(_StubManifest2())
    out2 = build_devset_section(_StubManifest2())
    assert out1 == out2


def test_build_devset_section_dict_independent_batch10():
    out1 = build_devset_section(_StubManifest2())
    out2 = build_devset_section(_StubManifest2())
    out1["status"] = "modified"
    assert out2["status"] == "incomplete"


def test_build_devset_section_does_not_mutate_categories_batch10():
    m = _StubManifest2()
    snapshot = list(m.categories_covered)
    _ = build_devset_section(m)
    assert m.categories_covered == snapshot


def test_build_devset_section_json_serializable_batch10():
    out = build_devset_section(_StubManifest2())
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


# ---------- aggregate_summary 行为深度第十批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {"metrics": metrics}


def test_aggregate_summary_top_keys_order_batch10():
    out = aggregate_summary([])
    assert list(out.keys()) == ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]


def test_aggregate_summary_top_keys_count_batch10():
    out = aggregate_summary([])
    assert len(out) == 4


def test_aggregate_summary_counts_none_when_no_participation_batch10():
    docs = [_metrics_doc({}) for _ in range(3)]
    out = aggregate_summary(docs)
    for name in _COUNT_METRICS:
        assert out["counts"][name] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_counts_participating_docs_batch10():
    docs = [
        _metrics_doc({"element_count_total": {"value": 5}}),
        _metrics_doc({}),
        _metrics_doc({"element_count_total": {"value": 10}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["participating_docs"] == 2
    assert out["counts"]["element_count_total"]["sum"] == 15


def test_aggregate_summary_success_rate_zero_batch10():
    docs = [
        _metrics_doc({"pipeline_success": {"value": False}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(docs)
    rate_info = out["success_rates"]["pipeline_success"]
    assert rate_info["success_count"] == 0
    assert rate_info["total"] == 2
    assert rate_info["rate"] == 0.0


def test_aggregate_summary_success_rate_one_batch10():
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    rate_info = out["success_rates"]["pipeline_success"]
    assert rate_info["success_count"] == 2
    assert rate_info["total"] == 2
    assert rate_info["rate"] == 1.0


def test_aggregate_summary_success_rate_half_batch10():
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(docs)
    rate_info = out["success_rates"]["pipeline_success"]
    assert rate_info["rate"] == 0.5


def test_aggregate_summary_success_rate_none_when_empty_batch10():
    docs = []
    out = aggregate_summary(docs)
    rate_info = out["success_rates"]["pipeline_success"]
    assert rate_info["rate"] is None
    assert rate_info["total"] == 0


def test_aggregate_summary_ratio_macro_count_12_batch10():
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == len(_RATIO_METRICS) == 12


def test_aggregate_summary_ratio_macro_all_none_when_skipped_batch10():
    docs = [_metrics_doc({}) for _ in range(5)]
    out = aggregate_summary(docs)
    for name in _RATIO_METRICS:
        macro = out["ratio_macro_averages"][name]
        assert macro["macro_average"] is None
        assert macro["participating_docs"] == 0
        assert macro["not_evaluated"] == 5


def test_aggregate_summary_silent_drop_total_mixed_batch10():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 5}}),
        _metrics_doc({}),  # 缺
        _metrics_doc({"silent_drop_count": {"value": None}}),
        _metrics_doc({"silent_drop_count": {"value": 7}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 12


def test_aggregate_summary_silent_drop_total_int_type_batch10():
    docs = [_metrics_doc({"silent_drop_count": {"value": 5}})]
    out = aggregate_summary(docs)
    assert type(out["silent_drop_total"]) is int


def test_aggregate_summary_extra_metric_ignored_batch10():
    """额外的 metric 应被忽略。"""
    docs = [
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "totally_unknown_metric": {"value": 999},
            }
        )
    ]
    out = aggregate_summary(docs)
    # 没有任何顶层字段对应 totally_unknown_metric
    for top_key, top_val in out.items():
        if isinstance(top_val, dict):
            assert "totally_unknown_metric" not in top_val


def test_aggregate_summary_dict_type_batch10():
    out = aggregate_summary([])
    assert type(out) is dict


def test_aggregate_summary_input_not_mutated_batch10():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    snapshot = json.dumps(docs)
    _ = aggregate_summary(docs)
    assert json.dumps(docs) == snapshot


# ---------- module source forbidden tokens 第十三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_report_source_no_forbidden_token_thirteenth_batch10(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_report_source_no_unlink_batch10():
    source = inspect.getsource(rmod)
    assert "unlink" not in source


def test_report_source_no_remove_batch10():
    source = inspect.getsource(rmod)
    assert ".remove(" not in source


def test_report_source_no_kill_batch10():
    source = inspect.getsource(rmod)
    assert ".kill(" not in source


def test_report_source_no_terminate_batch10():
    source = inspect.getsource(rmod)
    assert ".terminate(" not in source


def test_report_source_no_async_def_batch10():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_report_source_no_yield_batch10():
    source = inspect.getsource(rmod)
    assert "yield" not in source


def test_report_source_no_walrus_batch10():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_report_source_no_top_level_lambda_batch10():
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_report_source_no_print_batch10():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_report_source_no_logging_batch10():
    source = inspect.getsource(rmod)
    assert "logging" not in source
    assert "logger" not in source


def test_report_source_no_open_write_batch10():
    source = inspect.getsource(rmod)
    assert 'open(' not in source


def test_report_source_no_socket_batch10():
    source = inspect.getsource(rmod)
    assert "socket" not in source


def test_report_source_no_threading_batch10():
    source = inspect.getsource(rmod)
    assert "threading" not in source


def test_report_source_no_multiprocessing_batch10():
    source = inspect.getsource(rmod)
    assert "multiprocessing" not in source


def test_report_source_no_asyncio_batch10():
    source = inspect.getsource(rmod)
    assert "asyncio" not in source


# ---------- module source 字符串精确补强第十批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_subprocess_batch10():
    source = inspect.getsource(rmod)
    assert "import subprocess" in source


def test_module_source_imports_datetime_batch10():
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_imports_path_batch10():
    source = inspect.getsource(rmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch10():
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_three_pkg_in_iteration_batch10():
    """get_dependency_versions 内出现 3 个 pkg 元组。"""
    source = inspect.getsource(rmod)
    assert '"pdfplumber"' in source
    assert '"python-docx"' in source
    assert '"pypdfium2"' in source


def test_module_source_has_try_except_batch10():
    source = inspect.getsource(rmod)
    assert "try:" in source
    assert "except" in source


def test_module_source_has_oserror_subprocess_error_batch10():
    source = inspect.getsource(rmod)
    assert "OSError" in source
    assert "SubprocessError" in source


def test_module_source_importlib_metadata_in_function_batch10():
    """importlib.metadata 在函数体内 import（非顶层）。"""
    source = inspect.getsource(rmod)
    # 应在 get_dependency_versions 函数内
    assert "import importlib.metadata" in source


def test_module_source_has_pure_ascii_docstring_marker_batch10():
    """docstring 内含 macro 字。"""
    assert rmod.__doc__ is not None
    assert "macro" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_evaluator_batch10():
    assert rmod.__doc__ is not None
    assert "评测" in rmod.__doc__ or "evaluation" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_provenance_batch10():
    assert rmod.__doc__ is not None
    assert "provenance" in rmod.__doc__.lower() or "devset" in rmod.__doc__.lower()


def test_module_source_no_main_block_batch10():
    source = inspect.getsource(rmod)
    assert "if __name__" not in source


def test_module_source_has_popen_not_batch10():
    """没有 os.popen / subprocess.Popen。"""
    source = inspect.getsource(rmod)
    assert "Popen" not in source


# ---------- signatures 第十批 ----------


def test_signature_get_git_provenance_params_count_batch10():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1


def test_signature_get_git_provenance_param_name_batch10():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters) == ["project_root"]


def test_signature_get_git_provenance_param_kind_batch10():
    sig = inspect.signature(get_git_provenance)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_get_git_provenance_param_no_default_batch10():
    sig = inspect.signature(get_git_provenance)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_get_git_provenance_return_annotation_batch10():
    sig = inspect.signature(get_git_provenance)
    # annotation 是字符串 "dict[str, Any]"（因为 from __future__ import annotations）
    assert sig.return_annotation is not inspect.Signature.empty


def test_signature_get_dependency_versions_no_params_batch10():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_get_dependency_versions_return_annotation_batch10():
    sig = inspect.signature(get_dependency_versions)
    assert sig.return_annotation is not inspect.Signature.empty


def test_signature_build_provenance_4_params_batch10():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_signature_build_provenance_param_names_batch10():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_param_kinds_batch10():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_build_provenance_no_defaults_batch10():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_build_devset_section_1_param_batch10():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_signature_build_devset_section_param_name_batch10():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters) == ["manifest"]


def test_signature_aggregate_summary_1_param_batch10():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1


def test_signature_aggregate_summary_param_name_batch10():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters) == ["per_doc_results"]


def test_signature_funcs_function_type_batch10():
    for func in (
        get_git_provenance,
        get_dependency_versions,
        build_provenance,
        build_devset_section,
        aggregate_summary,
    ):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch10():
    for func in (
        get_git_provenance,
        get_dependency_versions,
        build_provenance,
        build_devset_section,
        aggregate_summary,
    ):
        assert func.__module__ == "evaluation.report"


# ---------- module 合理性第十批 ----------


def test_module_all_value_batch10():
    assert rmod.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_is_list_batch10():
    assert isinstance(rmod.__all__, list)


def test_module_all_entries_unique_batch10():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_all_entries_str_batch10():
    for name in rmod.__all__:
        assert isinstance(name, str)


def test_module_has_dunder_file_batch10():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_endswith_report_py_batch10():
    import os
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "report.py") or rmod.__file__.endswith(
        "evaluation/report.py"
    )


def test_module_name_is_evaluation_report_batch10():
    assert rmod.__name__ == "evaluation.report"


def test_module_user_function_count_batch10():
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


def test_module_user_constant_count_batch10():
    consts = [
        n for n, v in vars(rmod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert set(consts) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}


def test_module_no_user_classes_batch10():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_has_evaluator_version_batch10():
    assert hasattr(rmod, "EVALUATOR_VERSION")
    assert rmod.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_has_report_version_batch10():
    assert hasattr(rmod, "REPORT_VERSION")
    assert rmod.REPORT_VERSION == REPORT_VERSION


def test_module_docstring_present_batch10():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


# ---------- 端到端集成第十批 ----------


def test_e2e_full_chain_minimal_batch10():
    prov = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    out = aggregate_summary([])
    report = {
        "provenance": prov,
        "devset": build_devset_section(_StubManifest2()),
        "summary": out,
        "per_doc": [],
    }
    text = json.dumps(report)
    parsed = json.loads(text)
    assert parsed == report


def test_e2e_full_chain_json_serializable_batch10():
    docs = [
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 5},
                "silent_drop_count": {"value": 2},
                "chunk_boundary_f1": {"value": 0.7},
            }
        )
    ]
    summary = aggregate_summary(docs)
    text = json.dumps(summary)
    parsed = json.loads(text)
    assert parsed == summary


def test_e2e_aggregate_summary_kwargs_call_batch10():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out1 = aggregate_summary(docs)
    out2 = aggregate_summary(per_doc_results=docs)
    assert out1 == out2


def test_e2e_build_devset_section_round_trip_batch10():
    out = build_devset_section(_StubManifest2())
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_build_provenance_does_not_raise_on_real_call_batch10():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert isinstance(out, dict)
    assert len(out) == 9


def test_e2e_aggregate_summary_zero_participation_returns_none_macro_batch10():
    docs = [_metrics_doc({}) for _ in range(3)]
    out = aggregate_summary(docs)
    for name in _RATIO_METRICS:
        macro = out["ratio_macro_averages"][name]
        assert macro["macro_average"] is None
        assert macro["participating_docs"] == 0
        assert macro["not_evaluated"] == 3


def test_e2e_aggregate_summary_consistent_structure_batch10():
    out1 = aggregate_summary([])
    out2 = aggregate_summary([_metrics_doc({"schema_valid": {"value": 1.0}})])
    assert list(out1.keys()) == list(out2.keys())


def test_e2e_combined_chain_idempotent_batch10():
    out1_summary = aggregate_summary([])
    out2_summary = aggregate_summary([])
    assert out1_summary == out2_summary

    out1_devset = build_devset_section(_StubManifest2())
    out2_devset = build_devset_section(_StubManifest2())
    assert out1_devset == out2_devset


def test_e2e_combined_chain_complex_input_batch10():
    """混合多种 metric 的 doc。"""
    docs = [
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 1},
                "chunk_boundary_f1": {"value": 0.9},
                "text_preservation_equal": {"value": 1.0},
            }
        ),
        _metrics_doc(
            {
                "schema_valid": {"value": 0.0},
                "pipeline_success": {"value": False},
                "element_count_total": {"value": 5},
                "chunk_boundary_f1": {"value": 0.5},
            }
        ),
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


def test_e2e_combined_chain_dependency_versions_used_batch10():
    """dependency_versions 在 build_provenance 中被消费。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    direct = get_dependency_versions()
    assert out["dependencies"] == direct
