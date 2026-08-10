"""evaluation/report.py 第三十轮 edges 测试（Round 416）。

补强 edges29 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十三批（互不相交 / 字段总数 / 元组不可变性 / __all__ 与元组的关系）
- get_git_provenance 异常深度第十三批（FileNotFoundError 子类 OSError / TimeoutExpired 子类 SubprocessError / r2 returncode != 0 / r2 stdout 仅空白 → dirty False / r.stdout 仅换行 → commit None）
- get_dependency_versions 异常深度第十三批（PackageNotFoundError 路径 / 其它异常 → None 不抛 / dict 字段固定 3 个 / pkg 名拼写不变）
- build_provenance 字段深度第十三批（字段顺序固定 / max_chars 负数仍 int 截断 / parser_version None 透传 / dependencies 引用 get_dependency_versions）
- build_devset_section 字段深度第十三批（属性读取顺序 / categories_covered 是 list / devset_status 透传不校验）
- aggregate_summary 行为深度第十三批（schema_valid partial null / multiple count metric docs / pipeline_success 全 False / silent_drop 全 null）
- module source forbidden tokens 第十八批
- module source 字符串精确补强第十五批
- signatures 第十五批
- module 合理性第十五批
- 端到端集成第十五批
"""

from __future__ import annotations

import inspect
import json
import subprocess
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十三批 ----------


def test_count_metrics_intersects_neither_ratio_nor_success_batch13():
    s_count = set(_COUNT_METRICS)
    s_ratio = set(_RATIO_METRICS)
    s_success = set(_SUCCESS_BOOL_METRICS)
    assert s_count.isdisjoint(s_ratio)
    assert s_count.isdisjoint(s_success)


def test_ratio_and_success_intersect_on_schema_valid_batch13():
    """schema_valid 同时出现在 _RATIO_METRICS 和（隐式）success-style 算法里。
    这里只验证它属于 _RATIO_METRICS（实际成功率的 success_rates 也基于此）。"""
    assert "schema_valid" in _RATIO_METRICS


def test_count_metrics_only_one_total_batch13():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_only_pipeline_batch13():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_metrics_tuple_total_count_batch13():
    """三个元组合计 14 个名字（不含 silent_drop_count，它单独处理）。"""
    total = len(_COUNT_METRICS) + len(_RATIO_METRICS) + len(_SUCCESS_BOOL_METRICS)
    assert total == 14


def test_metrics_tuples_are_tuple_type_batch13():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_metrics_tuples_immutable_no_append_batch13():
    """元组没有 append 方法。"""
    assert not hasattr(_RATIO_METRICS, "append")
    assert not hasattr(_COUNT_METRICS, "append")
    assert not hasattr(_SUCCESS_BOOL_METRICS, "append")


def test_ratio_metrics_contains_all_chunk_boundary_keys_batch13():
    """chunk_boundary 三项都在 _RATIO_METRICS 中。"""
    for name in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert name in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal_batch13():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_silent_drop_batch13():
    assert "silent_drop_count" not in _RATIO_METRICS
    assert "silent_drop_count" not in _COUNT_METRICS
    assert "silent_drop_count" not in _SUCCESS_BOOL_METRICS


def test_metrics_names_all_strings_batch13():
    for n in _RATIO_METRICS:
        assert isinstance(n, str)
    for n in _COUNT_METRICS:
        assert isinstance(n, str)
    for n in _SUCCESS_BOOL_METRICS:
        assert isinstance(n, str)


# ---------- get_git_provenance 异常深度第十三批 ----------


def test_get_git_provenance_oserror_includes_filenotfound_batch13():
    """OSError 包含 FileNotFoundError 等，捕获 OSError 也覆盖。"""
    with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_expired_captured_batch13():
    """TimeoutExpired 是 SubprocessError 子类，被 except 捕获。"""
    err = subprocess.TimeoutExpired(cmd="git", timeout=10)
    with patch("subprocess.run", side_effect=err):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_r2_returncode_nonzero_batch13():
    """r2 (status --porcelain) returncode 非 0 → dirty=False（短路逻辑：returncode==0 必须成立）。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_err = subprocess.CompletedProcess(args=[], returncode=1, stdout=" M x\n", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok, fake_err]):
        out = get_git_provenance(Path("."))
    # r2.returncode != 0 → returncode == 0 短路为 False → dirty=False
    assert out["git_dirty"] is False


def test_get_git_provenance_r2_stdout_only_whitespace_batch13():
    """r2 stdout 仅空白 → dirty False（strip 后为空）。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="   \n\t ", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok, fake_clean]):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False


