"""命令行入口。

用法：
    # 解析 + 分块 + 校验 + 写盘
    python -m app.cli parse <input.pdf|input.docx> -o <output.json>
    python -m app.cli parse <input.docx> -o <output.json> --parser fallback --max-chars 1000

    # 仅校验已有的 JSON（独立子命令，不会把 JSON 当成 PDF/DOCX 输入）
    python -m app.cli validate <output.json>

    # 可读概览已有的 JSON（不写盘，仅 stdout）
    python -m app.cli inspect <output.json>
    python -m app.cli inspect <output.json> --elements --chunks
    python -m app.cli inspect <output.json> --elements --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows 上子进程的 stdout 默认是 cp936；强制 utf-8 让输出在所有平台一致
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

from app.pipeline import process_single, validate_only


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app.cli",
        description=(
            "面向 KVFS 的复合文档解析与结构分块原型 CLI。\n"
            "  解析：python -m app.cli parse <input.pdf|input.docx> -o <output.json>\n"
            "  校验：python -m app.cli validate <output.json>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # parse 子命令
    parse = sub.add_parser("parse", help="解析 PDF/DOCX/MD/HTML/TXT/IPYNB → 统一文档模型 → 分块 → JSON")
    parse.add_argument("input", help="输入文件路径（PDF/DOCX/MD/HTML/TXT/IPYNB）")
    parse.add_argument("-o", "--output", required=True, help="输出 JSON 路径")
    parse.add_argument(
        "--parser",
        choices=("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"),
        default=None,
        help="选择解析器（默认按扩展名自动推断：.pdf/.docx→fallback, "
             ".md/.markdown→markdown, .html/.htm→html, .txt/.text→text, "
             ".ipynb→ipynb；kreuzberg 需显式指定）",
    )
    parse.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="分块最大字符数（默认 800）",
    )

    # parse-dir 子命令
    pd = sub.add_parser(
        "parse-dir",
        help="目录批量解析：遍历输入目录所有支持类型的文件",
    )
    pd.add_argument("input_dir", help="输入目录")
    pd.add_argument("-o", "--output-dir", required=True, help="输出目录（JSON 与 summary 写入此）")
    pd.add_argument(
        "--recursive",
        action="store_true",
        help="递归遍历子目录（默认仅顶层）",
    )
    pd.add_argument(
        "--parser",
        choices=("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"),
        default=None,
        help="强制覆盖扩展名推断（默认按每个文件的扩展名推断）",
    )
    pd.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="分块最大字符数（默认 800）",
    )

    # validate 子命令
    val = sub.add_parser("validate", help="校验已有的 JSON 文件是否符合 Schema")
    val.add_argument("input", help="待校验的 JSON 文件路径")

    # inspect 子命令
    ins = sub.add_parser(
        "inspect",
        help="可读概览已有的 JSON（摘要 + 可选 elements/chunks 明细）",
    )
    ins.add_argument("input", help="已生成的文档 JSON 路径")
    ins.add_argument(
        "--elements",
        action="store_true",
        help="列出每个 element 的一行摘要（type / id / 内容预览）",
    )
    ins.add_argument(
        "--chunks",
        action="store_true",
        help="列出每个 chunk 的一行摘要（id / char 数 / 来源 element 数 / 文本预览）",
    )
    ins.add_argument(
        "--limit",
        type=int,
        default=10,
        help="与 --elements/--chunks 配合，限制列出条数（默认 10；<=0 表示全列）",
    )
    return p


def _emit_structured_error(input_path: Path, code: str, message: str, **extra) -> None:
    err = {
        "schema_version": "0.1.0",
        "input": str(input_path),
        "errors": [{"code": code, "message": message, **(extra or {})}],
    }
    print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)


_EXTENSION_TO_PARSER: dict[str, str] = {
    ".pdf": "fallback",
    ".docx": "fallback",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".txt": "text",
    ".text": "text",
    ".ipynb": "ipynb",
}


def _infer_parser_name(input_path: Path) -> str:
    """按扩展名推断 parser 名称。未知扩展名回退到 fallback。"""
    return _EXTENSION_TO_PARSER.get(input_path.suffix.lower(), "fallback")


def _iter_supported_files(input_dir: Path, recursive: bool):
    """遍历目录中所有支持类型的文件，按文件名升序。"""
    if recursive:
        candidates = sorted(p for p in input_dir.rglob("*") if p.is_file())
    else:
        candidates = sorted(p for p in input_dir.iterdir() if p.is_file())
    return [p for p in candidates if p.suffix.lower() in _EXTENSION_TO_PARSER]


def _relative_output_path(input_dir: Path, file_path: Path, output_dir: Path) -> Path:
    """计算输出 JSON 路径：output_dir / <relative-path-with-suffix>.json。

    例如：input_dir/sub/doc.md → output_dir/sub/doc.md.json
    """
    rel = file_path.relative_to(input_dir)
    # 把 suffix 也包含进文件名再加 .json，避免 doc.md 与 doc.html 冲突
    return output_dir / (str(rel).replace("\\", "/") + ".json")


def _run_parse(args) -> int:
    """parse 子命令实现。"""
    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.is_file():
        _emit_structured_error(input_path, "file_not_found", f"输入文件不存在: {input_path}")
        return 1

    parser_name = args.parser
    if parser_name is None:
        parser_name = _infer_parser_name(input_path)
        print(
            f"[INFO] 未指定 --parser，按扩展名 {input_path.suffix or '(无)'} "
            f"自动选择: {parser_name}",
            file=sys.stderr,
        )

    document, errors = process_single(
        input_path,
        output_path,
        parser_name=parser_name,
        max_chars=args.max_chars,
        write_json=True,
    )

    if errors:
        out = {
            "schema_version": "0.1.0",
            "input": str(input_path),
            "errors": [e.to_dict() for e in errors],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2), file=sys.stderr)
        # 失败时不能留下半成品 JSON
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass
        return 1

    assert document is not None
    print(
        f"[OK] {input_path} → {output_path}  "
        f"(elements={len(document.elements)}, chunks={len(document.chunks)}, "
        f"warnings={len(document.warnings)})"
    )
    return 0


def _run_parse_dir(args) -> int:
    """parse-dir 子命令实现。"""
    from app.pipeline import process_single

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    if not input_dir.is_dir():
        print(f"[ERROR] 输入目录不存在: {input_dir}", file=sys.stderr)
        return 2

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[ERROR] 创建输出目录失败: {e}", file=sys.stderr)
        return 1

    files = _iter_supported_files(input_dir, args.recursive)
    if not files:
        print(
            f"[WARN] {input_dir} 中未发现支持类型的文件"
            f"（支持：{', '.join(sorted(_EXTENSION_TO_PARSER))}）",
            file=sys.stderr,
        )

    summary: dict = {
        "schema_version": "0.1.0",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "recursive": bool(args.recursive),
        "parser_override": args.parser,
        "max_chars": args.max_chars,
        "total": len(files),
        "success": 0,
        "failure": 0,
        "files": [],
    }

    for f in files:
        out_path = _relative_output_path(input_dir, f, output_dir)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            summary["failure"] += 1
            summary["files"].append({
                "input": str(f),
                "output": str(out_path),
                "status": "fail",
                "errors": [{"code": "mkdir_failed", "message": str(e)}],
            })
            print(f"[FAIL] {f} (mkdir 失败: {e})", file=sys.stderr)
            continue

        parser_name = args.parser or _infer_parser_name(f)
        document, errors = process_single(
            f,
            out_path,
            parser_name=parser_name,
            max_chars=args.max_chars,
            write_json=True,
        )
        if errors:
            # 失败：清掉半成品
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            summary["failure"] += 1
            summary["files"].append({
                "input": str(f),
                "output": str(out_path),
                "status": "fail",
                "parser": parser_name,
                "errors": [e.to_dict() for e in errors],
            })
            print(
                f"[FAIL] {f} → {out_path}  "
                f"(errors={len(errors)}, first={errors[0].code})",
                file=sys.stderr,
            )
        else:
            assert document is not None
            summary["success"] += 1
            summary["files"].append({
                "input": str(f),
                "output": str(out_path),
                "status": "ok",
                "parser": parser_name,
                "elements": len(document.elements),
                "chunks": len(document.chunks),
                "warnings": len(document.warnings),
            })
            print(
                f"[OK] {f} → {out_path}  "
                f"(parser={parser_name}, elements={len(document.elements)}, "
                f"chunks={len(document.chunks)})"
            )

    summary_path = output_dir / "_summary.json"
    try:
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[ERROR] 写 summary 失败: {e}", file=sys.stderr)
        return 1

    print(
        f"\n[SUMMARY] {summary['success']}/{summary['total']} ok, "
        f"{summary['failure']} failed → {summary_path}"
    )
    return 0 if summary["failure"] == 0 else 1


def _preview(text: str | None, width: int = 60) -> str:
    """把任意文本压成单行、限定宽度的预览串（空白归一、超出加省略号）。"""
    if not text:
        return ""
    # 归一空白：换行/连续空格 → 单空格
    collapsed = " ".join(text.split())
    if len(collapsed) <= width:
        return collapsed
    return collapsed[: width - 1] + "…"


def _load_document_json(input_path: Path) -> tuple[dict | None, str]:
    """读 JSON 文件。返回 (data 或 None, 错误信息)。"""
    try:
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, f"文件不存在: {input_path}"
    except OSError as e:
        return None, f"读文件失败: {e}"
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败: {e}"
    return data, ""


def _format_summary(data: dict, input_path: Path) -> str:
    """渲染文档级摘要（不带 elements/chunks 明细）。"""
    lines: list[str] = []
    lines.append(f"file:        {input_path}")
    lines.append(f"schema:      {data.get('schema_version', '?')}")
    lines.append(f"document_id: {data.get('document_id', '?')}")
    lines.append(f"source:      {data.get('source_path', '?')}")
    lines.append(
        f"             type={data.get('source_type', '?')} "
        f"hash={data.get('source_hash', '?')[:16]}…"
    )
    lines.append(
        f"parser:      {data.get('parser_name', '?')} "
        f"v{data.get('parser_version', '?')}"
    )

    elements = data.get("elements", []) or []
    chunks = data.get("chunks", []) or []
    relations = data.get("relations", []) or []
    warnings = data.get("warnings", []) or []
    errors = data.get("errors", []) or []

    # element 按 type 计数
    type_counts: dict[str, int] = {}
    total_content_chars = 0
    for el in elements:
        t = el.get("type", "?")
        type_counts[t] = type_counts.get(t, 0) + 1
        c = el.get("content") or ""
        total_content_chars += len(c)
    type_str = (
        ", ".join(f"{t}={n}" for t, n in sorted(type_counts.items())) or "(none)"
    )

    lines.append(
        f"counts:      elements={len(elements)} "
        f"chunks={len(chunks)} "
        f"relations={len(relations)} "
        f"warnings={len(warnings)} "
        f"errors={len(errors)}"
    )
    lines.append(f"elements by type: {type_str}")
    if elements:
        avg = total_content_chars / len(elements)
        lines.append(
            f"element text: total_chars={total_content_chars} avg={avg:.0f}"
        )

    # chunk 字符数统计
    if chunks:
        chunk_lens = [len(c.get("text") or "") for c in chunks]
        lines.append(
            f"chunk text:  min={min(chunk_lens)} "
            f"max={max(chunk_lens)} "
            f"avg={sum(chunk_lens) / len(chunk_lens):.0f} "
            f"total={sum(chunk_lens)}"
        )
        # 每个 chunk 引用多少 element
        ref_counts = [len(c.get("source_element_ids") or []) for c in chunks]
        lines.append(
            f"chunk refs:  min={min(ref_counts)} max={max(ref_counts)} "
            f"avg={sum(ref_counts) / len(ref_counts):.1f}"
        )

    if warnings:
        lines.append(f"warnings ({len(warnings)}):")
        for w in warnings[:5]:
            lines.append(f"  - [{w.get('code', '?')}] {w.get('reason', '?')}")
        if len(warnings) > 5:
            lines.append(f"  … +{len(warnings) - 5} more")

    if errors:
        lines.append(f"errors ({len(errors)}):")
        for e in errors[:5]:
            lines.append(f"  - [{e.get('code', '?')}] {e.get('message', '?')}")

    return "\n".join(lines)


def _format_elements_list(elements: list[dict], limit: int) -> str:
    lines: list[str] = [f"elements ({len(elements)}):"]
    items = elements if limit <= 0 else elements[:limit]
    for el in items:
        eid = el.get("element_id", "?")
        etype = el.get("type", "?")
        parent = el.get("parent_id")
        parent_str = f" parent={parent}" if parent else ""
        content = _preview(el.get("content"), 60)
        lines.append(f"  - [{etype:9}] {eid}{parent_str}  | {content}")
    if limit > 0 and len(elements) > limit:
        lines.append(f"  … +{len(elements) - limit} more (use --limit 0 to see all)")
    return "\n".join(lines)


def _format_chunks_list(chunks: list[dict], limit: int) -> str:
    lines: list[str] = [f"chunks ({len(chunks)}):"]
    items = chunks if limit <= 0 else chunks[:limit]
    for c in items:
        cid = c.get("chunk_id", "?")
        text = c.get("text") or ""
        refs = c.get("source_element_ids") or []
        preview = _preview(text, 70)
        lines.append(
            f"  - {cid}  chars={len(text)} refs={len(refs)}  | {preview}"
        )
    if limit > 0 and len(chunks) > limit:
        lines.append(f"  … +{len(chunks) - limit} more (use --limit 0 to see all)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if args.command == "validate":
        input_path = Path(args.input)
        if not input_path.is_file():
            print(f"[ERROR] 文件不存在: {input_path}", file=sys.stderr)
            return 2
        ok, message = validate_only(input_path)
        if ok:
            print(f"[OK] {input_path} 通过 Schema 校验")
            return 0
        print(f"[FAIL] {input_path} 校验失败：{message}", file=sys.stderr)
        return 1

    if args.command == "inspect":
        input_path = Path(args.input)
        if not input_path.is_file():
            print(f"[ERROR] 文件不存在: {input_path}", file=sys.stderr)
            return 2
        data, err = _load_document_json(input_path)
        if data is None:
            print(f"[ERROR] {err}", file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print("[ERROR] JSON 顶层不是对象", file=sys.stderr)
            return 1

        out_lines: list[str] = [_format_summary(data, input_path)]
        if args.elements:
            out_lines.append("")
            out_lines.append(
                _format_elements_list(data.get("elements") or [], args.limit)
            )
        if args.chunks:
            out_lines.append("")
            out_lines.append(
                _format_chunks_list(data.get("chunks") or [], args.limit)
            )
        print("\n".join(out_lines))
        return 0

    if args.command == "parse":
        return _run_parse(args)

    if args.command == "parse-dir":
        return _run_parse_dir(args)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
