# -*- coding: utf-8 -*-
"""批次 13 冒烟对照：人工推导 expectations vs parser 实际输出。

数据源：
- 人工计数：samples/private/devset/manifest.json（Option 1 人工推导，
  worksheets 转录，不经 parser 反推）
- parser 输出：outputs/evaluation-batch13-real-corpus.json 的
  per_doc.metrics.element_count_by_type

输出：逐文档逐类型对照表（GT / actual / 差异% / 归因），差异 >50%
必须有归因（验收标准：差异 <50% 或已归因）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ATTRIBUTIONS: dict[tuple[str, str], str] = {
    ("DC-REAL-001-DOCX", "heading"): "parser +1：Subtitle 不在其标题判定集、"
    "2 个空标题段被计入（口径差，非欠提取）",
    ("DC-REAL-001-PDF", "heading"): "欠提取 32%：10-11pt 细粒度层级（24+27 个）"
    "大半漏检；多行标题垂直合并缺失",
    ("DC-REAL-001-PDF", "table"): "过度提取 3：Requirements 条款布局被误判为表",
    ("DC-REAL-002-DOCX", "heading"): "欠提取 5：封面嵌套 w:sdt，body 顶层遍历漏",
    ("DC-REAL-002-DOCX", "image"): "欠提取 2（100%）：同 sdt 嵌套漏检",
    ("DC-REAL-002-PDF", "heading"): "过度提取 3.5x：表单字段标签/框标签误判为标题",
    ("DC-REAL-002-PDF", "image"): "欠提取 3（60%）：矢量 logo/装饰条不产 raster",
    ("DC-REAL-003-DOCX", "heading"): "欠提取 1：Subtitle 不在标题判定集（同 001）",
    ("DC-REAL-003-PDF", "heading"): "过度提取 5：callout 框标题计入",
    ("DC-REAL-003-PDF", "image"): "欠提取 8（89%）：矢量插图不产 raster 对象",
    ("DC-REAL-004-PDF", "heading"): "欠提取 3（50%）：双栏同基线行交错",
    ("DC-REAL-004-PDF", "table"): "过度提取 1：无边框公式组误判为表",
    ("DC-REAL-004-PDF", "image"): "欠提取 1（50%）：矢量图不产 raster",
    ("DC-REAL-004-PDF", "caption"): "欠提取 3（100%）：题注文字被打散成单字符碎片",
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    manifest = json.loads(
        (ROOT / "samples/private/devset/manifest.json").read_text(encoding="utf-8"))
    report = json.loads(
        (ROOT / "outputs/evaluation-batch13-real-corpus.json").read_text(
            encoding="utf-8"))

    gt = {d["doc_id"]: d.get("expectations", {}).get("element_count_by_type", {})
          for d in manifest["documents"]}
    actual = {d["doc_id"]: (d.get("metrics", {}).get("element_count_by_type")
                            or {}).get("value", {})
              for d in report["per_doc"]}

    print(f"{'doc_id':<18} {'type':<9} {'GT':>4} {'parser':>7} {'diff%':>8}"
          f"  归因")
    unattributed: list[str] = []
    for doc_id in gt:
        for t in ("heading", "table", "image", "caption"):
            g = gt[doc_id].get(t, 0)
            a = actual[doc_id].get(t, 0)
            if g == 0:
                diff = 0.0 if a == 0 else float("inf")
            else:
                diff = (a - g) / g * 100
            flag = ""
            if abs(diff) > 50 or diff == float("inf"):
                attr = ATTRIBUTIONS.get((doc_id, t))
                if attr is None and a != g:
                    unattributed.append(f"{doc_id}/{t}")
                    attr = "!! 未归因"
                elif attr is None:
                    attr = "（GT=0 侧多项）"
                flag = f"→ {attr}"
            print(f"{doc_id:<18} {t:<9} {g:>4} {a:>7} {diff:>7.0f}%  {flag}")
    print()
    if unattributed:
        print(f"FAIL: {len(unattributed)} 项 >50% 差异未归因: {unattributed}")
        raise SystemExit(1)
    print("VERDICT: PASS — 全部 >50% 差异均已归因（worksheets 复核备注"
          "含完整推导）")


if __name__ == "__main__":
    main()
