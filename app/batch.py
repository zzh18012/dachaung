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
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Iterable

from app.pipeline import process_single

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
    """批模式按扩展名路由：fallback 仅支持 pdf/docx，.md 走 markdown。"""
    p = Path(path)
    if parser_name == "fallback" and p.suffix.lower() == ".md":
        return "markdown"
    return parser_name


def _result(
    file: str | Path,
    success: bool,
    seconds: float,
    *,
    elements: int = 0,
    chunks: int = 0,
    warning_codes: list[str] | None = None,
    code: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "file": str(file),
        "success": success,
        "elements": elements,
        "chunks": chunks,
        "warnings": warning_codes or [],
        "error_code": code,
        "error_message": message,
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

    if not src_path.is_file():
        return _result(
            src_path, False, time.perf_counter() - t0,
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
            code=type(exc).__name__, message=str(exc),
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
            code=first.get("code"), message=first.get("message"),
        )

    assert document is not None
    return _result(
        src_path, True, seconds,
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


def batch_parse_files(
    file_list: Iterable[str | Path],
    output_dir: str | Path,
    *,
    parser_name: str = "fallback",
    max_chars: int = 800,
    workers: int | None = None,
) -> dict[str, Any]:
    """批量解析并写盘，返回 summary dict（同时写 <output_dir>/summary.json）。

    summary.wall_time_seconds 为父进程墙钟（并行加速比据此计算），
    不是各文档 seconds 之和。
    """
    workers = default_workers() if workers is None else max(1, int(workers))
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

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

    wall0 = time.perf_counter()
    if effective_workers == 1:
        results = list(
            _progress((parse_one_file(a) for a in args_list), len(args_list), "parse")
        )
    else:
        with Pool(effective_workers) as pool:
            results = list(
                _progress(
                    pool.imap_unordered(parse_one_file, args_list),
                    len(args_list),
                    "parse",
                )
            )
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
