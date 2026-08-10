"""evaluation/report.py 第三十一轮 edges 测试（Round 423）。

补强 edges30 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十四批（成员重复不可 / 元组长度 / __contains__ 行为 / set 操作）
- get_git_provenance 行为深度第十四批（r.stdout 含 trailing whitespace / r2.stdout 含 /r/n / git_commit 末尾换行 strip）
- get_dependency_versions 行为深度第十四批（返回 dict / 3 个固定 key / 调用 3 次 importlib.metadata）
- build_provenance 字段深度第十四批（9 个 key / 时间戳格式 / dependencies 引用 / git 引用）
- build_devset_section 字段深度第十四批（6 个 key / 返回新 dict / 属性读取顺序）
- aggregate_summary 行为深度第十四批（multiple ratios / silent_drop 0 vs None / count_sum_with_float_value / not_evaluated 计数）
- module source forbidden tokens 第十九批
- module source 字符串精确补强第十六批
- signatures 第十六批
- module 合理性第十六批
- 端到端集成第十六批
"""

from __future__ import annotations

import inspect
import json
import subprocess
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十四批 ----------


def test_ratio_metrics_unique_members_batch14():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_count_metrics_unique_members_batch14():
    assert len(_COUNT_METRICS) == len(set(_COUNT_METRICS))


def test_success_bool_metrics_unique_members_batch14():
    assert len(_SUCCESS_BOOL_METRICS) == len(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_length_12_batch14():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_length_1_batch14():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_length_1_batch14():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_ratio_metrics_contains_text_char_multiset_batch14():
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_pdf_docx_locator_batch14():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_batch14():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_batch14():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_batch14():
    assert "heading_boundary_compliance" in _RATIO_METRICS


# ---------- get_git_provenance 行为深度第十四批 ----------


def test_get_git_provenance_strips_trailing_newline_batch14():
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc1234\n", stderr="")
    fake2 = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake, fake2]):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc1234"


def test_get_git_provenance_strips_multiple_newlines_batch14():
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n\n\n", stderr="")
    fake2 = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake, fake2]):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc"


def test_get_git_provenance_r2_crlf_batch14():
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake2 = subprocess.CompletedProcess(args=[], returncode=0, stdout=" M x\r\n", stderr="")
    with patch("subprocess.run", side_effect=[fake, fake2]):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is True


def test_get_git_provenance_r2_with_only_cr_batch14():
    """r2 stdout 仅含 \r（也是 whitespace）→ strip 后空 → dirty False。"""
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake2 = subprocess.CompletedProcess(args=[], returncode=0, stdout="\r", stderr="")
    with patch("subprocess.run", side_effect=[fake, fake2]):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False


def test_get_git_provenance_returns_two_keys_only_batch14():
    out = get_git_provenance(Path("."))
    assert len(out) == 2


def test_get_git_provenance_returns_proper_types_batch14():
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake2 = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake, fake2]):
        out = get_git_provenance(Path("."))
    # git_commit 是 str 或 None
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)
    assert isinstance(out["git_dirty"], bool)


# ---------- get_dependency_versions 行为深度第十四批 ----------


def test_get_dependency_versions_keys_count_3_batch14():
    out = get_dependency_versions()
    assert len(out) == 3


def test_get_dependency_versions_value_none_or_str_batch14():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_has_pdfplumber_batch14():
    out = get_dependency_versions()
    assert "pdfplumber" in out


def test_get_dependency_versions_has_python_docx_batch14():
    out = get_dependency_versions()
    assert "python-docx" in out


def test_get_dependency_versions_has_pypdfium2_batch14():
    out = get_dependency_versions()
    assert "pypdfium2" in out


def test_get_dependency_versions_no_other_keys_batch14():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


# ---------- build_provenance 字段深度第十四批 ----------


def test_build_provenance_returns_9_keys_batch14():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert len(out) == 9


