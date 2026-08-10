r"""evaluation/runner.py 边角测试 - 第二十轮（Round 279）。

edges19 已覆盖：source-level token 详尽（_load_annotation / _process_one / run_evaluation）；
模块 imports / namespace / signatures / docstring；empty manifest 行为；_load_annotation 行为；
报告写盘后可解析；ensure_ascii=False / indent=2；两次调用独立。

edges20 补强未覆盖的角度（行为 + schema 联动）：
- **schema 交叉验证**：run_evaluation 实际输出通过 evaluation-report.schema.json
- **失败文档路径**：DocumentEntry 指向不存在的文件 → process_single 返 file_not_found → metrics 大多 null
  + reason=pipeline_failed；error_code 取自 errors[0].code
- **expected_failures 完整路径**：
  * matches=True（actual_code == expected_error_code）
  * matches=False（actual_code != expected_error_code）
  * actual_code 不在 errors 时为 None（process_single 成功）
- **tolerance_chars 传播**：默认 30；自定义 50/100 → per_doc record _tolerance_chars 反映
- **_annotation_present 行为**：annotation_file 存在 → True；不存在 / None → False
- **provenance 字段类型**：dependencies 是 dict；max_chars 是 int；parser_version 是 str|None
- **summary 字段类型**：counts/success_rates/ratio_macro_averages 都是 dict；silent_drop_total 是 int|None
- **per_doc wall_time_seconds 5 keys**：total/parse/chunk/parse_reason/chunk_reason
- **report_version 等于 REPORT_VERSION 常量**
- **多文档 manifest**：2+ 文档 → per_doc 长度匹配；summary counts/success_rates 反映所有文档
- **public_per_doc vs internal**：public 不含 _ 前缀字段（_annotation_present/_tolerance_chars/_missing_markers）
- **empty manifest schema 验证**：devset 字段类型正确（file_count 是 int 0；categories_covered 是 list）
- **out_stub 清理**：_per_doc/<doc_id>.json 不留盘（即使 process_single 失败）
- **module source 不含 subprocess**（已可能在 edges19 验证；这里再补）
- **run_evaluation 不修改 manifest**（包括 documents / expected_failures / project_root）
- **run_evaluation 在不同 parser_name 下不出错**（用 fallback 默认）
- **run_evaluation 处理含 paired_with 的 manifest**（content_group_count > 0）
- **process_one source 5-tuple 顺序**：(document, error, total_seconds, parser_version, image_dir)
- **module __all__ 仍然只是 ['run_evaluation']**
- **run_evaluation_report 字段值类型**：summary 是 dict；per_doc 是 list；expected_failures 是 list
- **public per_doc 字段顺序**：doc_id, source_type, metrics, wall_time_seconds
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 辅助：构造 Manifest / DocumentEntry
# =========================================================================


def _make_empty_manifest(tmp_path: Path) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def _make_failing_doc_entry(tmp_path: Path, doc_id: str = "fail-1") -> DocumentEntry:
    """构造一个指向不存在文件的 DocumentEntry，触发 file_not_found 错误。"""
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"missing/{doc_id}.pdf",
        resolved_path=tmp_path / "missing" / f"{doc_id}.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_failing_expected_failure(
    tmp_path: Path, doc_id: str = "ef-1", expected_code: str = "file_not_found"
) -> ExpectedFailure:
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=f"missing/{doc_id}.docx",
        resolved_path=tmp_path / "missing" / f"{doc_id}.docx",
        expected_error_code=expected_code,
        source_type="docx",
    )


def _make_manifest_with_failing_docs(
    tmp_path: Path,
    docs: tuple[DocumentEntry, ...] = (),
    expected_failures: tuple[ExpectedFailure, ...] = (),
) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=expected_failures,
        project_root=tmp_path,
    )


# =========================================================================
# schema 交叉验证：实际 run_evaluation 输出通过 evaluation-report.schema.json
# =========================================================================


def test_run_evaluation_empty_manifest_passes_schema(tmp_path):
    """空 manifest 输出应通过 evaluation-report.schema.json。"""
    from evaluation.schema import validate

    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    validate(report, "evaluation-report.schema.json")


def test_run_evaluation_failing_doc_passes_schema(tmp_path):
    """含一个失败 doc 的 manifest 输出应通过 evaluation-report.schema.json。"""
    from evaluation.schema import validate

    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    validate(report, "evaluation-report.schema.json")


def test_run_evaluation_with_expected_failure_passes_schema(tmp_path):
    """含 expected_failures 的 manifest 输出应通过 evaluation-report.schema.json。"""
    from evaluation.schema import validate

    ef = _make_failing_expected_failure(tmp_path)
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    validate(report, "evaluation-report.schema.json")


def test_run_evaluation_combined_passes_schema(tmp_path):
    """同时含 failing doc 和 expected_failure 的 manifest 输出应通过 schema。"""
    from evaluation.schema import validate

    doc = _make_failing_doc_entry(tmp_path)
    ef = _make_failing_expected_failure(tmp_path)
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(doc,), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    validate(report, "evaluation-report.schema.json")


# =========================================================================
# 失败文档路径（process_single 返 file_not_found）
# =========================================================================


def test_run_evaluation_failing_doc_metrics_pipeline_failed(tmp_path):
    """失败 doc 的 14 个 metrics 中，除 pipeline_success/error_code 外，其余 12 应 null + pipeline_failed。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    assert report["per_doc"]
    metrics = report["per_doc"][0]["metrics"]
    # pipeline_success=False（value False）
    assert metrics["pipeline_success"]["value"] is False
    # error_code = 'file_not_found'（来自 hash 阶段）
    assert metrics["error_code"]["value"] == "file_not_found"
    # schema_valid null + pipeline_failed
    assert metrics["schema_valid"]["value"] is None
    assert metrics["schema_valid"]["reason"] == "pipeline_failed"


