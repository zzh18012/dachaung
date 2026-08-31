"""批量解析：多进程并行处理文档列表（Stage 8 批次 16，Option A 裁决）。

关键约束（会话 cf170a6f，GPT 5.6 Sol 裁决）：
- worker 为模块级函数（Windows spawn 可 pickle）
- worker 内自写 JSON，IPC 只传小 dict（不回传 Document 大对象）
- 错误全隔离：Python 异常永不出 worker；单文档失败不中断批
- 小批次（<3 文件）或 workers=1 走顺序路径（免 spawn + import 开销）
- 已知限制：pdfplumber 底层 C 库崩溃（segfault）会破坏进程池（docs/BACKLOG.md）
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback as traceback_mod
from multiprocessing import Pool, Queue as MpQueue
from pathlib import Path
from typing import Any, Iterable

from app.jsonlog import setup_logger
from app.parser_registry import registered_names
from app.pipeline import process_single
from app.plugin_loader import PluginLoadError, load_plugins

try:  # 可选依赖：新增依赖须用户单独批准，未装时降级为逐行进度
    from tqdm import tqdm as _tqdm
except ImportError:  # pragma: no cover - 取决于环境是否安装 tqdm
    _tqdm = None

BATCH_SUFFIXES = (".pdf", ".docx", ".md")
DEFAULT_MAX_WORKERS = 8
SEQUENTIAL_THRESHOLD = 3


def default_workers() -> int:
    """默认并行数：min(cpu_count, 8)。内存 ∝ workers × 最大文档峰值。"""
    return min(os.cpu_count() or 1, DEFAULT_MAX_WORKERS)


def effective_parser_for(parser_name: str, path: str | Path) -> str:
    """批模式按扩展名路由。

    - auto：注册表 discover_parser（priority 最小者）；无候选时回落
      fallback（worker 侧产出 unsupported_type 结构化错误，不炸批）
    - fallback 仅支持 pdf/docx，.md 走 markdown（批次 16 既有行为）
    """
    from app.parser_registry import discover_parser

    p = Path(path)
    if parser_name == "auto":
        try:
            return discover_parser(p)
        except ValueError:
            return "fallback"
    if parser_name == "fallback" and p.suffix.lower() == ".md":
        return "markdown"
    return parser_name


# 批次 19：worker 侧插件初始化状态。initializer 永不抛异常（避免进程池
# 重生循环/挂起），失败经 multiprocessing.Queue 恰回报一次，父进程在
# 任何文件任务派发前收取全部回报（受控通道，探测式 map 无法保证覆盖
# 每个 worker）。
_WORKER_PLUGIN_ERROR: dict | None = None
PLUGIN_INIT_REPORT_TIMEOUT = 120.0


def _worker_init_plugins(
    modules: tuple[str, ...], report_queue: Any
) -> None:
    """Pool initializer：在每个 worker 进程内重放插件加载（Windows spawn）。

    只捕获 PluginLoadError（load_plugins 契约保证只抛该类型）：存入
    worker 全局（作 parse_one_file 防御背板），并恰回报一次给父进程。
    """
    global _WORKER_PLUGIN_ERROR
    try:
        load_plugins(list(modules))
        report_queue.put({"ok": True})
    except PluginLoadError as e:
        _WORKER_PLUGIN_ERROR = e.to_dict()
        report_queue.put({"ok": False, **_WORKER_PLUGIN_ERROR})


def _result(
    file: str | Path,
    success: bool,
    seconds: float,
    *,
    parser: str | None = None,
    elements: int = 0,
    chunks: int = 0,
    warning_codes: list[str] | None = None,
    code: str | None = None,
    message: str | None = None,
    tb: str | None = None,
) -> dict[str, Any]:
    return {
        "file": str(file),
        "success": success,
        "parser": parser,
        "elements": elements,
        "chunks": chunks,
        "warnings": warning_codes or [],
        "error_code": code,
        "error_message": message,
        "traceback": tb,
        "seconds": seconds,
    }


def parse_one_file(args: tuple) -> dict[str, Any]:
    """Worker：单文档解析 + 写盘，返回小 dict（可 pickle，异常永不出界）。

    Args:
        args: (src, out_dir, parser_name, max_chars)
    """
    src, out_dir, parser_name, max_chars = args
    src_path = Path(src)
    out_path = Path(out_dir) / f"{src_path.stem}.json"
    t0 = time.perf_counter()

    # 批次 19 防御背板：initializer 已捕获插件加载失败时，任何任务都不再
    # 触碰解析路径，直接返回结构化失败（正常情况下探测阶段已先行暴露）
    if _WORKER_PLUGIN_ERROR is not None:
        return _result(
            src_path, False, time.perf_counter() - t0,
            parser=parser_name,
            code=_WORKER_PLUGIN_ERROR["code"],
            message=_WORKER_PLUGIN_ERROR["message"],
        )

    if not src_path.is_file():
        return _result(
            src_path, False, time.perf_counter() - t0,
            parser=parser_name,
            code="file_not_found", message=f"输入文件不存在: {src_path}",
        )

    try:
        document, errors = process_single(
            src_path,
            out_path,
            parser_name=parser_name,
            max_chars=max_chars,
            write_json=True,
        )
    except Exception as exc:  # noqa: BLE001 — 裁决要求错误隔离：任何异常都转为失败结果
        return _result(
            src_path, False, time.perf_counter() - t0,
            parser=parser_name,
            code=type(exc).__name__, message=str(exc),
            tb=traceback_mod.format_exc(),
        )

    seconds = time.perf_counter() - t0

    if errors:
        # 失败不留半成品 JSON
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass
        first = errors[0].to_dict()
        return _result(
            src_path, False, seconds,
            parser=parser_name,
            code=first.get("code"), message=first.get("message"),
        )

    assert document is not None
    return _result(
        src_path, True, seconds,
        parser=parser_name,
        elements=len(document.elements),
        chunks=len(document.chunks),
        warning_codes=[w.code for w in document.warnings],
    )


def _progress(iterable: Iterable[dict[str, Any]], total: int, desc: str):
    """进度输出：tqdm（已装且 stderr 为 TTY）优先，否则每文档一行。"""
    if _tqdm is not None and sys.stderr.isatty():
        yield from _tqdm(iterable, total=total, desc=desc)
        return
    for i, r in enumerate(iterable, 1):
        name = Path(r["file"]).name
        if r["success"]:
            print(f"[{i}/{total}] {desc} {name} OK {r['seconds']:.1f}s", file=sys.stderr)
        else:
            print(f"[{i}/{total}] {desc} {name} FAIL {r['error_code']}", file=sys.stderr)
        yield r


def _log_file_event(logger, r: dict[str, Any]) -> None:
    """结果到达即发：success → file_complete + 逐 warning 码；else → file_error。"""
    if r["success"]:
        logger.info(
            "file_complete",
            extra={
                "file": r["file"],
                "parser": r["parser"],
                "elements": r["elements"],
                "chunks": r["chunks"],
                "seconds": r["seconds"],
            },
        )
        for wc in r["warnings"]:
            logger.warning("file_warning", extra={"file": r["file"], "warning_code": wc})
    else:
        logger.error(
            "file_error",
            extra={
                "file": r["file"],
                "parser": r["parser"],
                "error_code": r["error_code"],
                # "message" 是 LogRecord 保留属性，extra 不可用 → error_message
                "error_message": r["error_message"],
                "traceback": r["traceback"],
            },
        )


def batch_parse_files(
    file_list: Iterable[str | Path],
    output_dir: str | Path,
    *,
    parser_name: str = "fallback",
    max_chars: int = 800,
    log_file: str | Path | None = None,
    verbose: bool = False,
    workers: int | None = None,
    plugins: list[str] | None = None,
) -> dict[str, Any]:
    """批量解析并写盘，返回 summary dict（同时写 <output_dir>/summary.json）。

    summary.wall_time_seconds 为父进程墙钟（并行加速比据此计算），
    不是各文档 seconds 之和。

    log_file / verbose：结构化 JSONL 日志（app.jsonlog.setup_logger）。
    事件在结果到达时流式发射（并行下非 manifest 顺序）。

    plugins（批次 19）：父进程在池创建前加载（fail-fast 抛 PluginLoadError，
    不启动批处理）；并行路径每 worker initializer 重放加载，探测阶段在任何
    文件任务前校验全部 worker 初始化成功，失败则受控终止池并抛
    PluginLoadError（不挂起、不泄漏原始 traceback）。
    """
    workers = default_workers() if workers is None else max(1, int(workers))
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger("app.batch", log_file, verbose)

    plugin_modules = list(plugins or [])
    try:
        loaded_plugins = load_plugins(plugin_modules) if plugin_modules else []
    except PluginLoadError as e:
        logger.error(
            "plugin_load_failed",
            extra={
                "plugin": e.plugin,
                "error_code": e.code,
                "error_message": e.error_message,
            },
        )
        raise
    for entry in loaded_plugins:
        logger.info(
            "plugin_loaded",
            extra={
                "plugin": entry["plugin"],
                "parsers_added": entry["parsers_added"],
            },
        )

    files = [Path(f) for f in file_list]

    # stem 冲突：父进程侧检测，后者记错误不派发（不覆盖前者的输出）
    seen: dict[str, Path] = {}
    tasks: list[Path] = []
    collision_errors: list[dict[str, Any]] = []
    for p in files:
        if p.stem in seen:
            collision_errors.append(
                {
                    "file": str(p),
                    "code": "stem_collision",
                    "message": f"输出文件名与 {seen[p.stem]} 冲突，未覆盖",
                }
            )
        else:
            seen[p.stem] = p
            tasks.append(p)

    args_list = [
        (f, out_dir, effective_parser_for(parser_name, f), max_chars) for f in tasks
    ]
    effective_workers = (
        workers if workers > 1 and len(args_list) >= SEQUENTIAL_THRESHOLD else 1
    )

    logger.info(
        "batch_start",
        extra={
            "workers": effective_workers,
            "file_count": len(files),
            "parser": parser_name,
            "max_chars": max_chars,
            "plugins": plugin_modules,
        },
    )
    for ce in collision_errors:
        logger.error(
            "file_error",
            extra={
                "file": ce["file"],
                "error_code": ce["code"],
                "error_message": ce["message"],
                "traceback": None,
            },
        )

    wall0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    if effective_workers == 1:
        for r in _progress(
            (parse_one_file(a) for a in args_list), len(args_list), "parse"
        ):
            _log_file_event(logger, r)
            results.append(r)
    else:
        pool_kwargs: dict[str, Any] = {}
        init_reports: list[dict[str, Any]] = []
        report_queue: Any = None
        if plugin_modules:
            report_queue = MpQueue()
            pool_kwargs = {
                "initializer": _worker_init_plugins,
                "initargs": (tuple(plugin_modules), report_queue),
            }
        try:
            with Pool(effective_workers, **pool_kwargs) as pool:
                # 批次 19 受控通道：收取每个 worker 恰一次的初始化回报
                # （在文件任务派发前）；not ok / 回报超时 → 受控上抛，
                # with 语句退出即 terminate + join 回收池
                if plugin_modules:
                    try:
                        init_reports = [
                            report_queue.get(timeout=PLUGIN_INIT_REPORT_TIMEOUT)
                            for _ in range(effective_workers)
                        ]
                    except Exception as e:  # queue.Empty 等：同样受控，不挂起
                        raise PluginLoadError(
                            "plugin_init_report_timeout",
                            ",".join(plugin_modules),
                            type(e).__name__,
                            f"worker 初始化回报超时/异常（{PLUGIN_INIT_REPORT_TIMEOUT}s）: {e}",
                        ) from None
                    bad = next((r for r in init_reports if not r.get("ok", True)), None)
                    if bad is not None:
                        logger.error(
                            "plugin_load_failed",
                            extra={
                                "plugin": bad.get("plugin"),
                                "error_code": bad.get("code"),
                                "error_message": bad.get("message"),
                                "worker_init": True,
                            },
                        )
                        raise PluginLoadError(
                            bad.get("code", "plugin_import_failed"),
                            bad.get("plugin", "?"),
                            bad.get("error_type", ""),
                            bad.get("message", ""),
                        )
                for r in _progress(
                    pool.imap_unordered(parse_one_file, args_list),
                    len(args_list),
                    "parse",
                ):
                    _log_file_event(logger, r)
                    results.append(r)
        finally:
            if report_queue is not None:
                report_queue.close()
    wall = time.perf_counter() - wall0

    failed_results = [r for r in results if not r["success"]]
    errors = (
        [
            {
                "file": r["file"],
                "code": r["error_code"],
                "message": r["error_message"],
            }
            for r in failed_results
        ]
        + collision_errors
    )
    summary = {
        "total": len(files),
        "success": len(results) - len(failed_results),
        "failed": len(errors),
        "workers": effective_workers,
        "wall_time_seconds": wall,
        "errors": errors,
    }

    logger.info(
        "batch_complete",
        extra={
            "success": summary["success"],
            "failed": summary["failed"],
            "wall_time_seconds": wall,
        },
    )

    with (out_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    return summary


__all__ = [
    "BATCH_SUFFIXES",
    "SEQUENTIAL_THRESHOLD",
    "batch_parse_files",
    "default_workers",
    "parse_one_file",
]
