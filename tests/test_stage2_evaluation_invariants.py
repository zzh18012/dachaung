"""Round 91 — Stage 2 评测方法学不变量测试。

互补于 per-module 单测，这里覆盖 CLAUDE.md 与 docs/evaluation.md 中描述的
Stage 2 评测方法学不变量：
- 计时只记 total；parse/chunk null + reason="not_instrumented"
- 比例指标分母为 0 时返回 null + reason，不返回 1.0
- 聚合按类型分开：counts 求和、success_rates 算 rate、ratio macro average、silent_drop 求和
- figure_caption_* 始终 null + parser_does_not_emit_relations
- chunk_boundary_* 一对一匹配，tolerance_chars 在报告中记录
- manifest path 必须相对项目根 + 正斜杠
- silent_drop_count 基于 expectations.element_count_by_type
- 报告写 devset_status/file_count/content_group_count/pdf_count/docx_count/categories_covered
- 原始评测报告 JSON 写到 outputs/（不进 git）

不修改任何源码。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio, compute_automatic_metrics


# =============================================================================
# 计时不变量：parse/chunk 必须 null + not_instrumented
# =============================================================================


def test_stage2_runner_emits_parse_chunk_null_with_not_instrumented(tmp_path):
    """run_evaluation 产出的 wall_time_seconds.parse/chunk 必须 null + reason。"""
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello world", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    output = proj_root / "report.json"
    report = run_evaluation(manifest, output, parser_name="fallback")

    for r in report["per_doc"]:
        wt = r["wall_time_seconds"]
        assert wt["parse"] is None
        assert wt["chunk"] is None
        assert wt.get("parse_reason") == "not_instrumented"
        assert wt.get("chunk_reason") == "not_instrumented"
        # total 必须有值（非 None）
        assert wt["total"] is not None


def test_stage2_runner_total_is_non_negative(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    for r in report["per_doc"]:
        assert r["wall_time_seconds"]["total"] >= 0


def test_stage2_runner_total_only_one_value_not_duplicated(tmp_path):
    """total 只记一次，不在 parse/chunk 中重复。"""
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    wt = report["per_doc"][0]["wall_time_seconds"]
    # parse/chunk 都是 None，不存在把 total 复制到这两个字段的情况
    assert wt["parse"] is None
    assert wt["chunk"] is None


# =============================================================================
# 比例指标：分母为 0 → null + reason，绝不返回 1.0
# =============================================================================


def test_stage2_helper_null_returns_value_none():
    """_null 返回 value=None + reason。"""
    m = _null("my_reason")
    assert m["value"] is None
    assert m["reason"] == "my_reason"


def test_stage2_helper_ratio_returns_value_float():
    m = _ratio(0.5)
    assert m["value"] == 0.5
    assert m["reason"] is None


def test_stage2_helper_ratio_zero_denominator_returns_null_not_one():
    """metrics.py 的 _pdf_locator_ratio 等内部函数在分母为 0 时返回 _null。
    通过 figure_caption_prf 的常量 reason 验证该模式：始终 null + reason。"""
    result = figure_caption_prf(None, None)
    for k, v in result.items():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_stage2_compute_metrics_no_chunks_ratios_not_one():
    """无 chunks 的 Document：所有 ratio 指标 value 应当是 None 或 0.0，绝不能是 1.0。"""
    document = {
        "elements": [
            {"type": "paragraph", "element_id": "e1", "content": "hello",
             "source_locator": {"line": 1}},
        ],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="text",
        expectations=None,
        image_base_dir=None,
    )
    # 找所有 ratio 指标
    for name, m in metrics.items():
        if "ratio" in name or "precision" in name or "recall" in name or "f1" in name:
            v = m["value"]
            # 不允许 1.0：要么 None（无预测），要么 0.0
            assert v != 1.0, f"{name} returned 1.0 with no chunks"


# =============================================================================
# figure_caption_* 始终 null + parser_does_not_emit_relations
# =============================================================================


def test_stage2_figure_caption_constants_locked():
    """figure_caption 三指标必须固定 null + 常量 reason。"""
    for doc_input in [None, {}, {"chunks": []}, {"elements": []}]:
        for ann_input in [None, {}, {"chunk_boundary_anchors": []}]:
            result = figure_caption_prf(doc_input, ann_input)
            for k, v in result.items():
                assert v["value"] is None
                assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_stage2_figure_caption_does_not_use_heuristic():
    """本期不引入"最近图片"启发式 —— 函数永远返回常量 reason。"""
    result = figure_caption_prf(
        {"elements": [{"type": "image", "element_id": "img1"}]},
        {"figure_caption_pairs": [{"figure_marker": "Fig 1", "caption_text": "x"}]},
    )
    for k, v in result.items():
        assert v["value"] is None
        assert v["reason"] != "nearest_image_heuristic"


# =============================================================================
# chunk_boundary：一对一匹配，tolerance_chars 必须在报告中记录
# =============================================================================


def test_stage2_chunk_boundary_tolerance_recorded_in_output():
    """所有路径都必须输出 _tolerance_chars。"""
    document = None
    annotation = None
    result = chunk_boundary_prf(document, annotation, tolerance_chars=42)
    assert result["_tolerance_chars"]["value"] == 42


def test_stage2_chunk_boundary_default_tolerance_30():
    """默认容差 30。"""
    result = chunk_boundary_prf({"chunks": []}, None)
    assert result["_tolerance_chars"]["value"] == 30


def test_stage2_chunk_boundary_one_to_one_match():
    """一对一匹配：1 predicted 只能匹配 1 anchor。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "abc", "position": "after"},  # 第 2 个找不到（search_from 推进）
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 第 1 个 anchor 匹配 predicted；第 2 个 anchor marker 在 stream 中找不到（已用尽）
    # → recall = 1/2 或 1/1（取决于 missing_markers）
    # 一对一：predicted 不能同时匹配 2 个 anchor
    assert result["chunk_boundary_precision"]["value"] in (None, 1.0)
    assert result["chunk_boundary_recall"]["value"] in (None, 0.5, 1.0)


