# -*- coding: utf-8 -*-
"""Stage 6 批次 7 评测归因验证（docs/table-caption-relation-contract.md §7）。

对照批次 6 封存基线 outputs/evaluation-batch6-zerodiff-check.json
（git_commit=7d06f34，evaluator_version=1.8）逐字段 diff 新跑
outputs/evaluation-batch7-attribution-check.json。

排除集（逐项归因）：
- wall_time_seconds.total：计时
- provenance.git_commit / run_timestamp_iso：运行环境

必然不变断言（比批次 6 更强）：
- provenance.evaluator_version：维持 1.8（契约 §1：评测能力未变，
  不新增报告指标族）
- 任何 .metrics. 路径零差异：table_has_caption 无对应 GT 键，不进
  任何指标族；figure_caption_* 沿用批次 6 值

任何越界差异 → 退出码 1。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "outputs" / "evaluation-batch6-zerodiff-check.json"
NEW = ROOT / "outputs" / "evaluation-batch7-attribution-check.json"

_EXCLUDED_PROV = {"git_commit", "run_timestamp_iso"}

diffs: list[str] = []


def walk(path: str, a, b) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(f"{path}.{k}: only-in-new={b[k]!r}")
            elif k not in b:
                diffs.append(f"{path}.{k}: only-in-old={a[k]!r}")
            else:
                walk(f"{path}.{k}", a[k], b[k])
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: len {len(a)} != {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(f"{path}[{i}]", x, y)
    else:
        if a != b:
            diffs.append(f"{path}: {a!r} != {b!r}")


def excluded(diff_line: str) -> bool:
    path = diff_line.split(":", 1)[0]
    if ".wall_time_seconds." in path and path.endswith(".total"):
        return True
    if path.startswith(".provenance."):
        return path.split(".")[2] in _EXCLUDED_PROV
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    old = json.loads(BASE.read_text(encoding="utf-8"))
    new = json.loads(NEW.read_text(encoding="utf-8"))

    walk("", old, new)

    real = [d for d in diffs if not excluded(d)]
    allowed = [d for d in diffs if excluded(d)]

    # 排除集"必然不同"断言：git_commit 与 run_timestamp_iso 必须确实变化
    must_change = [
        any("provenance.git_commit" in d for d in diffs),
        any("provenance.run_timestamp_iso" in d for d in diffs),
    ]
    # 必然不变断言：evaluator_version 维持 1.8；任何 metrics 路径零差异
    must_not_change = [
        not any("provenance.evaluator_version" in d for d in diffs),
        not any(".metrics." in d for d in diffs),
    ]
    print(f"total field diffs: {len(diffs)}")
    print(f"allowed (exclusion set, with attribution): {len(allowed)}")
    for d in allowed:
        print(f"  [excluded] {d}")
    print(f"unexpected diffs: {len(real)}")
    for d in real[:50]:
        print(f"  [DIFF] {d}")
    print(f"must-change assertions (git_commit, run_timestamp_iso): {must_change}")
    print(f"must-not-change assertions (evaluator_version, metrics): {must_not_change}")
    if real or not all(must_change) or not all(must_not_change):
        print("VERDICT: FAIL")
        raise SystemExit(1)
    print("VERDICT: PASS — 除计时/运行环境外逐字段一致；评测能力面零变化")


if __name__ == "__main__":
    main()