def test_build_provenance_keys_exact_batch14():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    expected = {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_dependencies_call_get_dependency_versions_batch14():
    """build_provenance 应调用 get_dependency_versions。"""
    with patch("evaluation.report.get_dependency_versions", return_value={"a": "1"}) as mock_fn:
        out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert mock_fn.called
    assert out["dependencies"] == {"a": "1"}


def test_build_provenance_calls_get_git_provenance_batch14():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
        out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["git_commit"] == "x"
    assert out["git_dirty"] is False


def test_build_provenance_parser_name_passthrough_batch14():
    out = build_provenance(Path("."), parser_name="my_parser", max_chars=100, parser_version=None)
    assert out["parser_name"] == "my_parser"


def test_build_provenance_evaluator_version_value_batch14():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_batch14():
    out = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    assert out["report_version"] == REPORT_VERSION


# ---------- build_devset_section 字段深度第十四批 ----------


class _StubManifestBatch14:
    devset_status = "incomplete"
    file_count = 5
    content_group_count = 3
    pdf_count = 2
    docx_count = 3
    categories_covered = ["a", "b", "c"]


def test_build_devset_section_returns_6_keys_batch14():
    out = build_devset_section(_StubManifestBatch14())
    assert len(out) == 6


def test_build_devset_section_returns_new_dict_batch14():
    m = _StubManifestBatch14()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 == out2
    assert out1 is not out2


def test_build_devset_section_reads_devset_status_batch14():
    out = build_devset_section(_StubManifestBatch14())
    assert out["status"] == _StubManifestBatch14().devset_status


def test_build_devset_section_reads_categories_batch14():
    out = build_devset_section(_StubManifestBatch14())
    assert out["categories_covered"] == ["a", "b", "c"]


def test_build_devset_section_attribute_order_batch14():
    """读取顺序：devset_status → file_count → content_group_count → pdf_count → docx_count → categories_covered。"""
    read_order: list = []
    class _M:
        @property
        def devset_status(self):
            read_order.append("devset_status")
            return "incomplete"
        @property
        def file_count(self):
            read_order.append("file_count")
            return 0
        @property
        def content_group_count(self):
            read_order.append("content_group_count")
            return 0
        @property
        def pdf_count(self):
            read_order.append("pdf_count")
            return 0
        @property
        def docx_count(self):
            read_order.append("docx_count")
            return 0
        @property
        def categories_covered(self):
            read_order.append("categories_covered")
            return []
    build_devset_section(_M())
    assert read_order == ["devset_status", "file_count", "content_group_count", "pdf_count", "docx_count", "categories_covered"]


# ---------- aggregate_summary 行为深度第十四批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {
        "document_id": "doc1",
        "source": "x.pdf",
        "parser": "fallback",
        "metrics": metrics,
    }


def test_aggregate_summary_multiple_ratios_batch14():
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 0.8},
            "pdf_locator_valid_ratio": {"value": 1.0},
        }),
        _metrics_doc({
            "schema_valid": {"value": 0.6},
            "pdf_locator_valid_ratio": {"value": 0.5},
        }),
    ]
    s = aggregate_summary(docs)
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == pytest.approx(0.7)
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == pytest.approx(0.75)


def test_aggregate_summary_silent_drop_zero_batch14():
    """silent_drop_count=0 也应参与求和。"""
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 0}}),
        _metrics_doc({"silent_drop_count": {"value": 3}}),
    ]
    s = aggregate_summary(docs)
    assert s["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_none_excluded_batch14():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": None, "reason": "x"}}),
        _metrics_doc({"silent_drop_count": {"value": 5}}),
    ]
    s = aggregate_summary(docs)
    assert s["silent_drop_total"] == 5


def test_aggregate_summary_count_with_float_value_batch14():
    """element_count_total 是 float（虽不该）→ sum 是 float。"""
    docs = [
        _metrics_doc({"element_count_total": {"value": 5.5}}),
        _metrics_doc({"element_count_total": {"value": 4.5}}),
    ]
    s = aggregate_summary(docs)
    assert s["counts"]["element_count_total"]["sum"] == 10.0