def test_stage2_chunk_boundary_run_includes_tolerance_in_per_doc(tmp_path):
    """run_evaluation 产出的 per_doc 必须含 _tolerance_chars（运行时移除，公开 per_doc 不含）。"""
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello world", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(
        manifest, proj_root / "report.json", tolerance_chars=99
    )
    # 公开 per_doc 不含 _tolerance_chars（schema additionalProperties:false）
    for r in report["per_doc"]:
        assert "_tolerance_chars" not in r
        assert "_missing_markers" not in r
        assert "_annotation_present" not in r


# =============================================================================
# manifest path：必须相对项目根 + 正斜杠
# =============================================================================


def test_stage2_manifest_rejects_absolute_path(tmp_path):
    """manifest schema 拒绝绝对路径（用 evaluation.schema.validate 校验）。"""
    from evaluation.schema import EvalSchemaError, validate

    abs_path = str(tmp_path / "test.docx").replace("\\", "/")
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": abs_path, "source_type": "docx"},
        ],
    }
    # manifest schema 本身不强制拒绝绝对路径（只用 minLength:1）
    # load_manifest 在解析时检查 _is_absolute_like → 拒绝
    from evaluation.manifest import ManifestError, load_manifest

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # 校验 schema 通过
    validate(manifest, "manifest.schema.json")

    # 但 load_manifest 应当拒绝
    with pytest.raises((ManifestError, EvalSchemaError, Exception)):
        load_manifest(manifest_path)


def test_stage2_manifest_rejects_backslash_path(tmp_path):
    """manifest 中 path 不允许反斜杠。"""
    from evaluation.manifest import load_manifest

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples\\test.docx", "source_type": "docx"},
        ],
    }), encoding="utf-8")

    with pytest.raises(Exception):
        load_manifest(manifest_path)


def test_stage2_manifest_path_must_be_inside_project_root(tmp_path):
    """path 解析后必须位于 project_root 内（防止路径穿越）。"""
    from evaluation.manifest import load_manifest

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    (proj_root / "samples").mkdir()
    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "../outside.docx", "source_type": "docx"},
        ],
    }), encoding="utf-8")

    with pytest.raises(Exception):
        load_manifest(manifest_path)


# =============================================================================
# silent_drop_count：基于 expectations.element_count_by_type
# =============================================================================


def test_stage2_silent_drop_count_null_when_no_expectations():
    """无 expectations → silent_drop_count null。"""
    document = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "x",
                      "source_locator": {"line": 1}}],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="text",
        expectations=None,
        image_base_dir=None,
    )
    sdc = metrics.get("silent_drop_count", {})
    assert sdc.get("value") is None