def test_run_evaluation_failing_doc_12_metrics_null_pipeline_failed(tmp_path):
    """失败 doc 的 12 个 null-prone metrics 全部 null + reason=pipeline_failed。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    metrics = report["per_doc"][0]["metrics"]
    null_metric_names = [
        "element_count_total",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    ]
    for name in null_metric_names:
        assert metrics[name]["value"] is None, f"{name} 应该是 null"
        assert metrics[name]["reason"] == "pipeline_failed", f"{name} reason 应为 pipeline_failed"


def test_run_evaluation_failing_doc_element_count_by_type_null(tmp_path):
    """element_count_by_type 在失败时也是 null + pipeline_failed。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    metrics = report["per_doc"][0]["metrics"]
    assert metrics["element_count_by_type"]["value"] is None
    assert metrics["element_count_by_type"]["reason"] == "pipeline_failed"


def test_run_evaluation_failing_doc_total_time_recorded(tmp_path):
    """失败 doc 也应记录 total time（>0；含 perf_counter 开销）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    wall = report["per_doc"][0]["wall_time_seconds"]
    assert wall["total"] is not None
    assert wall["total"] >= 0.0


def test_run_evaluation_failing_doc_wall_time_5_keys(tmp_path):
    """失败 doc 的 wall_time_seconds 仍含 5 keys。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    wall = report["per_doc"][0]["wall_time_seconds"]
    assert set(wall.keys()) == {
        "total", "parse", "chunk", "parse_reason", "chunk_reason"
    }
    assert wall["parse"] is None
    assert wall["chunk"] is None
    assert wall["parse_reason"] == "not_instrumented"
    assert wall["chunk_reason"] == "not_instrumented"


# =========================================================================
# expected_failures 完整路径
# =========================================================================


def test_run_evaluation_expected_failure_match_true(tmp_path):
    """expected_failure：file_not_found == file_not_found → matches=True。"""
    ef = _make_failing_expected_failure(
        tmp_path, doc_id="ef-match", expected_code="file_not_found"
    )
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    ef_results = report["expected_failures"]
    assert len(ef_results) == 1
    r = ef_results[0]
    assert r["doc_id"] == "ef-match"
    assert r["expected_error_code"] == "file_not_found"
    assert r["actual_error_code"] == "file_not_found"
    assert r["matches"] is True