def test_aggregate_summary_not_evaluated_count_batch14():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"schema_valid": {"value": None, "reason": "x"}}),
        _metrics_doc({}),  # 缺 schema_valid
    ]
    s = aggregate_summary(docs)
    entry = s["ratio_macro_averages"]["schema_valid"]
    # total 3, participating 1
    assert entry["participating_docs"] == 1
    assert entry["not_evaluated"] == 2


def test_aggregate_summary_success_rate_with_none_value_batch14():
    """pipeline_success=None 不算 success。"""
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": None, "reason": "x"}}),
    ]
    s = aggregate_summary(docs)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_does_not_modify_input_batch14():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
    ]
    docs_before = json.loads(json.dumps(docs))
    aggregate_summary(docs)
    assert docs == docs_before


def test_aggregate_summary_returns_4_keys_batch14():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


# ---------- module source forbidden tokens 第十九批 ----------


_FORBIDDEN_TOKENS_ROUND19 = [
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


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND19)
def test_module_source_forbidden_tokens_round19_batch14(token):
    source = inspect.getsource(rmod)
    assert token not in source


# ---------- module source 字符串精确补强第十六批 ----------


def test_module_source_module_docstring_present_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_subprocess_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import subprocess" in head


def test_module_source_imports_pathlib_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_eval_versions_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation import" in head


def test_module_source_defines_get_git_provenance_batch14():
    source = inspect.getsource(rmod)
    assert "def get_git_provenance(" in source


def test_module_source_defines_build_provenance_batch14():
    source = inspect.getsource(rmod)
    assert "def build_provenance(" in source


def test_module_source_defines_aggregate_summary_batch14():
    source = inspect.getsource(rmod)
    assert "def aggregate_summary(" in source


def test_module_source_has_dunder_all_batch14():
    source = inspect.getsource(rmod)
    assert "__all__" in source


def test_module_source_dunder_all_count_5_batch14():
    assert len(rmod.__all__) == 5


def test_module_source_uses_subprocess_run_batch14():
    source = inspect.getsource(rmod)
    assert "subprocess.run" in source


def test_module_source_no_open_call_batch14():
    source = inspect.getsource(rmod)
    assert "open('/etc" not in source
    assert 'open("/etc' not in source


def test_module_source_no_subprocess_call_batch14():
    """不应使用 subprocess.call（旧 API）。"""
    source = inspect.getsource(rmod)
    assert "subprocess.call(" not in source


def test_module_source_has_rev_parse_batch14():
    source = inspect.getsource(rmod)
    assert "rev-parse" in source


def test_module_source_has_porcelain_batch14():
    source = inspect.getsource(rmod)
    assert "porcelain" in source


def test_module_source_has_macro_average_batch14():
    source = inspect.getsource(rmod)
    assert "macro_average" in source


def test_module_source_has_participating_docs_batch14():
    source = inspect.getsource(rmod)
    assert "participating_docs" in source


def test_module_source_has_success_rates_batch14():
    source = inspect.getsource(rmod)
    assert "success_rates" in source


def test_module_source_has_silent_drop_batch14():
    source = inspect.getsource(rmod)
    assert "silent_drop" in source


# ---------- signatures 第十六批 ----------


def test_get_git_provenance_one_param_batch14():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1
    assert "project_root" in sig.parameters


def test_get_dependency_versions_no_params_batch14():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_4_params_batch14():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_build_devset_section_1_param_batch14():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_aggregate_summary_1_param_batch14():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1


def test_build_provenance_return_dict_batch14():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation)


def test_aggregate_summary_return_dict_batch14():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


def test_all_dunder_all_callable_batch14():
    for name in rmod.__all__:
        assert callable(getattr(rmod, name))


# ---------- module 合理性第十六批 ----------


def test_module_dunder_file_exists_batch14():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_report_py_batch14():
    assert "evaluation" in rmod.__file__
    assert rmod.__file__.endswith("report.py")


def test_module_name_evaluation_report_batch14():
    assert rmod.__name__ == "evaluation.report"


def test_module_dunder_all_5_items_batch14():
    assert len(rmod.__all__) == 5