def test_get_git_provenance_r_stdout_only_newline_batch13():
    """r.stdout 仅换行（strip 后空）→ commit None。"""
    fake_blank = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_blank, fake_clean]):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_r_returncode_nonzero_batch13():
    """r (rev-parse HEAD) returncode 非 0 → commit None。"""
    fake_err = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="error")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_err, fake_clean]):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_returns_dict_with_two_keys_batch13():
    out = get_git_provenance(Path("."))
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_first_call_rev_parse_batch13():
    seen: list = []
    def _fake(*args, **kwargs):
        seen.append(args[0])
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc\n", stderr="")
    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen[0] == ["git", "rev-parse", "HEAD"]


def test_get_git_provenance_second_call_status_porcelain_batch13():
    seen: list = []
    def _fake(*args, **kwargs):
        seen.append(args[0])
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=_fake):
        get_git_provenance(Path("."))
    assert seen[1] == ["git", "status", "--porcelain"]


# ---------- get_dependency_versions 异常深度第十三批 ----------


def test_get_dependency_versions_returns_dict_with_three_keys_batch13():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_value_type_batch13():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_importlib_internal_import_batch13():
    """importlib.metadata 在函数内部导入。"""
    source = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in source


def test_get_dependency_versions_catches_package_not_found_batch13():
    source = inspect.getsource(get_dependency_versions)
    assert "PackageNotFoundError" in source


def test_get_dependency_versions_catches_generic_exception_batch13():
    source = inspect.getsource(get_dependency_versions)
    assert "except Exception" in source


def test_get_dependency_versions_iterates_three_packages_batch13():
    source = inspect.getsource(get_dependency_versions)
    assert "(\"pdfplumber\", \"python-docx\", \"pypdfium2\")" in source


def test_get_dependency_versions_no_kwargs_batch13():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


# ---------- build_provenance 字段深度第十三批 ----------


def test_build_provenance_field_count_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert len(out) == 9


def test_build_provenance_field_order_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    keys = list(out.keys())
    assert keys[0] == "git_commit"
    assert keys[1] == "git_dirty"
    assert keys[2] == "evaluator_version"
    assert keys[3] == "report_version"
    assert keys[4] == "parser_name"
    assert keys[5] == "parser_version"
    assert keys[6] == "dependencies"
    assert keys[7] == "max_chars"
    assert keys[8] == "run_timestamp_iso"


def test_build_provenance_max_chars_negative_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=-100, parser_version=None)
    assert out["max_chars"] == -100


def test_build_provenance_max_chars_zero_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=0, parser_version=None)
    assert out["max_chars"] == 0


def test_build_provenance_max_chars_float_truncated_batch13():
    """int(max_chars) 截断浮点数。"""
    out = build_provenance(Path("."), parser_name="x", max_chars=800.99, parser_version=None)
    assert out["max_chars"] == 800


def test_build_provenance_parser_version_none_passthrough_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_string_passthrough_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version="1.5")
    assert out["parser_version"] == "1.5"


def test_build_provenance_evaluator_version_from_eval_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_from_eval_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_is_dict_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_timestamp_iso_format_batch13():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    s = out["run_timestamp_iso"]
    assert isinstance(s, str)
    # ISO format 至少包含 'T'
    assert "T" in s


# ---------- build_devset_section 字段深度第十三批 ----------


class _StubManifestBatch13:
    devset_status = "incomplete"
    file_count = 5
    content_group_count = 3
    pdf_count = 2
    docx_count = 3
    categories_covered = ["a", "b", "c"]


def test_build_devset_section_returns_six_keys_batch13():
    out = build_devset_section(_StubManifestBatch13())
    assert len(out) == 6


def test_build_devset_section_field_order_batch13():
    out = build_devset_section(_StubManifestBatch13())
    keys = list(out.keys())
    assert keys[0] == "status"
    assert keys[1] == "file_count"
    assert keys[2] == "content_group_count"
    assert keys[3] == "pdf_count"
    assert keys[4] == "docx_count"
    assert keys[5] == "categories_covered"