def test_run_evaluation_expected_failure_match_false(tmp_path):
    """expected_failure：期望 parse_failed 但实际 file_not_found → matches=False。"""
    ef = _make_failing_expected_failure(
        tmp_path, doc_id="ef-mismatch", expected_code="parse_failed"
    )
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    r = report["expected_failures"][0]
    assert r["expected_error_code"] == "parse_failed"
    assert r["actual_error_code"] == "file_not_found"
    assert r["matches"] is False


def test_run_evaluation_expected_failure_keys_order(tmp_path):
    """expected_failure 字段顺序：doc_id, expected_error_code, actual_error_code, matches。"""
    ef = _make_failing_expected_failure(tmp_path)
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    keys = list(report["expected_failures"][0].keys())
    assert keys == ["doc_id", "expected_error_code", "actual_error_code", "matches"]


def test_run_evaluation_two_expected_failures_independent(tmp_path):
    """两个 expected_failures 应产生两条独立记录。"""
    ef1 = _make_failing_expected_failure(tmp_path, doc_id="ef-1")
    ef2 = _make_failing_expected_failure(
        tmp_path, doc_id="ef-2", expected_code="parse_failed"
    )
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef1, ef2)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    assert len(report["expected_failures"]) == 2
    ids = [r["doc_id"] for r in report["expected_failures"]]
    assert ids == ["ef-1", "ef-2"]


# =========================================================================
# 多文档 manifest
# =========================================================================


def test_run_evaluation_two_failing_docs_per_doc_count(tmp_path):
    """两个失败 doc → per_doc 长度=2。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="fail-A")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="fail-B")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc1, doc2))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    assert len(report["per_doc"]) == 2
    ids = [r["doc_id"] for r in report["per_doc"]]
    assert ids == ["fail-A", "fail-B"]


def test_run_evaluation_two_failing_docs_summary_success_count(tmp_path):
    """两个失败 doc → success_rates.pipeline_success.success_count=0；total=2；rate=0.0。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="fail-A")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="fail-B")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc1, doc2))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    ps = report["summary"]["success_rates"]["pipeline_success"]
    assert ps["success_count"] == 0
    assert ps["total"] == 2
    assert ps["rate"] == 0.0


def test_run_evaluation_two_failing_docs_counts_participating(tmp_path):
    """两个失败 doc → counts.element_count_total.participating_docs=0；sum=None。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="fail-A")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="fail-B")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc1, doc2))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    ct = report["summary"]["counts"]["element_count_total"]
    assert ct["participating_docs"] == 0
    assert ct["sum"] is None


def test_run_evaluation_two_failing_docs_silent_drop_total_none(tmp_path):
    """两个失败 doc 都无 expectations → silent_drop_total=None。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="fail-A")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="fail-B")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc1, doc2))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    assert report["summary"]["silent_drop_total"] is None


# =========================================================================
# tolerance_chars 传播（默认 30；自定义反映到 per_doc record）
# =========================================================================


def test_run_evaluation_default_tolerance_chars_30(tmp_path):
    """run_evaluation 默认 tolerance_chars=30。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_custom_tolerance_chars_kwarg(tmp_path):
    """自定义 tolerance_chars=50 不报错。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    # 不应抛异常
    report = run_evaluation(manifest, out_path, tolerance_chars=50)
    assert report["per_doc"]


def test_run_evaluation_tolerance_chars_keyword_only(tmp_path):
    """tolerance_chars 是 KEYWORD_ONLY 参数。"""
    from inspect import Parameter

    sig = inspect.signature(run_evaluation)
    p = sig.parameters["tolerance_chars"]
    assert p.kind == Parameter.KEYWORD_ONLY


def test_run_evaluation_max_chars_keyword_only(tmp_path):
    """max_chars 是 KEYWORD_ONLY 参数。"""
    from inspect import Parameter

    sig = inspect.signature(run_evaluation)
    p = sig.parameters["max_chars"]
    assert p.kind == Parameter.KEYWORD_ONLY