def test_module_dunder_all_items_unique_batch14():
    assert len(set(rmod.__all__)) == len(rmod.__all__)


def test_module_no_class_definitions_batch14():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_constants_count_3_batch14():
    assert hasattr(rmod, "_RATIO_METRICS")
    assert hasattr(rmod, "_COUNT_METRICS")
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


# ---------- 端到端集成第十六批 ----------


def test_e2e_full_provenance_with_subprocess_patch_batch14():
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok, fake_clean]):
        prov = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    parsed = json.loads(json.dumps(prov))
    assert parsed == prov
    assert parsed["git_commit"] == "abc123"


def test_e2e_devset_section_with_full_manifest_batch14():
    out = build_devset_section(_StubManifestBatch14())
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_aggregate_summary_with_full_metrics_dict_batch14():
    metric_value = {"value": 0.7}
    full_metrics = {name: metric_value for name in _RATIO_METRICS}
    full_metrics["pipeline_success"] = {"value": True}
    full_metrics["element_count_total"] = {"value": 10}
    full_metrics["silent_drop_count"] = {"value": 2}
    docs = [_metrics_doc(full_metrics)]
    s = aggregate_summary(docs)
    parsed = json.loads(json.dumps(s))
    assert parsed == s


def test_e2e_combined_three_components_json_serializable_batch14():
    """三个组件 key 不应重叠且都 json 可序列化。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok, fake_clean]):
        prov = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    devset = build_devset_section(_StubManifestBatch14())
    summary = aggregate_summary([])
    prov_keys = set(prov.keys())
    devset_keys = set(devset.keys())
    summary_keys = set(summary.keys())
    assert prov_keys.isdisjoint(devset_keys)
    assert prov_keys.isdisjoint(summary_keys)
    assert devset_keys.isdisjoint(summary_keys)


def test_e2e_provenance_idempotent_except_timestamp_batch14():
    out1 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    # 去掉 timestamp 后应相同
    out1_copy = dict(out1)
    out2_copy = dict(out2)
    out1_copy.pop("run_timestamp_iso", None)
    out2_copy.pop("run_timestamp_iso", None)
    assert out1_copy == out2_copy


def test_e2e_devset_independent_calls_batch14():
    out1 = build_devset_section(_StubManifestBatch14())
    out2 = build_devset_section(_StubManifestBatch14())
    assert out1 is not out2


def test_e2e_aggregate_summary_independent_dict_batch14():
    docs = [_metrics_doc({"schema_valid": {"value": 0.5}})]
    out1 = aggregate_summary(docs)
    out2 = aggregate_summary(docs)
    assert out1 is not out2
    assert out1 == out2


def test_e2e_combined_summary_full_pipeline_batch14():
    docs = [
        _metrics_doc({
            "schema_valid": {"value": 1.0},
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 5},
            "silent_drop_count": {"value": 1},
            "pdf_locator_valid_ratio": {"value": 0.5},
            "chunk_reference_intact_ratio": {"value": 1.0},
        }),
        _metrics_doc({
            "schema_valid": {"value": 0.5},
            "pipeline_success": {"value": False},
            "element_count_total": {"value": 3},
            "silent_drop_count": {"value": 2},
            "pdf_locator_valid_ratio": {"value": 1.0},
            "chunk_reference_intact_ratio": {"value": 0.5},
        }),
    ]
    s = aggregate_summary(docs)
    assert s["counts"]["element_count_total"]["sum"] == 8
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert s["silent_drop_total"] == 3


def test_e2e_dependency_versions_idempotent_batch14():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2
    assert out1 is not out2


def test_e2e_full_report_assembly_batch14():
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")
    fake_clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok, fake_clean]):
        prov = build_provenance(Path("."), parser_name="x", max_chars=100, parser_version=None)
    devset = build_devset_section(_StubManifestBatch14())
    summary = aggregate_summary([])
    report = {
        "report_version": REPORT_VERSION,
        "provenance": prov,
        "devset": devset,
        "summary": summary,
    }
    parsed = json.loads(json.dumps(report))
    assert parsed == report
