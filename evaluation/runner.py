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

from app.pipeline import process_single

from evaluation import REPORT_VERSION
from evaluation.annotation_metrics import (
    chunk_boundary_prf,
    figure_caption_prf,
    heading_order_prf,
)
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
)

# --parser auto 的 source_type → parser 映射（仅按 manifest 声明，不猜扩展名）。
# 未注册的类型（text/ipynb）不路由到任何 parser——fallback 会把 .txt 错送进
# docx 路径产出误导性错误码，故由 runner 合成结构化 unsupported_type；
# parser 注册后加入本映射。
AUTO_PARSER_BY_SOURCE_TYPE = {
    "pdf": "fallback",
    "docx": "fallback",
    "markdown": "markdown",
    "html": "html",
    "text": "text",
    "ipynb": "ipynb",
}


def _resolve_parser_name(requested: str, source_type: str | None) -> str | None:
    """auto 模式下按 source_type 解析；未注册类型返回 None（文档级失败）。"""
    if requested != "auto":
        return requested
    if source_type is None:
        # expected_failures 的旧条目可无 source_type（pdf/docx 时代），
        # 沿用 fallback 保持旧行为
        return "fallback"
    return AUTO_PARSER_BY_SOURCE_TYPE.get(source_type)


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
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, float, str | None, Path]:
    """跑 process_single，返回 (document_dict, error_dict, total_seconds, parser_version, image_dir)。

    使用 write_json=False 但 output_path 给定，使 pipeline 推导出 image_output_dir
    并把图片落盘。返回 image_dir 让 metrics 校验 resource_path 时使用。
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

    # image_output_dir 与 pipeline 内部规则保持一致
    image_dir: Path | None = None
    if document is not None:
        # pipeline: out_root / images-{source_hash[:16]}
        # 我们 out_stub.parent = output_root/_per_doc/，所以 image_dir 是 _per_doc/images-<sha16>/
        # 用 document_id 反推（document_id = doc-{source_hash[:16]}）
        did = document.document_id
        sha16 = did.replace("doc-", "") if did.startswith("doc-") else did
        image_dir = out_stub.parent / f"images-{sha16}"

    # 清理 _per_doc 目录（图片留下；空目录留作 image_dir 引用）
    if out_stub.is_file():
        try:
            out_stub.unlink()
        except OSError:
            pass

    if errors:
        return None, errors[0].to_dict(), elapsed, None, image_dir or Path()
    if document is None:
        return (
            None,
            {"code": "unknown", "message": "process_single returned None without errors"},
            elapsed,
            None,
            image_dir or Path(),
        )
    return document.to_dict(), None, elapsed, document.parser_version, image_dir or Path()


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
        effective_parser = _resolve_parser_name(parser_name, doc.source_type)
        if effective_parser is None:
            # auto 遇未注册 source_type：合成结构化失败，不跑 pipeline
            document, error, total_seconds, parser_version, image_dir = (
                None,
                {
                    "code": "unsupported_type",
                    "message": (
                        f"auto 调度尚未注册 source_type={doc.source_type} 的 parser"
                    ),
                    "details": {"source_type": doc.source_type, "parser_mode": "auto"},
                },
                0.0,
                None,
                Path(),
            )
        else:
            document, error, total_seconds, parser_version, image_dir = _process_one(
                doc, output_root, effective_parser, max_chars
            )
        if parser_version and not parser_version_for_prov:
            parser_version_for_prov = parser_version

        metrics = compute_automatic_metrics(
            document=document,
            error=error,
            source_type=doc.source_type,
            expectations=doc.expectations,
            image_base_dir=image_dir if image_dir.is_dir() else None,
        )

        annotation = _load_annotation(doc.annotation_resolved)
        fig_caps = figure_caption_prf(document, annotation)
        chunk_b = chunk_boundary_prf(
            document, annotation, tolerance_chars=tolerance_chars
        )
        head_ord = heading_order_prf(document, annotation)
        metrics.update(fig_caps)
        tolerance_record = chunk_b.pop("_tolerance_chars", None)
        missing_markers_record = chunk_b.pop("_missing_markers", None)
        metrics.update(chunk_b)
        metrics.update(head_ord)

        per_doc_results.append(
            {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "parser_used": effective_parser or "none",
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
        ef_parser = _resolve_parser_name(parser_name, ef.source_type)
        if ef_parser is None:
            actual_code = "unsupported_type"
        else:
            out_stub = output_root / "_per_doc" / f"{ef.doc_id}.json"
            out_stub.parent.mkdir(parents=True, exist_ok=True)
            document, errors = process_single(
                ef.resolved_path,
                out_stub,
                parser_name=ef_parser,
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
        # auto 模式下多 parser 并存，单一 parser_version 会误导 → null
        parser_version=None if parser_name == "auto" else parser_version_for_prov,
    )
    devset = build_devset_section(manifest)
    summary = aggregate_summary(per_doc_results)

    public_per_doc = []
    for r in per_doc_results:
        public_per_doc.append(
            {
                "doc_id": r["doc_id"],
                "source_type": r["source_type"],
                "parser_used": r["parser_used"],
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
