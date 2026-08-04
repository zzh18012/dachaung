"""评测 CLI：子命令 run / validate-report / inspect-doc。

用法：
    python -m evaluation.cli run --manifest <path> --output <path>
        [--parser fallback] [--max-chars 800] [--tolerance-chars 30]
    python -m evaluation.cli validate-report <report.json>
    python -m evaluation.cli inspect-doc <doc.json>
        [--tolerance-chars 30]

inspect-doc：单文档快速跑指标，不写报告 JSON，仅 stdout 可读概览。
开发期 sanity check 用，省去构造 manifest 的开销。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows 控制台 utf-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

from evaluation.manifest import ManifestError, load_manifest
from evaluation.report import get_git_provenance
from evaluation.runner import run_evaluation
from evaluation.schema import EvalSchemaError, validate_file


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="evaluation.cli",
        description="评测 CLI：跑开发集 → 报告；或校验已有报告。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="跑评测，生成报告 JSON")
    run_p.add_argument("--manifest", required=True, help="清单 JSON 路径")
    run_p.add_argument("--output", required=True, help="报告输出 JSON 路径")
    run_p.add_argument(
        "--parser",
        choices=("fallback", "kreuzberg"),
        default="fallback",
        help="parser（默认 fallback）",
    )
    run_p.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="分块上限（默认 800）",
    )
    run_p.add_argument(
        "--tolerance-chars",
        type=int,
        default=30,
        help="chunk_boundary 匹配容差（字符数，默认 30）",
    )

    val_p = sub.add_parser(
        "validate-report", help="校验评测报告是否符合 evaluation-report.schema.json"
    )
    val_p.add_argument("input", help="待校验的报告 JSON 路径")

    ins_p = sub.add_parser(
        "inspect-doc",
        help="单文档跑指标 + 可读打印（不写报告，不强制 manifest）",
    )
    ins_p.add_argument("input", help="已生成的文档 JSON 路径")
    ins_p.add_argument(
        "--tolerance-chars",
        type=int,
        default=30,
        help="chunk_boundary 匹配容差（无标注时该指标固定 null）",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "run":
        manifest_path = Path(args.manifest)
        output_path = Path(args.output)
        if not manifest_path.is_file():
            print(f"[ERROR] 清单不存在: {manifest_path}", file=sys.stderr)
            return 2
        try:
            manifest = load_manifest(manifest_path)
        except (ManifestError, EvalSchemaError) as e:
            print(f"[ERROR] 清单加载失败: {e}", file=sys.stderr)
            return 1

        try:
            report = run_evaluation(
                manifest,
                output_path,
                parser_name=args.parser,
                max_chars=args.max_chars,
                tolerance_chars=args.tolerance_chars,
            )
        except EvalSchemaError as e:
            print(f"[ERROR] 生成的报告未通过 Schema 校验: {e}", file=sys.stderr)
            return 1

        # 报告生成后立刻自校验一次，确保格式合法
        try:
            validate_file(output_path, "evaluation-report.schema.json")
        except EvalSchemaError as e:
            print(f"[ERROR] 报告自校验失败: {e}", file=sys.stderr)
            return 1

        n_docs = len(report.get("per_doc", []))
        n_ok = sum(
            1
            for r in report.get("per_doc", [])
            if r["metrics"].get("pipeline_success", {}).get("value") is True
        )
        n_fail = n_docs - n_ok
        dev = report.get("devset", {})
        git = get_git_provenance(manifest.project_root)
        print(
            f"[OK] 评测完成：{output_path}\n"
            f"      documents={n_docs}（成功 {n_ok}，失败 {n_fail}）\n"
            f"      devset_status={dev.get('status')} "
            f"file_count={dev.get('file_count')} "
            f"groups={dev.get('content_group_count')} "
            f"pdf={dev.get('pdf_count')} docx={dev.get('docx_count')}\n"
            f"      git_commit={(git.get('git_commit') or 'unknown')[:12]} "
            f"git_dirty={git.get('git_dirty')}"
        )
        return 0

    if args.command == "validate-report":
        input_path = Path(args.input)
        if not input_path.is_file():
            print(f"[ERROR] 报告不存在: {input_path}", file=sys.stderr)
            return 2
        try:
            validate_file(input_path, "evaluation-report.schema.json")
        except EvalSchemaError as e:
            print(f"[FAIL] {input_path} 报告校验失败：{e}", file=sys.stderr)
            return 1
        except FileNotFoundError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
            return 1
        print(f"[OK] {input_path} 通过 evaluation-report Schema 校验")
        return 0

    if args.command == "inspect-doc":
        return _run_inspect_doc(args)

    return 2


def _format_metric(name: str, metric: dict) -> str:
    """单行渲染一个 metric：name: value (reason)。"""
    value = metric.get("value")
    reason = metric.get("reason")
    if value is None:
        return f"  {name:36} null  ({reason})"
    if isinstance(value, bool):
        return f"  {name:36} {str(value).lower()}  ({reason or 'ok'})"
    if isinstance(value, float):
        return f"  {name:36} {value:.4f}  ({reason or 'ok'})"
    if isinstance(value, dict):
        # element_count_by_type 这种 dict
        items = ", ".join(f"{k}={v}" for k, v in sorted(value.items()))
        return f"  {name:36} {items}  ({reason or 'ok'})"
    return f"  {name:36} {value}  ({reason or 'ok'})"


def _run_inspect_doc(args) -> int:
    """inspect-doc 子命令：单文档跑指标，可读打印。"""
    from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf
    from evaluation.metrics import compute_automatic_metrics

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"[ERROR] 文档不存在: {input_path}", file=sys.stderr)
        return 2
    try:
        with input_path.open("r", encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
        return 1
    if not isinstance(doc, dict):
        print("[ERROR] JSON 顶层不是对象", file=sys.stderr)
        return 1

    source_type = doc.get("source_type", "unknown")
    elements = doc.get("elements") or []
    chunks = doc.get("chunks") or []

    metrics = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type=source_type,
        expectations=None,
        image_base_dir=None,
    )
    # 标注相关指标在无标注时是 null；为了 inspect-doc 的完整性也跑一遍
    metrics.update(figure_caption_prf(doc, None))
    metrics.update(chunk_boundary_prf(doc, None, tolerance_chars=args.tolerance_chars))

    # 文档元信息
    print(f"file:        {input_path}")
    print(f"document_id: {doc.get('document_id', '?')}")
    print(f"source:      {doc.get('source_path', '?')}  type={source_type}")
    print(f"parser:      {doc.get('parser_name', '?')} v{doc.get('parser_version', '?')}")
    print(f"counts:      elements={len(elements)} chunks={len(chunks)}")
    print()
    print("metrics:")

    # 排序：先 bool/success 类，再 ratio 类，再 count 类，最后 null 类
    def _sort_key(name: str) -> tuple[int, str]:
        m = metrics.get(name, {})
        v = m.get("value")
        if v is None:
            return (3, name)
        if isinstance(v, bool):
            return (0, name)
        if isinstance(v, (int, float)):
            return (1, name)
        return (2, name)

    for name in sorted(metrics.keys(), key=_sort_key):
        print(_format_metric(name, metrics[name]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
