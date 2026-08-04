"""report.py 的测试：聚合规则、provenance、devset 元数据。"""

from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
)


def _make_per_doc(metric_overrides: dict | None = None) -> dict:
    metrics = {
        "pipeline_success": {"value": True, "reason": None},
        "schema_valid": {"value": True, "reason": None},
        "element_count_total": {"value": 5, "reason": None},
        "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
        "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
        "image_resource_exists_ratio": {"value": 1.0, "reason": None},
        "chunk_reference_intact_ratio": {"value": 1.0, "reason": None},
        "text_preservation_equal": {"value": True, "reason": None},
        "text_char_multiset_precision": {"value": 1.0, "reason": None},
        "text_char_multiset_recall": {"value": 1.0, "reason": None},
        "heading_boundary_compliance": {"value": 1.0, "reason": None},
        "silent_drop_count": {"value": 0, "reason": None},
        "figure_caption_precision": {"value": None, "reason": "parser_does_not_emit_relations"},
        "figure_caption_recall": {"value": None, "reason": "parser_does_not_emit_relations"},
        "figure_caption_f1": {"value": None, "reason": "parser_does_not_emit_relations"},
        "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
        "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
        "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
    }
    if metric_overrides:
        metrics.update(metric_overrides)
    return {
        "doc_id": "x",
        "source_type": "pdf",
        "metrics": metrics,
        "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None,
                              "parse_reason": "not_instrumented",
                              "chunk_reason": "not_instrumented"},
    }


def test_aggregate_counts_summed():
    per_doc = [_make_per_doc(), _make_per_doc({"element_count_total": {"value": 3, "reason": None}})]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 8
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_success_rate():
    per_doc = [
        _make_per_doc(),
        _make_per_doc({"pipeline_success": {"value": False, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_ratio_macro_average_excludes_null():
    per_doc = [
        _make_per_doc(),
        _make_per_doc({"pdf_locator_valid_ratio": {"value": None, "reason": "x"}}),
    ]
    s = aggregate_summary(per_doc)
    ratio = s["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ratio["macro_average"] == 1.0  # 只有 1 个非 null 参与
    assert ratio["participating_docs"] == 1
    assert ratio["not_evaluated"] == 1


def test_aggregate_silent_drop_summed():
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": 1, "reason": None}}),
        _make_per_doc({"silent_drop_count": {"value": 2, "reason": None}}),
        _make_per_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 3


def test_aggregate_silent_drop_all_null():
    per_doc = [_make_per_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}})]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] is None


def test_build_devset_section_categories_sorted():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 2
        content_group_count = 1
        pdf_count = 1
        docx_count = 1
        categories_covered = ["image", "report", "table"]

    d = build_devset_section(FakeManifest())
    assert d["status"] == "incomplete"
    assert d["file_count"] == 2
    assert d["categories_covered"] == ["image", "report", "table"]


def test_build_provenance_structure(tmp_path: Path):
    # 在临时项目根创建 git 仓库
    import subprocess
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    prov = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="test=1.0")
    assert prov["git_commit"] is not None
    assert prov["git_dirty"] is False  # 已提交，无未跟踪
    assert prov["parser_name"] == "fallback"
    assert prov["parser_version"] == "test=1.0"
    assert prov["max_chars"] == 800
    assert "run_timestamp_iso" in prov
    assert "pdfplumber" in prov["dependencies"]


def test_build_provenance_dirty_flag(tmp_path: Path):
    import subprocess
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    # 加一个未跟踪文件 → dirty
    (tmp_path / "uncommitted.txt").write_text("x", encoding="utf-8")
    prov = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version=None)
    assert prov["git_dirty"] is True


def test_no_mixed_overall_score():
    """聚合 summary 不应包含一个混合所有指标的'综合分数'。"""
    per_doc = [_make_per_doc()]
    s = aggregate_summary(per_doc)
    # 应当只有这 4 个 key
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    # 不存在 overall / total_score / aggregate_score 之类的字段
    for v in s.values():
        if isinstance(v, dict):
            for k in v:
                assert "overall" not in k.lower()
                assert "total_score" not in k.lower()


# ---------- 边角与缺漏补强（Round 26） ----------