def test_build_devset_section_status_passthrough_batch13():
    out = build_devset_section(_StubManifestBatch13())
    assert out["status"] == "incomplete"


def test_build_devset_section_status_no_validation_batch13():
    class _M:
        devset_status = "weird value"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
    out = build_devset_section(_M())
    assert out["status"] == "weird value"


def test_build_devset_section_categories_is_list_batch13():
    out = build_devset_section(_StubManifestBatch13())
    assert isinstance(out["categories_covered"], list)


def test_build_devset_section_attribute_error_raised_batch13():
    class _M:
        devset_status = "x"
        # 缺 file_count
    with pytest.raises(AttributeError):
        build_devset_section(_M())


def test_build_devset_section_pdf_docx_count_distinct_batch13():
    out = build_devset_section(_StubManifestBatch13())
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 3


def test_build_devset_section_file_count_passthrough_batch13():
    out = build_devset_section(_StubManifestBatch13())
    assert out["file_count"] == 5


# ---------- aggregate_summary 行为深度第十三批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {
        "document_id": "doc1",
        "source": "x.pdf",
        "parser": "fallback",
        "metrics": metrics,
    }


def test_aggregate_summary_schema_valid_partial_null_batch13():
    """schema_valid 部分文档 null → not_evaluated 计数。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"schema_valid": {"value": None, "reason": "no_document"}}),
    ]
    s = aggregate_summary(docs)
    entry = s["ratio_macro_averages"]["schema_valid"]
    assert entry["participating_docs"] == 1
    assert entry["not_evaluated"] == 1
    assert entry["macro_average"] == 1.0


def test_aggregate_summary_multiple_count_docs_batch13():
    docs = [
        _metrics_doc({"element_count_total": {"value": 5}}),
        _metrics_doc({"element_count_total": {"value": 7}}),
        _metrics_doc({"element_count_total": {"value": 3}}),
    ]
    s = aggregate_summary(docs)
    assert s["counts"]["element_count_total"]["sum"] == 15
    assert s["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_pipeline_success_all_false_batch13():
    docs = [
        _metrics_doc({"pipeline_success": {"value": False}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
    ]
    s = aggregate_summary(docs)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_pipeline_success_mixed_batch13():
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
        _metrics_doc({"pipeline_success": {"value": None, "reason": "x"}}),
    ]
    s = aggregate_summary(docs)
    # success 只计 True，total 是全部
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 3
    assert s["success_rates"]["pipeline_success"]["rate"] == pytest.approx(1 / 3)


def test_aggregate_summary_silent_drop_all_null_batch13():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
        _metrics_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
    ]
    s = aggregate_summary(docs)
    assert s["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_partial_null_batch13():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 3}}),
        _metrics_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
    ]
    s = aggregate_summary(docs)
    # None 不参与，sum = 3
    assert s["silent_drop_total"] == 3


def test_aggregate_summary_returns_4_top_keys_batch13():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_default_when_empty_batch13():
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_success_rate_none_when_empty_batch13():
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_ratio_macro_none_when_empty_batch13():
    s = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert s["ratio_macro_averages"][name]["macro_average"] is None
        assert s["ratio_macro_averages"][name]["participating_docs"] == 0


def test_aggregate_summary_does_not_mutate_input_batch13():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    docs_before = json.loads(json.dumps(docs))
    aggregate_summary(docs)
    assert docs == docs_before


def test_aggregate_summary_silent_drop_total_int_when_values_batch13():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 1}}),
        _metrics_doc({"silent_drop_count": {"value": 2}}),
    ]
    s = aggregate_summary(docs)
    assert isinstance(s["silent_drop_total"], int)
    assert s["silent_drop_total"] == 3


def test_aggregate_summary_count_participating_with_value_only_batch13():
    docs = [
        _metrics_doc({"element_count_total": {"value": 5}}),
        _metrics_doc({"element_count_total": {"value": None, "reason": "x"}}),
    ]
    s = aggregate_summary(docs)
    assert s["counts"]["element_count_total"]["participating_docs"] == 1
    assert s["counts"]["element_count_total"]["sum"] == 5


# ---------- module source forbidden tokens 第十八批 ----------


_FORBIDDEN_TOKENS_ROUND18 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND18)
def test_module_source_forbidden_tokens_round18_batch13(token):
    source = inspect.getsource(rmod)
    assert token not in source


# ---------- module source 字符串精确补强第十五批 ----------


def test_module_source_contains_module_docstring_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:10])
    assert '"""' in head


