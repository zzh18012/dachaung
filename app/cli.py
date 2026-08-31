"""命令行入口。

用法：
    # 解析 + 分块 + 校验 + 写盘
    python -m app.cli parse <input.pdf|input.docx> -o <output.json>
    python -m app.cli parse <input.docx> -o <output.json> --parser fallback --max-chars 1000

    # 批量解析（目录 / glob / 单文件，多进程并行 + summary.json）
    python -m app.cli batch-parse <dir|glob|file> -o <output_dir> [--workers 8]

    # 仅校验已有的 JSON（独立子命令，不会把 JSON 当成 PDF/DOCX 输入）
    python -m app.cli validate <output.json>
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
    parse = sub.add_parser("parse", help="解析 PDF/DOCX/MD → 统一文档模型 → 分块 → JSON")
    parse.add_argument("input", help="输入文件路径（PDF/DOCX/MD）")
    parse.add_argument("-o", "--output", required=True, help="输出 JSON 路径")
    parse.add_argument(
        "--parser",
        choices=("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"),
        default="fallback",
        help="选择解析器（默认 fallback；kreuzberg 已实测对 DOCX 给不出元素结构）",
    )
    parse.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="分块最大字符数（默认 800）",
    )

    # validate 子命令
    val = sub.add_parser("validate", help="校验已有的 JSON 文件是否符合 Schema")
    val.add_argument("input", help="待校验的 JSON 文件路径")

    # batch-parse 子命令（Stage 8 批次 16）
    from app.batch import default_workers

    batch = sub.add_parser(
        "batch-parse",
        help="批量解析：目录（递归 pdf/docx/md）/ glob 模式 / 单文件 → 多进程并行 + summary.json",
    )
    batch.add_argument(
        "input", help="输入目录、glob 模式（含 * 或 ?）或单文件路径"
    )
    batch.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="输出目录（每文档 1 个 JSON + summary.json）",
    )
    batch.add_argument(
        "--parser",
        choices=("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"),
        default="fallback",
        help="选择解析器（默认 fallback）",
    )
    batch.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="分块最大字符数（默认 800）",
    )
    batch.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"并行进程数（默认 min(cpu_count, 8) = {default_workers()}）",
    )
    batch.add_argument(
        "--log-file",
        default=None,
        help="结构化日志（JSONL，append）输出路径，建议 outputs/ 下（gitignored）",
    )
    batch.add_argument(
        "--verbose",
        action="store_true",
        help="把结构化日志同时打到 stderr（与进度输出可能交错）",
    )
    return p


def _emit_structured_error(input_path: Path, code: str, message: str, **extra) -> None:
    err = {
        "schema_version": "0.1.0",
        "input": str(input_path),
        "errors": [{"code": code, "message": message, **(extra or {})}],
    }
    print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)


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

    if args.command == "parse":
        input_path = Path(args.input)
        output_path = Path(args.output)
        if not input_path.is_file():
            _emit_structured_error(input_path, "file_not_found", f"输入文件不存在: {input_path}")
            return 1

        document, errors = process_single(
            input_path,
            output_path,
            parser_name=args.parser,
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

    if args.command == "batch-parse":
        import glob as globlib

        from app.batch import BATCH_SUFFIXES, batch_parse_files

        raw = args.input
        input_path = Path(raw)
        if input_path.is_dir():
            files = sorted(
                p for p in input_path.rglob("*") if p.suffix.lower() in BATCH_SUFFIXES
            )
        elif any(ch in raw for ch in "*?["):
            files = sorted(Path(p) for p in globlib.glob(raw, recursive=True))
        else:
            if not input_path.is_file():
                print(f"[ERROR] 输入文件不存在: {input_path}", file=sys.stderr)
                return 2
            files = [input_path]
        if not files:
            print(f"[ERROR] 未找到可解析文件: {raw}", file=sys.stderr)
            return 2

        out_dir = Path(args.output_dir)
        summary = batch_parse_files(
            files,
            out_dir,
            parser_name=args.parser,
            max_chars=args.max_chars,
            log_file=args.log_file,
            verbose=args.verbose,
            workers=args.workers,
        )
        status = "[OK]" if summary["failed"] == 0 else "[FAIL]"
        print(
            f"{status} batch-parse: {summary['success']}/{summary['total']} 成功，"
            f"workers={summary['workers']}，"
            f"{summary['wall_time_seconds']:.1f}s → {out_dir / 'summary.json'}"
        )
        for err in summary["errors"]:
            print(f"  [FAIL] {err['file']}: {err['code']} {err['message']}", file=sys.stderr)
        return 0 if summary["failed"] == 0 else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
