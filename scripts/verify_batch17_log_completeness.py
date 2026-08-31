"""批次 17 验证：结构化日志完整性检查。

规则（Stage 8 批次 17 裁决）：
- 每行必须为合法 JSON
- 首事件 batch_start / eval_start，末事件 batch_complete / eval_complete
- file_complete + file_error 数 == batch_start.file_count
- doc_complete + doc_error 数 == eval_start.doc_count
- complete 事件 success + failed == 文档总数

用法：
    python scripts/verify_batch17_log_completeness.py --log outputs/b.jsonl --kind batch
    python scripts/verify_batch17_log_completeness.py --log outputs/e.jsonl --kind eval
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="结构化日志完整性验证")
    p.add_argument("--log", required=True, help="JSONL 日志文件路径")
    p.add_argument("--kind", choices=("batch", "eval"), required=True)
    args = p.parse_args(argv)

    log_path = Path(args.log)
    if not log_path.is_file():
        print(f"[ERROR] 日志文件不存在: {log_path}", file=sys.stderr)
        return 2

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        print("[FAIL] 日志文件为空", file=sys.stderr)
        return 1

    events = []
    for i, line in enumerate(lines, 1):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"[FAIL] 第 {i} 行不是合法 JSON: {e}", file=sys.stderr)
            return 1

    failures: list[str] = []
    if args.kind == "batch":
        first, last = events[0], events[-1]
        if first.get("event") != "batch_start":
            failures.append(f"首事件应为 batch_start，实际 {first.get('event')}")
        if last.get("event") != "batch_complete":
            failures.append(f"末事件应为 batch_complete，实际 {last.get('event')}")
        n = first.get("file_count")
        ok = sum(1 for e in events if e.get("event") == "file_complete")
        err = sum(1 for e in events if e.get("event") == "file_error")
        if ok + err != n:
            failures.append(f"file_complete({ok}) + file_error({err}) != file_count({n})")
        if last.get("success", 0) + last.get("failed", 0) != n:
            failures.append("batch_complete 的 success + failed != file_count")
        print(
            f"batch: events={len(events)} file_count={n} "
            f"file_complete={ok} file_error={err} "
            f"success={last.get('success')} failed={last.get('failed')}"
        )
    else:
        first, last = events[0], events[-1]
        if first.get("event") != "eval_start":
            failures.append(f"首事件应为 eval_start，实际 {first.get('event')}")
        if last.get("event") != "eval_complete":
            failures.append(f"末事件应为 eval_complete，实际 {last.get('event')}")
        n = first.get("doc_count")
        ok = sum(1 for e in events if e.get("event") == "doc_complete")
        err = sum(1 for e in events if e.get("event") == "doc_error")
        if ok + err != n:
            failures.append(f"doc_complete({ok}) + doc_error({err}) != doc_count({n})")
        if last.get("success", 0) + last.get("failed", 0) != n:
            failures.append("eval_complete 的 success + failed != doc_count")
        print(
            f"eval: events={len(events)} doc_count={n} "
            f"doc_complete={ok} doc_error={err} "
            f"success={last.get('success')} failed={last.get('failed')}"
        )

    if failures:
        for f in failures:
            print(f"[FAIL] {f}", file=sys.stderr)
        return 1
    print("[OK] 日志完整性验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
