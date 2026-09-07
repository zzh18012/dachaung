# -*- coding: utf-8 -*-
"""Stage 9 批次 26：标注人工抽查渲染工具（只读支撑）。

用途：指南 §7 用户抽查义务的支撑件——把标注 JSON 渲染为人类可读
视图（按 gold_segment 分组、逐 unit 列页码/kind/硬边界标记/完整
文本，页切换处插分隔线；nontext 显示 nontext_ref），供用户对照
PDF 原文抽查切分/段归属/图 表登记质量。工具只渲染标注内容，
不做任何判定，不改任何冻结物（与 identity_view 同类支撑件）。

用法（项目 venv python）：
  python scripts/stage9_annotation_report.py \
      --annotation samples/private/stage9-corpus/annotations/<doc_id>.json \
      [--out outputs/spotcheck_<doc_id>.txt]

默认打印到 stdout；--out 写 UTF-8 文件（推荐，长文档报告很大）。
退出码：0 正常；2 输入/IO 错误。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def render(ann, annotation_sha256):
    units = ann.get("units", [])
    segs = {s.get("gold_segment_id"): s for s in ann.get("segments", [])}
    n_text = sum(1 for u in units if u.get("kind") != "nontext")
    n_non = len(units) - n_text
    lines = []
    lines.append("doc_id: %s" % ann.get("doc_id"))
    lines.append("annotation_sha256=%s" % annotation_sha256)
    lines.append("annotator: %s | schema: %s | splitter: %s | "
                 "norm: %s" % (ann.get("annotator"),
                               ann.get("annotation_schema"),
                               ann.get("sentence_splitter"),
                               ann.get("normalization")))
    lines.append("stream: %d 字符 | units: %d（text %d + nontext %d）"
                 "| segments: %d" % (len(ann.get("stream", "")),
                                   len(units), n_text, n_non,
                                   len(segs)))
    lines.append("—— segments 一览 ——")
    seg_order = []
    for u in units:
        sid = u.get("gold_segment_id")
        if sid not in seg_order:
            seg_order.append(sid)
    for sid in seg_order:
        s = segs.get(sid, {})
        cnt = sum(1 for u in units if u.get("gold_segment_id") == sid)
        lines.append("  %s  %s（%s）× %d units"
                     % (sid, s.get("hint", ""), s.get("kind", ""),
                        cnt))
    lines.append("")
    lines.append("—— 阅读序明细（按 gold_segment 分组；◆=硬边界；"
                 "页切换处插分隔线）——")
    cur_seg = None
    cur_page = None
    for u in units:
        sid = u.get("gold_segment_id")
        if sid != cur_seg:
            cur_seg = sid
            s = segs.get(sid, {})
            lines.append("")
            lines.append("[segment %s  %s（%s）]"
                         % (sid, s.get("hint", ""), s.get("kind", "")))
        page = u.get("page")
        if page is not None and page != cur_page:
            cur_page = page
            lines.append("-- 第 %s 页 --" % page)
        hard = "◆ " if u.get("hard_boundary_before") else "  "
        if u.get("kind") == "nontext":
            lines.append("%s%s  nontext %s" % (hard, u.get("unit_id"),
                                               u.get("nontext_ref")))
        else:
            span = u.get("char_span") or [0, 0]
            text = ann.get("stream", "")[span[0]:span[1]].strip()
            if u.get("page") is not None:
                loc = "p%s" % u.get("page")
            else:
                loc = "b%s" % u.get("body_index")
            lines.append("%s%s %s %s %s"
                         % (hard, u.get("unit_id"), loc,
                            u.get("kind"), text))
    lines.append("")
    lines.append("（渲染工具：scripts/stage9_annotation_report.py；"
                 "仅呈现标注内容，判定以 validator/agreement 为准）")
    return "\n".join(lines)


def main(argv=None):
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(
        description="标注人工抽查渲染（只读支撑，不改判定）")
    parser.add_argument("--annotation", required=True,
                        help="标注 JSON 文件路径")
    parser.add_argument("--out", help="输出文件路径（默认 stdout）")
    args = parser.parse_args(argv)
    try:
        raw = Path(args.annotation).read_bytes()
        annotation_sha = hashlib.sha256(raw).hexdigest()
        ann = json.loads(raw.decode("utf-8"))
        text = render(ann, annotation_sha)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
            print("已写 %s（%d 行）" % (args.out, text.count("\n") + 1))
        else:
            print(text)
    except (OSError, json.JSONDecodeError, KeyError, TypeError,
            IndexError, ValueError) as exc:
        print("输入错误: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