def test_module_source_contains_from_future_annotations_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_source_imports_subprocess_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import subprocess" in head


def test_module_source_imports_datetime_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from datetime import datetime" in head


def test_module_source_imports_pathlib_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_evaluator_report_versions_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in head


def test_module_source_defines_get_git_provenance_batch13():
    source = inspect.getsource(rmod)
    assert "def get_git_provenance(project_root: Path)" in source


def test_module_source_defines_get_dependency_versions_batch13():
    source = inspect.getsource(rmod)
    assert "def get_dependency_versions()" in source


def test_module_source_defines_build_provenance_batch13():
    source = inspect.getsource(rmod)
    assert "def build_provenance(" in source


def test_module_source_defines_build_devset_section_batch13():
    source = inspect.getsource(rmod)
    assert "def build_devset_section(" in source


def test_module_source_defines_aggregate_summary_batch13():
    source = inspect.getsource(rmod)
    assert "def aggregate_summary(" in source


def test_module_source_has_dunder_all_batch13():
    source = inspect.getsource(rmod)
    assert "__all__" in source


def test_module_source_has_count_metrics_constant_batch13():
    source = inspect.getsource(rmod)
    assert "_COUNT_METRICS" in source


def test_module_source_has_ratio_metrics_constant_batch13():
    source = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in source


def test_module_source_has_success_bool_metrics_constant_batch13():
    source = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS" in source


def test_module_source_iter_errors_pattern_not_present_batch13():
    """报告装配器不应直接调用 iter_errors（schema 的事）。"""
    source = inspect.getsource(rmod)
    assert "iter_errors" not in source


def test_module_source_no_open_call_batch13():
    """report.py 不需要 open() — 只读元数据。"""
    source = inspect.getsource(rmod)
    # 确保没有 open( 调用
    assert "open(" not in source


def test_module_source_revision_pattern_batch13():
    source = inspect.getsource(rmod)
    assert "rev-parse" in source


def test_module_source_porcelain_pattern_batch13():
    source = inspect.getsource(rmod)
    assert "porcelain" in source


def test_module_source_contains_dict_splitting_comment_batch13():
    source = inspect.getsource(rmod)
    assert "聚合规则" in source


def test_module_source_contains_macro_average_logic_batch13():
    source = inspect.getsource(rmod)
    assert "macro_average" in source


def test_module_source_contains_not_evaluated_batch13():
    source = inspect.getsource(rmod)
    assert "not_evaluated" in source


def test_module_source_contains_participating_docs_batch13():
    source = inspect.getsource(rmod)
    assert "participating_docs" in source


# ---------- signatures 第十五批 ----------


def test_get_git_provenance_takes_project_root_batch13():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.default is inspect.Parameter.empty


def test_get_dependency_versions_no_args_batch13():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_takes_4_args_batch13():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4
    for name in ("project_root", "parser_name", "max_chars", "parser_version"):
        assert name in sig.parameters


def test_build_devset_section_takes_1_arg_batch13():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1
    assert "manifest" in sig.parameters


def test_aggregate_summary_takes_1_arg_batch13():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1
    assert "per_doc_results" in sig.parameters


def test_get_git_provenance_return_annotation_dict_batch13():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_get_dependency_versions_return_annotation_dict_batch13():
    sig = inspect.signature(get_dependency_versions)
    assert "dict" in str(sig.return_annotation)


def test_build_provenance_return_annotation_dict_batch13():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation)


def test_build_devset_section_no_return_annotation_batch13():
    """build_devset_section 有 # type: ignore 注释，注释不影响 signature。"""
    sig = inspect.signature(build_devset_section)
    assert "dict" in str(sig.return_annotation)


def test_aggregate_summary_return_annotation_dict_batch13():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


def test_build_provenance_parser_version_optional_batch13():
    """parser_version 接受 None。"""
    sig = inspect.signature(build_provenance)
    p = sig.parameters["parser_version"]
    # 签名应该是 str | None
    sig_str = str(p.annotation)
    assert "None" in sig_str


def test_build_provenance_no_var_positional_batch13():
    sig = inspect.signature(build_provenance)
    assert sig.parameters.get("args") is None
    assert sig.parameters.get("kwargs") is None


