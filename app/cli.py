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

    # explain-parser 子命令（Stage 8 批次 22）
    exp = sub.add_parser(
        "explain-parser",
        help=(
            "解释 --parser auto 的选择：扩展名 → 候选 parser + 胜者 + 原因"
            "（仅按扩展名，不读文件内容、不实例化 parser）"
        ),
    )
    exp.add_argument(
        "input",
        help="输入文件路径（仅取扩展名；文件不存在也可解释）",
    )
    exp.add_argument(
        "--plugin",
        action="append",
        default=None,
        metavar="MODULE",
        help="外部插件模块（dotted 名，可重复；加载后参与解释）",
    )
    exp.add_argument(
        "--json",
        action="store_true",
        help=(
            "输出机器可读 JSON（显式字段：extension/candidates/winner/"
            "reason/tied_names）"
        ),
    )

    # audit-parsers 子命令（Stage 8 批次 23）
    aud = sub.add_parser(
        "audit-parsers",
        help=(
            "审计注册表全局解析竞争：扩展名全集 → 每扩展候选/胜者/平局"
            "（只读，不实例化 parser、不读文件）"
        ),
    )
    aud.add_argument(
        "--plugin",
        action="append",
        default=None,
        metavar="MODULE",
        help="外部插件模块（dotted 名，可重复；加载后参与审计）",
    )
    aud.add_argument(
        "--json",
        action="store_true",
        help="输出机器可读 JSON（extensions 明细 + summary 计数）",
    )

    # list-parsers 子命令（Stage 8 批次 18；批次 19 增 --plugin；
    # 批次 21 Phase C 增 --json 与能力列）
    lp = sub.add_parser(
        "list-parsers",
        help=(
            "列出已注册 parser（含插件）：name / priority / extensions /"
            " source_types / locator_family / version"
        ),
    )
    lp.add_argument(
        "--plugin",
        action="append",
        default=None,
        metavar="MODULE",
        help="外部插件模块（dotted 名，可重复；加载后再列出）",
    )
    lp.add_argument(
        "--json",
        action="store_true",
        help="输出机器可读 JSON（list_parsers() 行原样，(priority, name) 稳定序）",
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

    if args.command == "audit-parsers":
        from app.parser_registry import discover_parser_details, list_parsers

        rc = _load_cli_plugins(args.plugin, "audit-parsers")
        if rc is not None:
            return rc
        # extension universe：已注册 capability snapshot 的 extensions 并集
        # （经 list_parsers() 读取快照，不建第二份缓存、不扫文件系统）
        extensions = sorted({
            ext
            for row in list_parsers()
            for ext in row["extensions"]
        })
        entries = []
        for ext in extensions:
            result = discover_parser_details(Path("x" + ext))
            # status 是 CLI 派生展示字段（derived presentation field），
            # 不是 discovery 状态——禁止反向进入 DiscoveryResult
            if len(result.candidates) == 1:
                status = "uncontested"
            elif result.tied_names:
                status = "tie"
            else:
                status = "priority_competition"
            entries.append((result, status))
        summary = {
            "extension_count": len(entries),
            "uncontested": sum(1 for _, s in entries if s == "uncontested"),
            "priority_competition": sum(
                1 for _, s in entries if s == "priority_competition"
            ),
            "tie": sum(1 for _, s in entries if s == "tie"),
        }
        if args.json:
            payload = {
                "extensions": [
                    {
                        "extension": r.extension,
                        "candidates": [
                            {
                                "name": c.name,
                                "priority": c.priority,
                                "registration_order": c.registration_order,
                            }
                            for c in r.candidates
                        ],
                        "winner": r.winner,
                        "reason": r.reason,
                        "tied_names": list(r.tied_names),
                        "status": s,
                    }
                    for r, s in entries
                ],
                "summary": summary,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        print(
            f"{'extension':<12} {'winner':<20} {'status':<22} candidates"
        )
        for r, s in entries:
            cands = ", ".join(
                f"{c.name}({c.priority})" for c in r.candidates
            )
            tie_note = (
                "  <- 平局：先注册者胜"
                if s == "tie"
                else ""
            )
            print(
                f"{r.extension:<12} {r.winner:<20} {s:<22} {cands}{tie_note}"
            )
        print(
            f"\nsummary: {summary['extension_count']} extensions | "
            f"uncontested={summary['uncontested']} "
            f"priority_competition={summary['priority_competition']} "
            f"tie={summary['tie']}"
        )
        return 0

    if args.command == "explain-parser":
        from app.parser_registry import discover_parser_details

        input_path = Path(args.input)
        # 插件加载先于解释（与 parse 一致的加载序，批次 19 契约）
        rc = _load_cli_plugins(args.plugin, str(input_path))
        if rc is not None:
            return rc
        result = discover_parser_details(input_path)
        if result.winner is None:
            _emit_structured_error(input_path, "unsupported_type", result.reason)
            return 1
        if args.json:
            # 批次 22 D4 裁决：显式构造字段，不直接序列化 dataclass
            # （CLI JSON 是公开契约，防未来内部字段泄漏）
            payload = {
                "extension": result.extension,
                "candidates": [
                    {
                        "name": c.name,
                        "priority": c.priority,
                        "registration_order": c.registration_order,
                    }
                    for c in result.candidates
                ],
                "winner": result.winner,
                "reason": result.reason,
                "tied_names": list(result.tied_names),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        print(f"extension: {result.extension}")
        print("candidates（priority 升序，同 priority 先注册者胜）:")
        for c in result.candidates:
            mark = "  <-- winner" if c.name == result.winner else ""
            print(
                f"  {c.name:<24} priority={c.priority:<6}"
                f" registration_order={c.registration_order}{mark}"
            )
        print(f"winner: {result.winner}")
        print(f"reason: {result.reason}")
        print(
            "\n注：仅按扩展名解释，未读取文件内容"
            "（resolution based on extension only; file content was not read）"
        )
        return 0

    if args.command == "list-parsers":
        rc = _load_cli_plugins(args.plugin, "list-parsers")
        if rc is not None:
            return rc
        rows = _reg_list_parsers()
        if args.json:
            # 批次 21 Phase C：机器可读能力清单（数据源 list_parsers()
            # → _capabilities 快照，不重读 Parser 类）
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        header = (
            f"{'name':<20} {'priority':<8} {'extensions':<18}"
            f" {'source_types':<18} {'locator_family':<16} version"
        )
        print(header)
        for r in rows:
            exts = ",".join(r["extensions"]) or "-"
            sts = ",".join(r["source_types"]) or "-"
            fam = r["locator_family"] or "-"
            print(
                f"{r['name']:<20} {r['priority']:<8} {exts:<18}"
                f" {sts:<18} {fam:<16} {r['version']}"
            )
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