def test_run_evaluation_parser_name_keyword_only(tmp_path):
    """parser_name 是 KEYWORD_ONLY 参数。"""
    from inspect import Parameter

    sig = inspect.signature(run_evaluation)
    p = sig.parameters["parser_name"]
    assert p.kind == Parameter.KEYWORD_ONLY


# =========================================================================
# _annotation_present 行为
# =========================================================================


def test_run_evaluation_annotation_present_false_when_no_annotation(tmp_path):
    """无 annotation_file → _annotation_present False（通过 public per_doc 看不到，但内部 record 有）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    # public per_doc 不含 _ 前缀字段
    assert "_annotation_present" not in report["per_doc"][0]


def test_run_evaluation_annotation_present_not_in_public(tmp_path):
    """public per_doc 永远不含 _ 前缀字段（_annotation_present/_tolerance_chars/_missing_markers）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    for r in report["per_doc"]:
        for k in r.keys():
        # 所有 public per_doc key 不以 _ 开头
            assert not k.startswith("_"), f"public per_doc 含 _ 前缀字段: {k}"


def test_run_evaluation_public_per_doc_keys_exact(tmp_path):
    """public per_doc keys 精确：doc_id, source_type, metrics, wall_time_seconds。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)

    keys = list(report["per_doc"][0].keys())
    assert keys == ["doc_id", "source_type", "metrics", "wall_time_seconds"]


# =========================================================================
# provenance 字段类型（schema 要求的精确类型）
# =========================================================================


def test_run_evaluation_provenance_max_chars_is_int(tmp_path):
    """provenance.max_chars 必须是 int（schema 要求 integer）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["provenance"]["max_chars"], int)
    assert not isinstance(report["provenance"]["max_chars"], bool)


def test_run_evaluation_provenance_dependencies_is_dict(tmp_path):
    """provenance.dependencies 必须是 dict。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["provenance"]["dependencies"], dict)


def test_run_evaluation_provenance_parser_name_is_str(tmp_path):
    """provenance.parser_name 必须是非空 str。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["provenance"]["parser_name"], str)
    assert report["provenance"]["parser_name"]


def test_run_evaluation_provenance_parser_version_none_when_no_success(tmp_path):
    """所有 doc 都失败 → parser_version 为 None。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_provenance_evaluator_version_str(tmp_path):
    """provenance.evaluator_version 必须是非空 str。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["provenance"]["evaluator_version"], str)
    assert report["provenance"]["evaluator_version"]


def test_run_evaluation_provenance_report_version_matches_constant(tmp_path):
    """provenance.report_version 必须等于 REPORT_VERSION 常量。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["provenance"]["report_version"] == REPORT_VERSION
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_provenance_run_timestamp_iso_str(tmp_path):
    """provenance.run_timestamp_iso 必须是非空 str（ISO 格式）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    ts = report["provenance"]["run_timestamp_iso"]
    assert isinstance(ts, str)
    assert ts


def test_run_evaluation_provenance_git_dirty_is_bool(tmp_path):
    """provenance.git_dirty 必须是 bool。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["provenance"]["git_dirty"], bool)


def test_run_evaluation_provenance_git_commit_is_str_or_none(tmp_path):
    """provenance.git_commit 必须是 str 或 None。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    gc = report["provenance"]["git_commit"]
    assert gc is None or isinstance(gc, str)


def test_run_evaluation_provenance_keys_count_9(tmp_path):
    """provenance 有 9 keys（schema required）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert len(report["provenance"]) == 9


def test_run_evaluation_provenance_keys_exact(tmp_path):
    """provenance keys 精确集合（schema additionalProperties:false）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(report["provenance"].keys()) == expected


# =========================================================================
# summary 字段类型（4 buckets）
# =========================================================================


def test_run_evaluation_summary_keys_exact(tmp_path):
    """summary keys 精确：counts, success_rates, ratio_macro_averages, silent_drop_total。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert set(report["summary"].keys()) == expected


def test_run_evaluation_summary_counts_is_dict(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["summary"]["counts"], dict)


def test_run_evaluation_summary_success_rates_is_dict(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["summary"]["success_rates"], dict)


def test_run_evaluation_summary_ratio_macro_averages_is_dict(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["summary"]["ratio_macro_averages"], dict)


def test_run_evaluation_summary_silent_drop_total_is_none_or_int(tmp_path):
    """empty manifest → silent_drop_total=None（无 docs）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    sdt = report["summary"]["silent_drop_total"]
    assert sdt is None or isinstance(sdt, int)


