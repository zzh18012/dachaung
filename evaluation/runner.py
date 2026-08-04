"""评测 runner：清单 → 逐文档跑 pipeline → 计算指标 → 装配报告。

关键约束：
- 计时只记 total（用 time.perf_counter 包住 process_single）
- parse / chunk 在本阶段未插桩：null + reason="not_instrumented"
  - 不修改 app/pipeline.py；不复制 pipeline 逻辑
- 失败文档（errors 非空）也写入 per_doc，但 metrics 大多为 null + "pipeline_failed"
- 图片资源：让 pipeline 把图片写入 outputs/<doc_id>/ 子目录（write_json=False 但
  output_path 给定，使 image_output_dir 仍被推导），这样 image_resource_exists_ratio
  才能真实反映 fallback parser 的能力
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.pipeline import image_output_dir_for, process_single

from evaluation import REPORT_VERSION
from evaluation.annotation_metrics import (
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
)


def _load_annotation(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _process_one(
    doc,  # DocumentEntry
    output_root: Path,
    parser_name: str,
    max_chars: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, float, str | None, Path | None]:
    """跑 process_single，返回 (document_dict, error_dict, total_seconds, parser_version, image_dir)。

    使用 write_json=False 但 output_path 给定，使 pipeline 推导出 image_output_dir
    并把图片落盘。返回 image_dir 让 metrics 校验 resource_path 时使用。

    image_dir 在 document 为 None 时也返回 None（而非 Path()——前者会让下游把 cwd
    当作 image_base_dir，是 bug）。
    """
    # 用 doc_id 作目录名，避免不同 doc 的 images-<sha> 混在一起难以归属
    out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"
    out_stub.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    document, errors = process_single(
        doc.resolved_path,
        out_stub,  # 给 output_path 让 pipeline 推 image_output_dir
        parser_name=parser_name,
        max_chars=max_chars,
        write_json=False,
    )
    elapsed = time.perf_counter() - t0

    # image_dir 与 pipeline 内部规则保持一致：直接复用 pipeline 的命名约定 helper，
    # 不再从 document_id 反推（避免硬编码 document_id 前缀与目录命名两个约定）。
    image_dir: Path | None = None
    if document is not None:
        image_dir = image_output_dir_for(out_stub, document.source_hash)

    # 清理 _per_doc 目录（图片留下；空目录留作 image_dir 引用）
    if out_stub.is_file():
        try:
            out_stub.unlink()
        except OSError:
            pass

    if errors:
        return None, errors[0].to_dict(), elapsed, None, image_dir
    if document is None:
        return (
            None,
            {"code": "unknown", "message": "process_single returned None without errors"},
            elapsed,
            None,
            image_dir,
        )
    return document.to_dict(), None, elapsed, document.parser_version, image_dir


def run_evaluation(
    manifest,  # Manifest
    output_path: Path,
    *,
    parser_name: str = "fallback",
    max_chars: int = 800,
    tolerance_chars: int = 30,
) -> dict[str, Any]:
    """跑评测主流程，返回报告 dict（同时写到 output_path）。"""
    output_root = Path(output_path).parent
    output_root.mkdir(parents=True, exist_ok=True)

    per_doc_results: list[dict[str, Any]] = []
    parser_version_for_prov: str | None = None

    for doc in manifest.documents:
        document, error, total_seconds, parser_version, image_dir = _process_one(
            doc, output_root, parser_name, max_chars
        )
        if parser_version and not parser_version_for_prov:
            parser_version_for_prov = parser_version

        metrics = compute_automatic_metrics(
            document=document,
            error=error,
            source_type=doc.source_type,
            expectations=doc.expectations,
            image_base_dir=image_dir if (image_dir is not None and image_dir.is_dir()) else None,
        )

        annotation = _load_annotation(doc.annotation_resolved)
        fig_caps = figure_caption_prf(document, annotation)
        chunk_b = chunk_boundary_prf(
            document, annotation, tolerance_chars=tolerance_chars
        )
        metrics.update(fig_caps)
        tolerance_record = chunk_b.pop("_tolerance_chars", None)
        missing_markers_record = chunk_b.pop("_missing_markers", None)
        metrics.update(chunk_b)

        per_doc_results.append(
            {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "metrics": metrics,
                "wall_time_seconds": {
                    "total": total_seconds,
                    "parse": None,
                    "chunk": None,
                    "parse_reason": "not_instrumented",
                    "chunk_reason": "not_instrumented",
                },
                "_annotation_present": annotation is not None,
                "_tolerance_chars": (
                    tolerance_record["value"] if tolerance_record else None
                ),
                "_missing_markers": (
                    missing_markers_record["value"]
                    if missing_markers_record
                    else []
                ),
            }
        )

    # 评测预期失败用例
    expected_failure_results: list[dict[str, Any]] = []
    for ef in manifest.expected_failures:
        out_stub = output_root / "_per_doc" / f"{ef.doc_id}.json"
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        document, errors = process_single(
            ef.resolved_path,
            out_stub,
            parser_name=parser_name,
            max_chars=max_chars,
            write_json=False,
        )
        if out_stub.is_file():
            try:
                out_stub.unlink()
            except OSError:
                pass
        actual_code = errors[0].code if errors else None
        expected_failure_results.append(
            {
                "doc_id": ef.doc_id,
                "expected_error_code": ef.expected_error_code,
                "actual_error_code": actual_code,
                "matches": actual_code == ef.expected_error_code,
            }
        )

    provenance = build_provenance(
        project_root=manifest.project_root,
        parser_name=parser_name,
        max_chars=max_chars,
        parser_version=parser_version_for_prov,
    )
    devset = build_devset_section(manifest)
    summary = aggregate_summary(per_doc_results)

    public_per_doc = []
    for r in per_doc_results:
        public_per_doc.append(
            {
                "doc_id": r["doc_id"],
                "source_type": r["source_type"],
                "metrics": r["metrics"],
                "wall_time_seconds": r["wall_time_seconds"],
            }
        )

    report = {
        "report_version": REPORT_VERSION,
        "provenance": provenance,
        "devset": devset,
        "summary": summary,
        "per_doc": public_per_doc,
        "expected_failures": expected_failure_results,
    }

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with out_p.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


__all__ = ["run_evaluation"]
