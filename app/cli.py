"""命令行入口。

用法：
    # 解析 + 分块 + 校验 + 写盘
    python -m app.cli parse <input.pdf|input.docx> -o <output.json>
    python -m app.cli parse <input.docx> -o <output.json> --parser fallback --max-chars 1000
    python -m app.cli parse <input.md> -o out.json --parser auto   # 扩展名自动发现
    python -m app.cli parse <input.myx> -o out.json --plugin my_pkg.my_plugin   # 外部插件（批次 19）

    # 批量解析（目录 / glob / 单文件，多进程并行 + summary.json）
    python -m app.cli batch-parse <dir|glob|file> -o <output_dir> [--workers 8]

    # 列出已注册 parser（含插件）
    python -m app.cli list-parsers [--plugin my_pkg.my_plugin]

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

from app.parser_registry import list_parsers as _reg_list_parsers
from app.parser_registry import registered_names as _reg_registered_names
from app.pipeline import process_single, validate_only


def _load_cli_plugins(modules: list[str] | None, input_label: str) -> int | None:
    """批次 19：加载 --plugin 模块（fail-fast，先于 parser 名称校验）。

    失败时输出结构化 errors JSON 并返回 1；成功返回 None。
    """
    if not modules:
        return None
    from app.plugin_loader import PluginLoadError, load_plugins

    try:
        load_plugins(modules)
    except PluginLoadError as e:
        d = e.to_dict()
        _emit_structured_error(
            Path(input_label),
            d["code"],
            d["message"],
            plugin=d["plugin"],
            error_type=d["error_type"],
        )
        return 1
    return None


def _validate_parser_choice(name: str, input_label: str) -> int | None:
    """批次 19：插件加载后按注册表名单动态校验 --parser（auto 为唯一保留名）。"""
    if name == "auto" or name in _reg_registered_names():
        return None
    known = ", ".join([*_reg_registered_names(), "auto"])
    _emit_structured_error(
        Path(input_label), "unknown_parser", f"未知 parser: {name}（支持: {known}）"
    )
    return 1


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
        default="fallback",
        help=(
            "选择解析器（默认 fallback；auto=按扩展名自动发现，"
            "priority 小者优先；插件加载后按注册表动态校验，"
            "未知名 → 结构化 unknown_parser）"
        ),
    )
    parse.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="分块最大字符数（默认 800）",
    )
    parse.add_argument(
        "--plugin",
        action="append",
        default=None,
        metavar="MODULE",
        help=(
            "外部插件模块（dotted 名，可重复，按出现顺序加载；"
            "仅显式加载，不做 entry_points 扫描）"
        ),
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
        default="fallback",
        help=(
            "选择解析器（默认 fallback；auto=按扩展名自动发现，逐文件路由；"
            "插件加载后按注册表动态校验）"
        ),
    )
    batch.add_argument(
        "--plugin",
        action="append",
        default=None,
        metavar="MODULE",
        help="外部插件模块（dotted 名，可重复；并行 worker 内重放加载）",
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

    # list-parsers 子命令（Stage 8 批次 18；批次 19 增 --plugin）
    lp = sub.add_parser(
        "list-parsers",
        help="列出已注册 parser（含插件）：name / priority / extensions / version",
    )
    lp.add_argument(
        "--plugin",
        action="append",
        default=None,
        metavar="MODULE",
        help="外部插件模块（dotted 名，可重复；加载后再列出）",
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
        from app.parser_registry import discover_parser

        input_path = Path(args.input)
        output_path = Path(args.output)
        if not input_path.is_file():
            _emit_structured_error(input_path, "file_not_found", f"输入文件不存在: {input_path}")
            return 1

        # 批次 19：插件加载必须先于 parser 名称校验（裁决条件 D6）
        rc = _load_cli_plugins(args.plugin, str(input_path))
        if rc is not None:
            return rc
        rc = _validate_parser_choice(args.parser, str(input_path))
        if rc is not None:
            return rc

        try:
            parser_name = (
                discover_parser(input_path)
                if args.parser == "auto"
                else args.parser
            )
        except ValueError as e:
            _emit_structured_error(input_path, "unsupported_type", str(e))
            return 1

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

    if args.command == "list-parsers":
        rc = _load_cli_plugins(args.plugin, "list-parsers")
        if rc is not None:
            return rc
        rows = _reg_list_parsers()
        print(f"{'name':<20} {'priority':<8} {'extensions':<22} version")
        for r in rows:
            exts = ",".join(r["extensions"]) or "-"
            print(f"{r['name']:<20} {r['priority']:<8} {exts:<22} {r['version']}")
        print(
            f"\n共 {len(rows)} 个已注册 parser；--parser auto 按扩展名自动发现"
            "（priority 小者优先；显式 --parser 永远覆盖发现）"
        )
        return 0

    if args.command == "batch-parse":
        import glob as globlib

        from app.batch import BATCH_SUFFIXES, batch_parse_files
        from app.plugin_loader import PluginLoadError

        # 批次 19：插件加载必须先于 parser 名称校验（裁决条件 D6）
        rc = _load_cli_plugins(args.plugin, args.input)
        if rc is not None:
            return rc
        rc = _validate_parser_choice(args.parser, args.input)
        if rc is not None:
            return rc

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
        try:
            summary = batch_parse_files(
                files,
                out_dir,
                parser_name=args.parser,
                max_chars=args.max_chars,
                log_file=args.log_file,
                verbose=args.verbose,
                workers=args.workers,
                plugins=args.plugin,
            )
        except PluginLoadError as e:
            # 父进程加载失败或 worker 初始化回报失败（受控通道，池已回收）
            d = e.to_dict()
            _emit_structured_error(
                Path(raw),
                d["code"],
                d["message"],
                plugin=d["plugin"],
                error_type=d["error_type"],
            )
            return 1
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