def test_aggregate_empty_per_doc_results():
    """空 per_doc list 不应崩溃。"""
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0
    # success_rates：total=0 → rate=None
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None
    # silent_drop_total：no values → None
    assert s["silent_drop_total"] is None


def test_aggregate_counts_all_none_returns_none_sum():
    """所有 doc 的 element_count_total 都是 None → sum=None, participating=0。"""
    per_doc = [
        _make_per_doc({"element_count_total": {"value": None, "reason": "pipeline_failed"}}),
        _make_per_doc({"element_count_total": {"value": None, "reason": "pipeline_failed"}}),
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_ratio_macro_average_with_multiple_values():
    """两个 doc 都给非 null ratio → macro 是算术平均。"""
    per_doc = [
        _make_per_doc({"pdf_locator_valid_ratio": {"value": 0.5, "reason": None}}),
        _make_per_doc({"pdf_locator_valid_ratio": {"value": 1.0, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    ratio = s["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ratio["macro_average"] == 0.75
    assert ratio["participating_docs"] == 2
    assert ratio["not_evaluated"] == 0


def test_aggregate_ratio_macro_average_all_null():
    """所有 doc 都给 None → macro=None, participating=0, not_evaluated=N。"""
    per_doc = [
        _make_per_doc({"pdf_locator_valid_ratio": {"value": None, "reason": "x"}}),
        _make_per_doc({"pdf_locator_valid_ratio": {"value": None, "reason": "y"}}),
    ]
    s = aggregate_summary(per_doc)
    ratio = s["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ratio["macro_average"] is None
    assert ratio["participating_docs"] == 0
    assert ratio["not_evaluated"] == 2


def test_aggregate_schema_valid_in_ratio_metrics():
    """schema_valid 同时在 success_rates（_SUCCESS_BOOL_METRICS 没有）
    和 ratio_macro_averages（在 _RATIO_METRICS 里）。
    它是 bool，但 macro_average 把 True 当 1.0 / False 当 0.0。"""
    per_doc = [
        _make_per_doc({"schema_valid": {"value": True, "reason": None}}),
        _make_per_doc({"schema_valid": {"value": False, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    # ratio 视角：True=1.0, False=0.0 → macro = 0.5
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5


def test_aggregate_figure_caption_excluded_from_ratio_averages():
    """figure_caption_* 不在 _RATIO_METRICS 中 → 不应出现在 ratio_macro_averages。"""
    per_doc = [_make_per_doc()]
    s = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in s["ratio_macro_averages"]
    assert "figure_caption_recall" not in s["ratio_macro_averages"]
    assert "figure_caption_f1" not in s["ratio_macro_averages"]


def test_aggregate_chunk_boundary_in_ratio_metrics():
    """chunk_boundary_* 在 _RATIO_METRICS 中。"""
    per_doc = [
        _make_per_doc({"chunk_boundary_precision": {"value": 0.5, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    assert "chunk_boundary_precision" in s["ratio_macro_averages"]
    assert s["ratio_macro_averages"]["chunk_boundary_precision"]["macro_average"] == 0.5


def test_aggregate_text_preservation_equal_treated_as_ratio():
    """text_preservation_equal 是 bool 但在 ratio 列表里：True=1.0 / False=0.0。"""
    per_doc = [
        _make_per_doc({"text_preservation_equal": {"value": True, "reason": None}}),
        _make_per_doc({"text_preservation_equal": {"value": False, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    # (True + False) / 2 → Python: (1 + 0) / 2 = 0.5
    macro = s["ratio_macro_averages"]["text_preservation_equal"]["macro_average"]
    assert macro == 0.5


def test_aggregate_success_rate_all_fail():
    per_doc = [
        _make_per_doc({"pipeline_success": {"value": False, "reason": None}}),
        _make_per_doc({"pipeline_success": {"value": False, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 2
    assert sr["rate"] == 0.0


def test_aggregate_success_rate_all_pass():
    per_doc = [_make_per_doc(), _make_per_doc()]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_silent_drop_mixed():
    """silent_drop_count 求和：null 不参与。"""
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": 0, "reason": None}}),
        _make_per_doc({"silent_drop_count": {"value": 5, "reason": None}}),
        _make_per_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
        _make_per_doc({"silent_drop_count": {"value": 3, "reason": None}}),
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_get_dependency_versions_returns_dict_with_known_packages():
    from evaluation.report import get_dependency_versions
    versions = get_dependency_versions()
    assert isinstance(versions, dict)
    # 三个包名都应在结果里（值可能是 None，如果未安装）
    assert "pdfplumber" in versions
    assert "python-docx" in versions
    assert "pypdfium2" in versions


def test_get_dependency_versions_values_are_str_or_none():
    from evaluation.report import get_dependency_versions
    versions = get_dependency_versions()
    for pkg, ver in versions.items():
        assert ver is None or isinstance(ver, str)


def test_get_git_provenance_non_git_dir_returns_none_commit(tmp_path: Path):
    """非 git 仓库 → commit=None（dirty 行为依赖 git 子进程，不强断）。"""
    from evaluation.report import get_git_provenance
    # tmp_path 不是 git 仓库
    prov = get_git_provenance(tmp_path)
    assert prov["git_commit"] is None
    # git_dirty 是 bool（具体值依赖环境：子进程失败时 True，正常返回非 0 时 False）
    assert isinstance(prov["git_dirty"], bool)


def test_build_provenance_int_converts_max_chars(tmp_path: Path):
    """max_chars 应被强制转成 int。"""
    import subprocess
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", " -m", "init"], cwd=str(tmp_path), capture_output=True)
    prov = build_provenance(tmp_path, parser_name="x", max_chars=800, parser_version=None)
    assert prov["max_chars"] == 800
    assert isinstance(prov["max_chars"], int)


def test_build_provenance_parser_version_none_handled(tmp_path: Path):
    """parser_version=None 应在结果里也是 None。"""
    import subprocess
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    prov = build_provenance(tmp_path, parser_name="x", max_chars=800, parser_version=None)
    assert prov["parser_version"] is None


def test_build_provenance_includes_evaluator_and_report_versions(tmp_path: Path):
    """provenance 包含 EVALUATOR_VERSION 与 REPORT_VERSION 常量。"""
    from evaluation import EVALUATOR_VERSION, REPORT_VERSION
    import subprocess
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    prov = build_provenance(tmp_path, parser_name="x", max_chars=800, parser_version=None)
    assert prov["evaluator_version"] == EVALUATOR_VERSION
    assert prov["report_version"] == REPORT_VERSION


def test_build_devset_section_all_fields_populated():
    from evaluation.report import build_devset_section

    class FakeManifest:
        devset_status = "complete"
        file_count = 10
        content_group_count = 5
        pdf_count = 4
        docx_count = 6
        categories_covered = ["a", "b", "c"]

    d = build_devset_section(FakeManifest())
    assert d == {
        "status": "complete",
        "file_count": 10,
        "content_group_count": 5,
        "pdf_count": 4,
        "docx_count": 6,
        "categories_covered": ["a", "b", "c"],
    }


def test_aggregate_ratio_macro_average_only_one_doc_participates_out_of_three():
    """3 个 doc，只有 1 个有非 null 值 → participating=1, not_evaluated=2。"""
    per_doc = [
        _make_per_doc({"image_resource_exists_ratio": {"value": 0.7, "reason": None}}),
        _make_per_doc({"image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"}}),
        _make_per_doc({"image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"}}),
    ]
    s = aggregate_summary(per_doc)
    ratio = s["ratio_macro_averages"]["image_resource_exists_ratio"]
    assert ratio["macro_average"] == 0.7
    assert ratio["participating_docs"] == 1
    assert ratio["not_evaluated"] == 2


def test_aggregate_does_not_mutate_input():
    """aggregate_summary 不应修改输入的 per_doc_results。"""
    per_doc = [_make_per_doc()]
    import copy
    snapshot = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snapshot


# ---------- 边角补强（Round 45） ----------


# 常量直接单测


def test_count_metrics_constant_value():
    from evaluation.report import _COUNT_METRICS
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_constant_value():
    from evaluation.report import _SUCCESS_BOOL_METRICS
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_constant_includes_known_metrics():
    from evaluation.report import _RATIO_METRICS
    expected = {
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    }
    assert set(_RATIO_METRICS) == expected


def test_ratio_metrics_constant_excludes_figure_caption():
    """figure_caption_* 始终 null，不参与 macro average。"""
    from evaluation.report import _RATIO_METRICS
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_constant_excludes_count_and_silent_drop():
    from evaluation.report import _RATIO_METRICS
    assert "element_count_total" not in _RATIO_METRICS
    assert "silent_drop_count" not in _RATIO_METRICS


# get_dependency_versions shape


def test_get_dependency_versions_returns_dict():
    from evaluation.report import get_dependency_versions
    deps = get_dependency_versions()
    assert isinstance(deps, dict)


def test_get_dependency_versions_has_three_known_packages():
    from evaluation.report import get_dependency_versions
    deps = get_dependency_versions()
    for pkg in ("pdfplumber", "python-docx", "pypdfium2"):
        assert pkg in deps


def test_get_dependency_versions_values_type():
    """值是 str（已安装）或 None（未安装）。"""
    from evaluation.report import get_dependency_versions
    deps = get_dependency_versions()
    for v in deps.values():
        assert v is None or isinstance(v, str)


# get_git_provenance shape


def test_get_git_provenance_returns_dict_with_two_keys(tmp_path: Path):
    from evaluation.report import get_git_provenance
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_real_repo_returns_commit():
    """在当前项目根（git 仓库）跑一次，commit 应是非空字符串。"""
    from evaluation.report import get_git_provenance
    project_root = Path(__file__).resolve().parent.parent
    out = get_git_provenance(project_root)
    # 在 git 仓库内 → commit 非空，dirty 是 bool
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_subprocess_failure_safe():
    """传一个不存在的路径 → subprocess 失败 → commit=None, dirty=True。"""
    from evaluation.report import get_git_provenance
    out = get_git_provenance(Path("Z:/nonexistent_path_xyz"))
    # 不抛异常即合格
    assert "git_commit" in out
    assert "git_dirty" in out


# build_provenance 字段完整性


def test_build_provenance_has_nine_top_level_keys(tmp_path: Path):
    """provenance 应含 9 个字段。"""
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version="v1",
    )
    expected_keys = {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(out.keys()) == expected_keys


def test_build_provenance_max_chars_int_type(tmp_path: Path):
    """max_chars 应被 int() 转换（即便传 float）。"""
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800.0,  # float
        parser_version=None,
    )
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_name_passthrough(tmp_path: Path):
    out = build_provenance(
        project_root=tmp_path,
        parser_name="custom_parser",
        max_chars=800,
        parser_version=None,
    )
    assert out["parser_name"] == "custom_parser"


def test_build_provenance_parser_version_passthrough(tmp_path: Path):
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version="custom=1.2.3",
    )
    assert out["parser_version"] == "custom=1.2.3"


def test_build_provenance_run_timestamp_iso_format(tmp_path: Path):
    """run_timestamp_iso 应是 ISO 8601（含 T 与 timezone）。"""
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version=None,
    )
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    assert "T" in ts
    # 应含时区偏移（+HH:MM 或 Z）
    assert "+" in ts or "-" in ts[-6:] or ts.endswith("Z")


def test_build_provenance_evaluator_version_matches_constant(tmp_path: Path):
    """evaluator_version 来自 EVALUATOR_VERSION（指示线 v1.1，**不要改**）。"""
    from evaluation import EVALUATOR_VERSION
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version=None,
    )
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_matches_constant(tmp_path: Path):
    from evaluation import REPORT_VERSION
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version=None,
    )
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_subfield(tmp_path: Path):
    """provenance.dependencies 是 dict（含 pdfplumber/python-docx/pypdfium2）。"""
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version=None,
    )
    deps = out["dependencies"]
    assert isinstance(deps, dict)
    assert "pdfplumber" in deps
    assert "python-docx" in deps
    assert "pypdfium2" in deps


# build_devset_section 字段完整性


def test_build_devset_section_six_keys():
    from evaluation.report import build_devset_section

    class FakeManifest:
        devset_status = "incomplete"
        file_count = 5
        content_group_count = 3
        pdf_count = 2
        docx_count = 3
        categories_covered = ["report", "table"]

    out = build_devset_section(FakeManifest())
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(out.keys()) == expected


def test_build_devset_section_passes_through_all_values():
    from evaluation.report import build_devset_section

    class FakeManifest:
        devset_status = "complete"
        file_count = 100
        content_group_count = 50
        pdf_count = 30
        docx_count = 70
        categories_covered = ["a", "b", "c"]

    out = build_devset_section(FakeManifest())
    assert out["status"] == "complete"
    assert out["file_count"] == 100
    assert out["content_group_count"] == 50
    assert out["pdf_count"] == 30
    assert out["docx_count"] == 70
    assert out["categories_covered"] == ["a", "b", "c"]


# aggregate_summary shape


def test_aggregate_summary_has_four_top_level_keys():
    summary = aggregate_summary([])
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert set(summary.keys()) == expected


def test_aggregate_summary_counts_section_includes_element_count_total():
    summary = aggregate_summary([])
    assert "element_count_total" in summary["counts"]


def test_aggregate_summary_success_rates_includes_pipeline_success():
    summary = aggregate_summary([])
    assert "pipeline_success" in summary["success_rates"]


def test_aggregate_summary_ratio_macro_averages_includes_all_ratio_metrics():
    """ratio_macro_averages 应含 _RATIO_METRICS 全部 12 个 key。"""
    from evaluation.report import _RATIO_METRICS
    summary = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert name in summary["ratio_macro_averages"]


def test_aggregate_summary_counts_sum_field_is_int_or_none():
    summary = aggregate_summary([_make_per_doc()])
    assert summary["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_summary_counts_participating_docs_field():
    summary = aggregate_summary([_make_per_doc(), _make_per_doc()])
    assert summary["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_rate_value():
    summary = aggregate_summary([_make_per_doc(), _make_per_doc()])
    rate = summary["success_rates"]["pipeline_success"]["rate"]
    assert rate == 1.0


def test_aggregate_summary_success_rate_total_field():
    summary = aggregate_summary([_make_per_doc()])
    assert summary["success_rates"]["pipeline_success"]["total"] == 1


def test_aggregate_summary_success_rate_success_count_field():
    summary = aggregate_summary([_make_per_doc(), _make_per_doc()])
    assert summary["success_rates"]["pipeline_success"]["success_count"] == 2


def test_aggregate_summary_ratio_macro_average_value():
    """单文档：macro_average = 该文档值。"""
    summary = aggregate_summary([_make_per_doc()])
    avg = summary["ratio_macro_averages"]["schema_valid"]["macro_average"]
    assert avg == 1.0


def test_aggregate_summary_ratio_participating_docs_field():
    summary = aggregate_summary([_make_per_doc(), _make_per_doc()])
    info = summary["ratio_macro_averages"]["schema_valid"]
    assert info["participating_docs"] == 2


def test_aggregate_summary_ratio_not_evaluated_field():
    summary = aggregate_summary([_make_per_doc(), _make_per_doc()])
    info = summary["ratio_macro_averages"]["schema_valid"]
    assert info["not_evaluated"] == 0


def test_aggregate_summary_silent_drop_total_zero_when_all_zero():
    summary = aggregate_summary([_make_per_doc(), _make_per_doc()])
    assert summary["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_total_sums():
    pd1 = _make_per_doc({"silent_drop_count": {"value": 3, "reason": None}})
    pd2 = _make_per_doc({"silent_drop_count": {"value": 5, "reason": None}})
    summary = aggregate_summary([pd1, pd2])
    assert summary["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_total_excludes_null():
    pd1 = _make_per_doc({"silent_drop_count": {"value": 3, "reason": None}})
    pd2 = _make_per_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}})
    summary = aggregate_summary([pd1, pd2])
    assert summary["silent_drop_total"] == 3


def test_aggregate_summary_empty_list_success_rate_rate_is_none():
    """空 per_doc → rate 是 None（分母为 0）。"""
    summary = aggregate_summary([])
    assert summary["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_empty_list_success_rate_total_zero():
    summary = aggregate_summary([])
    assert summary["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_empty_list_success_rate_success_count_zero():
    summary = aggregate_summary([])
    assert summary["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_empty_list_counts_participating_docs_zero():
    summary = aggregate_summary([])
    assert summary["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_list_silent_drop_total_none():
    summary = aggregate_summary([])
    assert summary["silent_drop_total"] is None