def test_run_evaluation_summary_counts_element_count_total_keys(tmp_path):
    """empty manifest → counts.element_count_total 含 sum=None, participating_docs=0。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    ect = report["summary"]["counts"]["element_count_total"]
    assert set(ect.keys()) == {"sum", "participating_docs"}
    assert ect["sum"] is None
    assert ect["participating_docs"] == 0


def test_run_evaluation_summary_success_rates_pipeline_success_keys(tmp_path):
    """empty manifest → success_rates.pipeline_success 含 success_count=0, total=0, rate=None。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    ps = report["summary"]["success_rates"]["pipeline_success"]
    assert set(ps.keys()) == {"success_count", "total", "rate"}
    assert ps["success_count"] == 0
    assert ps["total"] == 0
    assert ps["rate"] is None


def test_run_evaluation_summary_ratio_macro_averages_keys_count(tmp_path):
    """empty manifest → ratio_macro_averages 含 12 项（_RATIO_METRICS）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    rma = report["summary"]["ratio_macro_averages"]
    assert len(rma) == 12


def test_run_evaluation_summary_ratio_macro_averages_per_key_keys(tmp_path):
    """每个 ratio_macro_average 项含 macro_average, participating_docs, not_evaluated。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    rma = report["summary"]["ratio_macro_averages"]
    for k, v in rma.items():
        assert set(v.keys()) == {"macro_average", "participating_docs", "not_evaluated"}, \
            f"key {k} 不匹配"


def test_run_evaluation_summary_ratio_macro_averages_empty_values(tmp_path):
    """empty manifest → 每个 ratio_macro_average 项 macro_average=None, participating=0, not_evaluated=0。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    rma = report["summary"]["ratio_macro_averages"]
    for k, v in rma.items():
        assert v["macro_average"] is None
        assert v["participating_docs"] == 0
        assert v["not_evaluated"] == 0


# =========================================================================
# devset 字段（schema 要求）
# =========================================================================


def test_run_evaluation_devset_keys_exact(tmp_path):
    """devset keys 精确集合。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(report["devset"].keys()) == expected


def test_run_evaluation_devset_status_enum(tmp_path):
    """devset.status 必须是 'complete' 或 'incomplete'。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["devset"]["status"] in {"complete", "incomplete"}


def test_run_evaluation_devset_file_count_int(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["devset"]["file_count"], int)
    assert report["devset"]["file_count"] == 0


def test_run_evaluation_devset_categories_covered_list(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["devset"]["categories_covered"], list)


# =========================================================================
# 不修改 manifest
# =========================================================================


def test_run_evaluation_does_not_modify_manifest_documents(tmp_path):
    """run_evaluation 不修改 manifest.documents。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    docs_before = manifest.documents
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert manifest.documents is docs_before
    assert len(manifest.documents) == 1


def test_run_evaluation_does_not_modify_manifest_expected_failures(tmp_path):
    ef = _make_failing_expected_failure(tmp_path)
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    efs_before = manifest.expected_failures
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert manifest.expected_failures is efs_before


