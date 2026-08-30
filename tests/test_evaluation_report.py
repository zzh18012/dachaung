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
        "figure_caption_precision": {"value": None, "reason": "no_annotation"},
        "figure_caption_recall": {"value": None, "reason": "no_annotation"},
        "figure_caption_f1": {"value": None, "reason": "no_annotation"},
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
    # 应当只有这 5 个 key
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total", "expectation_checks"}
    # 不存在 overall / total_score / aggregate_score 之类的字段
    for v in s.values():
        if isinstance(v, dict):
            for k in v:
                assert "overall" not in k.lower()
                assert "total_score" not in k.lower()
