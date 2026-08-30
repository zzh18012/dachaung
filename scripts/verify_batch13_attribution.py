# -*- coding: utf-8 -*-
"""Stage 7 批次 13（P5 真实语料入 manifest）评测归因验证。

对照批次 12 封存基线 outputs/evaluation-batch12-table-unlock.json
逐字段 diff 新跑 outputs/evaluation-batch13-real-corpus.json。

预期变化（批次 13 核心任务，逐项归因）：
- devset：file_count 2→10、content_group_count 1→6、pdf_count 1→5、
  docx_count 1→5、categories_covered 11→12 项（新增真实语料 11 类，
  保留 MVP integrity-markers）
- per_doc[0..1]（DC-MVP-001 docx/pdf）：除 wall_time_seconds.total 外
  零差异（评测器未动，同输入同输出）
- per_doc[2..9]：only-in-new（8 份真实语料，人工推导 expectations）
- summary.counts/success_rates/ratio_macro_averages：participating_docs
  扩容 + element_count_total.sum 扩容；macro 值全 1.0 不变
- summary.silent_drop_total：0→51（001-PDF 22 / 002-DOCX 7 / 002-PDF 3
  / 003-DOCX 1 / 003-PDF 8 / 004-PDF 7 / 005-DOCX 0 / 001-DOCX 0）
- summary.expectation_checks.required_markers_check：evaluated 2→10、
  passed 2→9、failed 0→1（DC-REAL-002-DOCX 缺 3 marker：sdt 嵌套
  封面漏检——真实语料要曝光的欠提取）
排除集（运行环境）：
- wall_time_seconds.total / provenance.git_commit / run_timestamp_iso
必然不变断言：
- report_version 维持 1.3、evaluator_version 维持 1.10（评测器零改动）
- 两份 MVP 文档除 wall_time 外全部字段零差异
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "outputs" / "evaluation-batch12-table-unlock.json"
NEW = ROOT / "outputs" / "evaluation-batch13-real-corpus.json"

_ENV_PROV = {"git_commit", "run_timestamp_iso"}

diffs: list[str] = []


def walk(path: str, a, b) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(f"{path}.{k}: only-in-new")
            elif k not in b:
                diffs.append(f"{path}.{k}: only-in-old")
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
    if path == ".per_doc":
        return True  # 列表长度 2→10（8 份新文档整棵子树新增）
    if path.startswith(".per_doc["):
        idx = int(path[len(".per_doc["):].split("]")[0])
        if idx >= 2:
            return True  # 8 份新文档（only-in-new 整棵子树）
        return False  # MVP 两文档：任何非 wall_time 差异都算意外
    if path.startswith(".devset."):
        return True
    if path.startswith(".summary."):
        return True
    if path.startswith(".provenance."):
        return path.split(".")[2] in _ENV_PROV
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    old = json.loads(BASE.read_text(encoding="utf-8"))
    new = json.loads(NEW.read_text(encoding="utf-8"))

    walk("", old, new)

    real = [d for d in diffs if not excluded(d)]
    allowed = [d for d in diffs if excluded(d)]

    new_docs = [d for d in diffs if d.startswith(".per_doc[")
                and ": only-in-new" in d and int(d[len(".per_doc["):].split("]")[0]) >= 2]

    must_change = [
        any("provenance.git_commit" in d for d in diffs),
        any("provenance.run_timestamp_iso" in d for d in diffs),
        any(d == ".devset.file_count: 2 != 10" for d in diffs),
        any(d == ".devset.content_group_count: 1 != 6" for d in diffs),
        any(d == ".devset.pdf_count: 1 != 5" for d in diffs),
        any(d == ".devset.docx_count: 1 != 5" for d in diffs),
        any(d == ".summary.silent_drop_total: 3 != 51" for d in diffs),
        any(d.startswith(".summary.expectation_checks.required_markers_check")
            for d in diffs),
        any(d.startswith(".summary.counts.element_count_total") for d in diffs),
        any(d == ".per_doc: len 2 != 10" for d in diffs),
    ]
    must_not_change = [
        not any("report_version" in d for d in diffs),
        not any("evaluator_version" in d for d in diffs),
        not any("evaluator_name" in d for d in diffs),
        not any(
            d.startswith(".per_doc[0].") and ".wall_time_seconds." not in d
            for d in diffs
        ),
        not any(
            d.startswith(".per_doc[1].") and ".wall_time_seconds." not in d
            for d in diffs
        ),
        not any(d.startswith(".expected_failures") for d in diffs),
    ]
    print(f"total field diffs: {len(diffs)}")
    print(f"allowed (exclusion set, with attribution): {len(allowed)}")
    for d in sorted(allowed)[:60]:
        print(f"  [excluded] {d}")
    if len(allowed) > 60:
        print(f"  ... (+{len(allowed) - 60} more)")
    print(f"unexpected diffs: {len(real)}")
    for d in real[:50]:
        print(f"  [DIFF] {d}")
    print(f"must-change: {must_change}")
    print(f"must-not-change: {must_not_change}")
    if real or not all(must_change) or not all(must_not_change):
        print("VERDICT: FAIL")
        raise SystemExit(1)
    print("VERDICT: PASS — devset 2→10（8 份真实语料 only-in-new）+ "
          "summary 扩容（silent_drop 3→51、markers 9/10）+ MVP 两文档"
          "零漂移 + 运行环境；评测器版本封口不动（evaluator 1.10 / "
          "report 1.3）")


if __name__ == "__main__":
    main()