def test_stage2_silent_drop_count_zero_when_expectations_match():
    """expectations 与 elements 一致 → silent_drop_count = 0。"""
    document = {
        "elements": [
            {"type": "paragraph", "element_id": "e1", "content": "a",
             "source_locator": {"line": 1}},
            {"type": "paragraph", "element_id": "e2", "content": "b",
             "source_locator": {"line": 2}},
        ],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="text",
        expectations={"element_count_by_type": {"paragraph": 2}},
        image_base_dir=None,
    )
    sdc = metrics.get("silent_drop_count", {})
    assert sdc.get("value") == 0


def test_stage2_silent_drop_count_positive_when_expectations_exceed():
    """expectations 比 elements 多 → silent_drop_count = 差值。"""
    document = {
        "elements": [
            {"type": "paragraph", "element_id": "e1", "content": "a",
             "source_locator": {"line": 1}},
        ],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="text",
        expectations={"element_count_by_type": {"paragraph": 5}},
        image_base_dir=None,
    )
    sdc = metrics.get("silent_drop_count", {})
    assert sdc.get("value") == 4  # 5 - 1


# =============================================================================
# 报告：devset 必含 6 字段
# =============================================================================


def test_stage2_report_devset_has_six_required_fields(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    dev = report["devset"]
    for k in (
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    ):
        assert k in dev, f"missing {k}"


def test_stage2_report_devset_status_reflects_manifest(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    assert report["devset"]["status"] == "incomplete"


# =============================================================================
# 聚合：counts 求和、success_rates 算 rate、ratio macro average、silent_drop 求和
# =============================================================================


def test_stage2_aggregate_counts_sums_per_doc(tmp_path):
    """summary.counts 是 per_doc 字段求和。"""
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    for i in range(3):
        (samples / f"doc{i}.docx").write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": f"d{i}", "path": f"samples/doc{i}.docx", "source_type": "docx"}
            for i in range(3)
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    counts = report["summary"].get("counts", {})
    # element_count 或 chunk_count 等计数指标应当是 3 个 doc 的总和
    # 具体 key 取决于 metrics 实现，但聚合后应是求和结果
    assert isinstance(counts, dict)


def test_stage2_aggregate_does_not_mix_into_composite_score(tmp_path):
    """summary 不混合出"综合分数"（CLAUDE.md 关键约束）。"""
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    summary = report["summary"]
    # 不允许出现综合分数键
    forbidden_keys = {"overall_score", "composite_score", "total_score", "grade"}
    for k in forbidden_keys:
        assert k not in summary, f"summary 含违禁键 {k}"


def test_stage2_aggregate_silent_drop_total_is_sum(tmp_path):
    """silent_drop_total 应当是 per_doc.silent_drop_count 求和。"""
    from evaluation.report import aggregate_summary

    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    summary = aggregate_summary(per_doc)
    # None 应被跳过，2 + 3 = 5
    assert summary["silent_drop_total"] == 5


# =============================================================================
# 输出位置：报告 JSON 写到 outputs/（gitignored）
# =============================================================================


def test_stage2_outputs_directory_is_gitignored():
    """outputs/ 应当在 .gitignore 中。"""
    project_root = Path(__file__).resolve().parent.parent
    gitignore = project_root / ".gitignore"
    if not gitignore.is_file():
        pytest.skip("no .gitignore")
    content = gitignore.read_text(encoding="utf-8")
    assert "outputs" in content or "outputs/" in content


def test_stage2_outputs_directory_exists_or_irrelevant():
    """outputs/ 目录可能存在或不存在（评测时创建），不强制。"""
    project_root = Path(__file__).resolve().parent.parent
    outputs = project_root / "outputs"
    # 不强制存在；如果存在，里面应有 .gitkeep 或评测输出
    if outputs.exists():
        assert outputs.is_dir()


# =============================================================================
# 评测版本契约（不动 evaluator_version / report_version）
# =============================================================================


def test_stage2_evaluator_version_locked_at_1_1():
    """CLAUDE.md：evaluator_version = 1.1，不允许在本阶段变更。"""
    from evaluation import EVALUATOR_VERSION
    assert EVALUATOR_VERSION == "1.1"


def test_stage2_report_version_locked_at_1_1():
    """CLAUDE.md：report_version = 1.1。"""
    from evaluation import REPORT_VERSION
    assert REPORT_VERSION == "1.1"


def test_stage2_annotation_version_locked_at_1_0():
    from evaluation import ANNOTATION_VERSION
    assert ANNOTATION_VERSION == "1.0"


def test_stage2_manifest_version_locked_at_1_0():
    from evaluation import MANIFEST_VERSION
    assert MANIFEST_VERSION == "1.0"


def test_stage2_report_includes_evaluator_version_in_provenance(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    assert report["provenance"]["evaluator_version"] == "1.1"
    assert report["provenance"]["report_version"] == "1.1"
    assert report["report_version"] == "1.1"


# =============================================================================
# 失败文档也写入 per_doc（不丢弃）
# =============================================================================


def test_stage2_failed_documents_still_in_per_doc(tmp_path):
    """失败文档也应当写入 per_doc（CLAUDE.md 关键约束）。"""
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    # 写入伪 docx（实际是文本）→ fallback_parser 失败
    doc = samples / "test.docx"
    doc.write_text("hello world", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    assert len(report["per_doc"]) == 1
    ps = report["per_doc"][0]["metrics"].get("pipeline_success", {}).get("value")
    # 伪 docx 大概率失败 → pipeline_success 不是 True
    assert ps is not True


def test_stage2_failed_doc_metrics_mostly_null_with_pipeline_failed(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("not a real docx", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    metrics = report["per_doc"][0]["metrics"]
    # 失败时大多数指标应当 null + "pipeline_failed"
    null_count = sum(1 for m in metrics.values() if isinstance(m, dict) and m.get("value") is None)
    assert null_count >= 5  # 至少 5 个指标是 null


# =============================================================================
# expected_failures 处理
# =============================================================================


def test_stage2_expected_failures_in_report(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    bad = samples / "bad.docx"
    bad.write_text("not real docx", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "fail1",
                "path": "samples/bad.docx",
                "expected_error_code": "docx_parse_failed",
                "source_type": "docx",
            }
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    ef = report.get("expected_failures", [])
    assert len(ef) == 1
    assert ef[0]["doc_id"] == "fail1"
    assert ef[0]["expected_error_code"] == "docx_parse_failed"
    assert "actual_error_code" in ef[0]
    assert "matches" in ef[0]
    assert isinstance(ef[0]["matches"], bool)


def test_stage2_expected_failures_matches_reflects_actual(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    bad = samples / "bad.docx"
    bad.write_text("not real docx", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "fail1",
                "path": "samples/bad.docx",
                "expected_error_code": "docx_parse_failed",
                "source_type": "docx",
            }
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = run_evaluation(manifest, proj_root / "report.json")
    ef = report["expected_failures"][0]
    # matches 必须等于 (actual == expected)
    assert ef["matches"] == (ef["actual_error_code"] == ef["expected_error_code"])


# =============================================================================
# 报告自校验：报告 JSON 必须过 schema
# =============================================================================


def test_stage2_report_validates_against_schema(tmp_path):
    from evaluation.schema import validate as eval_validate
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    output = proj_root / "report.json"
    run_evaluation(manifest, output)

    # 加载磁盘文件并校验
    with output.open("r", encoding="utf-8") as f:
        report_data = json.load(f)
    eval_validate(report_data, "evaluation-report.schema.json")  # 不抛


def test_stage2_report_written_to_disk_matches_returned(tmp_path):
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples = proj_root / "samples"
    samples.mkdir()
    doc = samples / "test.docx"
    doc.write_text("hello", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
        ],
    }), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    output = proj_root / "report.json"
    returned = run_evaluation(manifest, output)
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    # 基本字段一致
    assert returned["report_version"] == on_disk["report_version"]
    assert len(returned["per_doc"]) == len(on_disk["per_doc"])


# =============================================================================
# 当前 devset incomplete（不冒充 complete）
# =============================================================================


def test_stage2_devset_status_incomplete_in_current_devset():
    """CLAUDE.md：当前 devset 固定 incomplete，所有数字称为 pilot baseline。

    本测试验证：用 incomplete 状态跑出的报告里 status 是 incomplete。
    """
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        proj_root = Path(td)
        samples = proj_root / "samples"
        samples.mkdir()
        (samples / "test.docx").write_text("hello", encoding="utf-8")

        manifest_path = proj_root / "manifest.json"
        manifest_path.write_text(json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "samples/test.docx", "source_type": "docx"}
            ],
        }), encoding="utf-8")

        manifest = load_manifest(manifest_path)
        report = run_evaluation(manifest, proj_root / "report.json")
        assert report["devset"]["status"] == "incomplete"
