# -*- coding: utf-8 -*-
"""Stage 7 批次 9（P1 标注解锁）评测归因验证。

对照批次 7 封存基线 outputs/evaluation-batch7-attribution-check.json
（批次 8 未跑评测，最近封存基线即批次 7）逐字段 diff 新跑
outputs/evaluation-batch9-figcap-unlock.json。

预期变化（批次 9 核心任务，逐项归因）：
- per_doc[0]（DC-MVP-001 docx）.metrics.figure_caption_{precision,recall,
  f1} 的 value 与 reason：null+no_annotation_pairs → 1.0+null
排除集（运行环境）：
- wall_time_seconds.total / provenance.git_commit / run_timestamp_iso
必然不变断言：
- provenance.evaluator_version 维持 1.8
- per_doc[1]（PDF）figure_caption_* 仍 null+no_annotation（无标注）
- 其余全部 .metrics. 路径零差异
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "outputs" / "evaluation-batch7-attribution-check.json"
NEW = ROOT / "outputs" / "evaluation-batch9-figcap-unlock.json"

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
    # 批次 9 核心变化：仅 docx 文档（per_doc[0]）的 figure_caption_* 解锁
    if (path.startswith(".per_doc[0].metrics.figure_caption_")
            and ("figure_caption_precision" in path
                 or "figure_caption_recall" in path
                 or "figure_caption_f1" in path)):
        return True
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    old = json.loads(BASE.read_text(encoding="utf-8"))
    new = json.loads(NEW.read_text(encoding="utf-8"))

    walk("", old, new)

    real = [d for d in diffs if not excluded(d)]
    allowed = [d for d in diffs if excluded(d)]

    must_change = [
        any("provenance.git_commit" in d for d in diffs),
        any("provenance.run_timestamp_iso" in d for d in diffs),
        any(".per_doc[0].metrics.figure_caption_precision.value" in d
            for d in diffs),
        any(".per_doc[0].metrics.figure_caption_precision.reason" in d
            for d in diffs),
    ]
    must_not_change = [
        not any("provenance.evaluator_version" in d for d in diffs),
        not any(".per_doc[1].metrics.figure_caption_" in d for d in diffs),
        not any(d for d in diffs
                if ".metrics." in d
                and "figure_caption_" in d
                and not d.startswith(".per_doc[0].metrics.figure_caption_")),
    ]
    print(f"total field diffs: {len(diffs)}")
    print(f"allowed (exclusion set, with attribution): {len(allowed)}")
    for d in allowed:
        print(f"  [excluded] {d}")
    print(f"unexpected diffs: {len(real)}")
    for d in real[:50]:
        print(f"  [DIFF] {d}")
    print(f"must-change (git_commit, ts, fc_value, fc_reason): {must_change}")
    print(f"must-not-change (evaluator_version, pdf_fc, other_metrics): "
          f"{must_not_change}")
    if real or not all(must_change) or not all(must_not_change):
        print("VERDICT: FAIL")
        raise SystemExit(1)
    print("VERDICT: PASS — 仅 docx figure_caption_* 解锁 + 运行环境；"
          "PDF 侧与其余指标族零变化")


if __name__ == "__main__":
    main()
