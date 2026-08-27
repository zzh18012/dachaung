"""评测报告装配：provenance + devset 元数据 + summary 聚合 + per_doc 列表。

聚合规则（不混合类型）：
- counts（element_count_total）→ 求和
- success_rates（pipeline_success, schema_valid）→ 成功文档数 + 成功率
- ratio_macro_averages（locator / image / chunk_ref / text_* / heading_boundary）
  → 各项 macro average + participating_docs + not_evaluated
- silent_drop_count → 求和（无 expectations 的文档不参与）
- expectation_checks → 按键统计 evaluated/passed/failed 文档数（未声明键不算）
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation import EVALUATOR_VERSION, REPORT_VERSION

# 标记哪些指标是 ratio（参与 macro average）
_RATIO_METRICS = (
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
)
# 注意：figure_caption_* 始终 null（reason 固定），不参与 macro average

_COUNT_METRICS = ("element_count_total",)
_SUCCESS_BOOL_METRICS = ("pipeline_success",)

# expectation 契约检查：per-doc value 为 {expected/…, passed: bool} 或 null
_CHECK_METRICS = (
    "required_markers_check",
    "forbidden_markers_check",
    "must_not_error_codes_check",
    "max_silent_drop_check",
)


def get_git_provenance(project_root: Path) -> dict[str, Any]:
    """读 git commit 与 dirty 状态。失败时 commit=null, dirty=true。"""
    commit: str | None = None
    dirty: bool = True
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if r.returncode == 0:
            commit = r.stdout.strip() or None
        # dirty：porcelain 输出非空表示有未提交修改
        r2 = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        dirty = bool(r2.returncode == 0 and r2.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        commit = None
        dirty = True
    return {"git_commit": commit, "git_dirty": dirty}


def get_dependency_versions() -> dict[str, str | None]:
    """读 fallback parser 实际依赖版本（pdfplumber / python-docx / pypdfium2）。

    优先用 importlib.metadata.version()（最可靠：读已安装发行版的元数据）。
    pypdfium2 模块本身没有 __version__ 属性，必须走 importlib.metadata。
    """
    import importlib.metadata

    versions: dict[str, str | None] = {}
    for pkg in ("pdfplumber", "python-docx", "pypdfium2"):
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = None
        except Exception:
            versions[pkg] = None
    return versions


def build_provenance(
    project_root: Path,
    parser_name: str,
    max_chars: int,
    parser_version: str | None,
) -> dict[str, Any]:
    git = get_git_provenance(project_root)
    return {
        "git_commit": git["git_commit"],
        "git_dirty": git["git_dirty"],
        "evaluator_version": EVALUATOR_VERSION,
        "report_version": REPORT_VERSION,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "dependencies": get_dependency_versions(),
        "max_chars": int(max_chars),
        "run_timestamp_iso": datetime.now().astimezone().isoformat(),
    }


def build_devset_section(manifest) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """从 Manifest 对象提取 devset 元数据（不再自行决定 status）。"""
    return {
        "status": manifest.devset_status,
        "file_count": manifest.file_count,
        "content_group_count": manifest.content_group_count,
        "pdf_count": manifest.pdf_count,
        "docx_count": manifest.docx_count,
        "categories_covered": manifest.categories_covered,
    }


def aggregate_summary(per_doc_results: list[dict[str, Any]]) -> dict[str, Any]:
    """聚合所有 per_doc 的指标。不混合类型。"""
    summary: dict[str, Any] = {}

    # counts: 求和
    counts: dict[str, Any] = {}
    for name in _COUNT_METRICS:
        values = [
            r["metrics"].get(name, {}).get("value")
            for r in per_doc_results
            if r["metrics"].get(name, {}).get("value") is not None
        ]
        if values:
            counts[name] = {
                "sum": sum(values),
                "participating_docs": len(values),
            }
        else:
            counts[name] = {"sum": None, "participating_docs": 0}
    summary["counts"] = counts

    # success_rates: 成功数 + 成功率
    success_rates: dict[str, Any] = {}
    for name in _SUCCESS_BOOL_METRICS:
        successes = sum(
            1
            for r in per_doc_results
            if r["metrics"].get(name, {}).get("value") is True
        )
        total = len(per_doc_results)
        rate = (successes / total) if total else None
        success_rates[name] = {
            "success_count": successes,
            "total": total,
            "rate": rate,
        }
    summary["success_rates"] = success_rates

    # ratio macro averages
    ratio_avgs: dict[str, Any] = {}
    for name in _RATIO_METRICS:
        values = [
            r["metrics"].get(name, {}).get("value")
            for r in per_doc_results
            if r["metrics"].get(name, {}).get("value") is not None
        ]
        not_eval = len(per_doc_results) - len(values)
        if values:
            macro = sum(values) / len(values)
        else:
            macro = None
        ratio_avgs[name] = {
            "macro_average": macro,
            "participating_docs": len(values),
            "not_evaluated": not_eval,
        }
    summary["ratio_macro_averages"] = ratio_avgs

    # silent_drop_count: 求和（null 不参与）
    silent_vals = [
        r["metrics"].get("silent_drop_count", {}).get("value")
        for r in per_doc_results
        if r["metrics"].get("silent_drop_count", {}).get("value") is not None
    ]
    summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None

    # expectation 契约检查：按键统计 通过/失败/未声明
    checks: dict[str, Any] = {}
    for name in _CHECK_METRICS:
        evaluated = passed = failed = 0
        for r in per_doc_results:
            v = r["metrics"].get(name, {}).get("value")
            if v is None:
                continue
            evaluated += 1
            if v.get("passed") is True:
                passed += 1
            else:
                failed += 1
        checks[name] = {
            "evaluated_docs": evaluated,
            "passed_docs": passed,
            "failed_docs": failed,
        }
    summary["expectation_checks"] = checks

    return summary


__all__ = [
    "build_provenance",
    "build_devset_section",
    "aggregate_summary",
    "get_git_provenance",
    "get_dependency_versions",
]