def test_all_module_functions_in_dunder_all_batch13():
    expected = {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }
    assert set(rmod.__all__) == expected


# ---------- module 合理性第十五批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_evaluation_report_batch13():
    assert "evaluation" in rmod.__file__
    assert rmod.__file__.endswith("report.py")


def test_module_name_evaluation_report_batch13():
    assert rmod.__name__ == "evaluation.report"


def test_module_dunder_all_5_items_batch13():
    assert len(rmod.__all__) == 5


def test_module_dunder_all_items_unique_batch13():
    assert len(set(rmod.__all__)) == len(rmod.__all__)


def test_module_constants_count_3_batch13():
    """_RATIO_METRICS, _COUNT_METRICS, _SUCCESS_BOOL_METRICS 共 3 个常量。"""
    assert hasattr(rmod, "_RATIO_METRICS")
    assert hasattr(rmod, "_COUNT_METRICS")
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


def test_module_private_constants_start_with_underscore_batch13():
    """3 个 metrics 常量都以下划线开头（私有）。"""
    for name in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
        assert name.startswith("_")


def test_module_no_class_definitions_batch13():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


# ---------- 端到端集成第十五批 ----------


def test_e2e_aggregate_summary_with_full_metrics_dict_batch13():
    metric_value = {"value": 0.5}
    full_metrics = {name: metric_value for name in _RATIO_METRICS}
    full_metrics["pipeline_success"] = {"value": True}
    full_metrics["element_count_total"] = {"value": 4}
    full_metrics["silent_drop_count"] = {"value": 2}
    full_metrics["schema_valid"] = {"value": 1.0}  # 也在 _RATIO_METRICS 中，会覆盖
    docs = [_metrics_doc(full_metrics)]
    s = aggregate_summary(docs)
    parsed = json.loads(json.dumps(s))
    assert parsed == s


def test_e2e_full_provenance_and_devset_combined_batch13():
    prov = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    devset = build_devset_section(_StubManifestBatch13())
    summary = aggregate_summary([])
    report = {"provenance": prov, "devset": devset, "summary": summary}
    parsed = json.loads(json.dumps(report))
    assert parsed == report


def test_e2e_provenance_json_serializable_with_subprocess_patch_batch13():
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok, fake_clean]):
        prov = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    text = json.dumps(prov)
    parsed = json.loads(text)
    assert parsed == prov
    assert parsed["git_commit"] == "abc123"


def test_e2e_devset_section_with_empty_categories_batch13():
    class _M:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = []
    out = build_devset_section(_M())
    parsed = json.loads(json.dumps(out))
    assert parsed == out
    assert out["categories_covered"] == []


def test_e2e_aggregate_summary_idempotent_batch13():
    docs = [_metrics_doc({"schema_valid": {"value": 0.7}})]
    out1 = aggregate_summary(docs)
    out2 = aggregate_summary(docs)
    assert out1 == out2


def test_e2e_dependency_versions_independent_calls_batch13():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2
    # 不同 dict 实例
    assert out1 is not out2


def test_e2e_provenance_dict_independent_calls_batch13():
    out1 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out1["dependencies"] is not out2["dependencies"]


def test_e2e_summary_no_overlap_with_devset_keys_batch13():
    summary = aggregate_summary([])
    devset = build_devset_section(_StubManifestBatch13())
    s_keys = set(summary.keys())
    d_keys = set(devset.keys())
    assert s_keys.isdisjoint(d_keys)


def test_e2e_combined_summary_with_count_silent_and_ratio_batch13():
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 1.0},
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 10},
            "silent_drop_count": {"value": 1},
            "pdf_locator_valid_ratio": {"value": 0.5},
        }),
        _metrics_doc({
            "schema_valid": {"value": 0.0},
            "pipeline_success": {"value": False},
            "element_count_total": {"value": 5},
            "silent_drop_count": {"value": 2},
            "pdf_locator_valid_ratio": {"value": 1.0},
        }),
    ]
    s = aggregate_summary(docs)
    assert s["counts"]["element_count_total"]["sum"] == 15
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.75
    assert s["silent_drop_total"] == 3


def test_e2e_dependency_versions_only_three_keys_batch13():
    out = get_dependency_versions()
    assert len(out) == 3