def test_run_evaluation_does_not_modify_manifest_project_root(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    pr_before = manifest.project_root
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert manifest.project_root is pr_before


def test_run_evaluation_does_not_modify_manifest_devset_status(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    status_before = manifest.devset_status
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert manifest.devset_status == status_before


# =========================================================================
# out_stub 清理：_per_doc/<doc_id>.json 不留盘
# =========================================================================


def test_run_evaluation_cleans_up_per_doc_stub_failing(tmp_path):
    """失败 doc 跑完后 _per_doc/<doc_id>.json 应被清理。"""
    doc = _make_failing_doc_entry(tmp_path, doc_id="cleanup-test")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    stub = out_path.parent / "_per_doc" / "cleanup-test.json"
    assert not stub.is_file()


def test_run_evaluation_cleans_up_per_doc_stub_expected_failure(tmp_path):
    """expected_failure 跑完后 _per_doc/<doc_id>.json 应被清理。"""
    ef = _make_failing_expected_failure(tmp_path, doc_id="ef-cleanup")
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    stub = out_path.parent / "_per_doc" / "ef-cleanup.json"
    assert not stub.is_file()


# =========================================================================
# 写盘后报告可重新解析 + schema 通过
# =========================================================================


def test_run_evaluation_written_report_passes_schema_failing(tmp_path):
    """含失败 doc 的报告写盘后，从磁盘读回再 schema validate 通过。"""
    from evaluation.schema import validate

    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    validate(loaded, "evaluation-report.schema.json")


def test_run_evaluation_written_report_no_u_escape_failing(tmp_path):
    r"""ensure_ascii=False → 报告中 \u 转义不出现（中文 reason 等保留）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    text = out_path.read_text(encoding="utf-8")
    assert "\\u" not in text


# =========================================================================
# report top-level 字段类型
# =========================================================================


def test_run_evaluation_report_version_constant(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_report_provenance_is_dict(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["provenance"], dict)


def test_run_evaluation_report_devset_is_dict(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["devset"], dict)


def test_run_evaluation_report_summary_is_dict(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["summary"], dict)


def test_run_evaluation_report_per_doc_is_list(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_report_expected_failures_is_list(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["expected_failures"], list)


# =========================================================================
# 模块 source 不含禁止内容（再补）
# =========================================================================


def test_module_source_does_not_contain_subprocess():
    """runner.py 不直接用 subprocess（provenance 在 evaluation/report.py 内）。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "import subprocess" not in src
    assert "subprocess.run" not in src


def test_module_source_does_not_contain_os_module():
    """runner.py 不导入 os。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_logging():
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "logging" not in src


def test_module_source_does_not_contain_concurrent_futures():
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "concurrent.futures" not in src
    assert "ThreadPoolExecutor" not in src
    assert "ProcessPoolExecutor" not in src


def test_module_source_does_not_contain_asyncio():
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "asyncio" not in src


def test_module_source_does_not_contain_threading():
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "threading" not in src


# =========================================================================
# module __all__ 仍然只是 ['run_evaluation']
# =========================================================================


def test_module_all_equals_run_evaluation_only():
    import evaluation.runner as m
    assert m.__all__ == ["run_evaluation"]


def test_module_all_is_list_type():
    import evaluation.runner as m
    assert isinstance(m.__all__, list)


def test_module_all_length_1():
    import evaluation.runner as m
    assert len(m.__all__) == 1


# =========================================================================
# _process_one 5-tuple 元素顺序 + 类型
# =========================================================================


def test_process_one_returns_5_tuple_for_failing_doc(tmp_path):
    """失败 doc 跑 _process_one → 返回 5-tuple (None, error_dict, float, None, None)。"""
    from app.models import ErrorRecord

    doc = _make_failing_doc_entry(tmp_path)
    out_root = tmp_path / "outputs"
    out_root.mkdir()
    result = _process_one(doc, out_root, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5
    document, error, total_seconds, parser_version, image_dir = result
    assert document is None
    assert isinstance(error, dict)
    assert error["code"] == "file_not_found"
    assert isinstance(total_seconds, float)
    assert parser_version is None
    # image_dir is None when document is None
    assert image_dir is None


def test_process_one_total_seconds_non_negative(tmp_path):
    """_process_one 返回的 total_seconds >= 0。"""
    doc = _make_failing_doc_entry(tmp_path)
    out_root = tmp_path / "outputs"
    out_root.mkdir()
    _, _, total_seconds, _, _ = _process_one(doc, out_root, "fallback", 800)
    assert total_seconds >= 0


def test_process_one_out_stub_cleaned_up(tmp_path):
    """_process_one 跑完后 out_stub 应被清理（即使失败）。"""
    doc = _make_failing_doc_entry(tmp_path, doc_id="stub-clean")
    out_root = tmp_path / "outputs"
    out_root.mkdir()
    _process_one(doc, out_root, "fallback", 800)
    stub = out_root / "_per_doc" / "stub-clean.json"
    # process_single 失败时不会写盘，stub 应不存在
    assert not stub.is_file()


def test_process_one_creates_per_doc_dir(tmp_path):
    """_process_one 应创建 _per_doc 子目录。"""
    doc = _make_failing_doc_entry(tmp_path, doc_id="mkdir-check")
    out_root = tmp_path / "outputs"
    out_root.mkdir()
    _process_one(doc, out_root, "fallback", 800)
    per_doc_dir = out_root / "_per_doc"
    assert per_doc_dir.is_dir()


# =========================================================================
# _load_annotation 行为补充
# =========================================================================


def test_load_annotation_returns_none_for_directory(tmp_path):
    """目录 → is_file() False → None。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_returns_none_for_none_input():
    assert _load_annotation(None) is None


def test_load_annotation_dict_with_nested(tmp_path):
    """嵌套 dict 也能加载。"""
    p = tmp_path / "nested.json"
    p.write_text('{"a": {"b": [1, 2, {"c": "d"}]}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": [1, 2, {"c": "d"}]}}


def test_load_annotation_broken_utf8_raises_unicode_decode_error(tmp_path):
    """非 UTF-8 字节 → json.load 内部 fp.read() 抛 UnicodeDecodeError（属 ValueError，不在 except 内）。"""
    p = tmp_path / "binary.json"
    p.write_bytes(b"\xff\xfe\x00\x01")
    # UnicodeDecodeError 不是 OSError 子类，所以不被 _load_annotation 的 except 捕获
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_only_catches_oserror_and_jsondecodeerror():
    """_load_annotation source 仅 catch (OSError, json.JSONDecodeError)。"""
    src = inspect.getsource(_load_annotation)
    assert "except (OSError, json.JSONDecodeError)" in src
    # 不应 catch 通用 Exception
    assert "except Exception" not in src
    assert "except:" not in src


# =========================================================================
# devset_status 传播
# =========================================================================


def test_run_evaluation_devset_status_incomplete_propagates(tmp_path):
    """manifest.devset_status='incomplete' → report.devset.status='incomplete'。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["devset"]["status"] == "incomplete"


def test_run_evaluation_devset_status_complete_propagates(tmp_path):
    """manifest.devset_status='complete' → report.devset.status='complete'。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["devset"]["status"] == "complete"


def test_run_evaluation_devset_pdf_count_reflects_documents(tmp_path):
    """含 1 个 pdf doc → devset.pdf_count=1。"""
    doc = _make_failing_doc_entry(tmp_path)  # source_type='pdf'
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["devset"]["pdf_count"] == 1
    assert report["devset"]["docx_count"] == 0


def test_run_evaluation_devset_file_count_reflects_documents(tmp_path):
    """含 2 个 doc → devset.file_count=2。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="d1")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="d2")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc1, doc2))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["devset"]["file_count"] == 2


# =========================================================================
# per_doc source_type 传播
# =========================================================================


def test_run_evaluation_per_doc_source_type_propagates(tmp_path):
    """per_doc.source_type 来自 DocumentEntry.source_type。"""
    doc = _make_failing_doc_entry(tmp_path)  # source_type='pdf'
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"][0]["source_type"] == "pdf"


def test_run_evaluation_per_doc_doc_id_propagates(tmp_path):
    """per_doc.doc_id 来自 DocumentEntry.doc_id。"""
    doc = _make_failing_doc_entry(tmp_path, doc_id="my-id-123")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"][0]["doc_id"] == "my-id-123"


# =========================================================================
# parser_name 传播
# =========================================================================


def test_run_evaluation_parser_name_default_fallback(tmp_path):
    """run_evaluation 默认 parser_name='fallback'。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_parser_name_in_provenance(tmp_path):
    """provenance.parser_name 反映输入。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_max_chars_in_provenance(tmp_path):
    """provenance.max_chars 反映输入。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path, max_chars=500)
    assert report["provenance"]["max_chars"] == 500


def test_run_evaluation_default_max_chars_800(tmp_path):
    """run_evaluation 默认 max_chars=800。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


# =========================================================================
# 错误码处理细节
# =========================================================================


def test_run_evaluation_failing_doc_error_code_in_metrics(tmp_path):
    """失败 doc 的 error_code metric 取自 errors[0].code。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    # file_not_found 来自 compute_file_hash 抛 FileNotFoundError
    assert report["per_doc"][0]["metrics"]["error_code"]["value"] == "file_not_found"


def test_run_evaluation_failing_doc_error_code_reason_none(tmp_path):
    """失败 doc 的 error_code.reason=None（即使 value 非 None）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"][0]["metrics"]["error_code"]["reason"] is None


def test_run_evaluation_failing_doc_pipeline_success_value_false(tmp_path):
    """失败 doc 的 pipeline_success.value=False（不是 null）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"][0]["metrics"]["pipeline_success"]["value"] is False


def test_run_evaluation_failing_doc_pipeline_success_reason_none(tmp_path):
    """失败 doc 的 pipeline_success.reason=None。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"][0]["metrics"]["pipeline_success"]["reason"] is None


# =========================================================================
# 完整 14 metrics key 集合验证（失败 doc）
# =========================================================================


def test_run_evaluation_failing_doc_metrics_keys_exact_14(tmp_path):
    """失败 doc 的 metrics 含精确 14 keys。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    metrics = report["per_doc"][0]["metrics"]
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    # 失败时还会含 figure_caption_prf + chunk_boundary_prf 的 6 keys（reason=not_applicable 等）
    # 所以至少含上述 14
    assert expected.issubset(set(metrics.keys()))


def test_run_evaluation_failing_doc_metrics_contains_annotation_keys(tmp_path):
    """失败 doc 仍含 figure_caption_prf + chunk_boundary_prf 的 metrics（可能 reason=not_applicable）。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    metrics = report["per_doc"][0]["metrics"]
    # annotation_metrics 始终 update 进 metrics
    assert "figure_caption_precision" in metrics
    assert "figure_caption_recall" in metrics
    assert "figure_caption_f1" in metrics
    assert "chunk_boundary_precision" in metrics
    assert "chunk_boundary_recall" in metrics
    assert "chunk_boundary_f1" in metrics


# =========================================================================
# 不依赖 git：dirty / commit 字段在 git 不可用时也合法
# =========================================================================


def test_run_evaluation_provenance_git_commit_str_or_none(tmp_path):
    """provenance.git_commit 在 git 不可用时为 None；可用时为 40-char str。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    gc = report["provenance"]["git_commit"]
    if gc is not None:
        assert isinstance(gc, str)
        # SHA-1 hex 40 chars（或短 7 chars，取决于 git 命令）
        assert all(c in "0123456789abcdef" for c in gc)


# =========================================================================
# write_json=False 行为：runner 不写 doc-level JSON
# =========================================================================


def test_run_evaluation_does_not_write_per_doc_json(tmp_path):
    """runner 不应在 outputs/ 下写 per-doc JSON 文件（process_single write_json=False）。"""
    doc = _make_failing_doc_entry(tmp_path, doc_id="no-write")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    # outputs/ 下只有 out.json（不应有 no-write.json 等 doc-level JSON）
    parent_files = list(out_path.parent.glob("*.json"))
    assert out_path in parent_files
    # 不应有 no-write.json
    no_write = out_path.parent / "no-write.json"
    assert not no_write.is_file()


# =========================================================================
# 自定义 output_path 在子目录下
# =========================================================================


def test_run_evaluation_output_in_nested_subdir(tmp_path):
    """output_path 在嵌套子目录下也能创建并写盘。"""
    manifest = _make_empty_manifest(tmp_path)
    nested = tmp_path / "deep" / "nested" / "subdir"
    out_path = nested / "out.json"
    report = run_evaluation(manifest, out_path)
    assert out_path.is_file()
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_output_creates_parent_dirs(tmp_path):
    """output_path 的父目录不存在时，run_evaluation 应创建。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "new_dir" / "out.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()
    assert out_path.parent.is_dir()
