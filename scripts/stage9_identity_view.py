# -*- coding: utf-8 -*-
"""Stage 9 批次 26：identity resolution 辅助工具（裁决 B'/B'' 配套）。

只读辅助脚本，不改 stage9/agreement.py 语义（七项禁改清单零接触）：
当正式 agreement 报告 decision=indeterminate（区间跨 0.85）时，
按盲态纪律对跨线歧义组做 identity resolution——解析者只看 PDF 页面
+双方标注的结构位置，对 gold_segment 与得分盲态。

两个子命令：

  plan（操作员视图，可见全量数值；--json 机器可读）
    列出未消解且贡献区间 gap>0 的歧义组（含贡献区间/gap/matched/
    双方成员数），并按整数比较复算"单独消解该组即可定判"标志：
    alone_pass（该组取上界贡献即整篇 pass）/ alone_below（取下界
    贡献即整篇 below_threshold），供操作员选定应交解析的跨线组。

  blind（解析者视图，盲态纪律工具化）
    对选定组只输出：家族+物理页（对照 PDF 该页图形位置）、双方
    unit_id（阅读序）、各自前后相邻的文本单元内容（结构位置证据）、
    需配对数 matched（presence 信息，填合法 pair map 所必需）。
    **不输出 gold_segment_id、一致率、贡献区间、判定**——解析者
    对 gold 与得分盲态。--skeleton 生成待填 pair map 骨架
    （{"家族|页": []}，填入恰 matched 对 [a_unit_id, b_unit_id]，
    单射、仅用组内 unit_id）。

  --pair-map（两子命令通用）：代入已填 pair map 后计算剩余未消解
  组，支持多轮迭代（骨架逐组补齐，最终一次代入
  scripts/stage9_agreement.py --pair-map 得确定一致率）。

用法（项目 venv python）：
  python scripts/stage9_identity_view.py plan --a A.json --b B.json [--json]
  python scripts/stage9_identity_view.py blind --a A.json --b B.json \
      [--groups img|1,img|2] [--skeleton pairmap_skeleton.json] [--out view.txt]

  默认 blind 组 = 全部未消解且 gap>0 的歧义组；--groups 显式指定
  （格式同 pair map 键 "家族|页"，页为空显示 None）。

退出码：0 正常（含无待消解组）；2 输入/IO 错误（含 doc_id 不一致、
组名不存在、组已消解、pair map 非法）。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.agreement import (  # noqa: E402
    THRESHOLD_DEN,
    THRESHOLD_NUM,
    AgreementInputError,
    compute_agreement,
)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _group_label(g):
    return "%s|%s" % (g["group"][0], g["group"][1])


def _parse_group_names(raw):
    names = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        family, _, page = part.partition("|")
        names.append((family, None if page in ("", "None") else page,
                      part))
    return names


def _open_groups(report):
    """未消解且贡献区间 gap>0 的歧义组（有真实配对自由度者）。"""
    out = []
    for g in report["ambiguous_groups"]:
        if (not g["resolved"]
                and g["contribution_upper"] > g["contribution_lower"]):
            out.append(g)
    return out


def _alone_flags(report, g):
    """整数比较复算：单独消解该组（其余组仍按区间取界）能否定判。"""
    lo, hi = g["contribution_lower"], g["contribution_upper"]
    base_lower, base_upper = report["agree_lower"], report["agree_upper"]
    union = report["union"]
    alone_pass = THRESHOLD_DEN * (base_lower - lo + hi) \
        >= THRESHOLD_NUM * union
    alone_below = THRESHOLD_DEN * (base_upper - hi + lo) \
        < THRESHOLD_NUM * union
    return alone_pass, alone_below


def _units_by_id(ann):
    return {u["unit_id"]: (i, u) for i, u in enumerate(ann["units"])}


def _neighbor_preview(ann, index, direction):
    """阅读序上最近的文本单元内容（结构位置证据；不含 gold 信息）。"""
    step = -1 if direction < 0 else 1
    j = index + step
    while 0 <= j < len(ann["units"]):
        u = ann["units"][j]
        if u["kind"] != "nontext":
            text = ann["stream"][u["char_span"][0]:u["char_span"][1]]
            return text.strip()[:40]
        j += step
    return None


def _render_blind(doc_id, report, groups, ann_a, ann_b, skeleton_path):
    lines = []
    lines.append("doc_id: %s（identity resolution 解析者视图——盲态："
                 "不含 gold_segment 与任何得分）" % doc_id)
    lines.append("待消解组 %d 个。请对照 PDF 对应物理页的图形位置，"
                 "判定两侧哪些 unit_id 是同一视觉语义对象。" % len(groups))
    skeleton = {}
    for g in groups:
        label = _group_label(g)
        family, page = g["group"]
        lines.append("")
        lines.append("组 %s（家族 %s，物理页 %s）" % (label, family, page))
        lines.append("  需确定 %d 对一一对应（matched=%d；A 侧 %d 个、"
                     "B 侧 %d 个对象）"
                     % (g["matched"], g["matched"], g["side_a"],
                        g["side_b"]))
        for side, ann, ids in (("A", ann_a, g["a_unit_ids"]),
                               ("B", ann_b, g["b_unit_ids"])):
            lines.append("  %s 侧（阅读序）:" % side)
            by_id = _units_by_id(ann)
            for uid in ids:
                idx, _u = by_id[uid]
                prev = _neighbor_preview(ann, idx, -1)
                nxt = _neighbor_preview(ann, idx, +1)
                lines.append("    %s  前文:%r  后文:%r"
                             % (uid,
                                prev if prev is not None else "（无）",
                                nxt if nxt is not None else "（无）"))
        lines.append("  填写：pair map %r 为恰 %d 对 [A unit_id, B "
                     "unit_id]（单射、仅用上列 unit_id）"
                     % (label, g["matched"]))
        skeleton[label] = []
    if skeleton_path:
        Path(skeleton_path).write_text(
            json.dumps(skeleton, ensure_ascii=False, indent=1),
            encoding="utf-8")
        lines.append("")
        lines.append("骨架已写 %s（各键填满后经 "
                     "scripts/stage9_agreement.py --pair-map 代入）"
                     % skeleton_path)
    return "\n".join(lines)


def main(argv=None):
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(
        description="identity resolution 辅助（plan=操作员视图 / "
                    "blind=解析者盲态视图；只读，不改 agreement 语义）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--a", required=True, help="第一份标注 JSON")
        p.add_argument("--b", required=True, help="第二份标注 JSON")
        p.add_argument("--pair-map",
                       help="已填 pair map JSON（迭代：显示剩余未消解组）")

    p_plan = sub.add_parser("plan", help="操作员视图（全量数值）")
    common(p_plan)
    p_plan.add_argument("--json", action="store_true",
                        help="机器可读 JSON 输出")

    p_blind = sub.add_parser("blind", help="解析者盲态视图")
    common(p_blind)
    p_blind.add_argument("--groups",
                         help="逗号分隔组名（家族|页），默认全部未消解"
                              "gap>0 组")
    p_blind.add_argument("--skeleton", help="待填 pair map 骨架输出路径")
    p_blind.add_argument("--out", help="视图写入文件（默认 stdout）")

    args = parser.parse_args(argv)

    try:
        ann_a = _load(args.a)
        ann_b = _load(args.b)
        pair_map = None
        pair_map_sha = None
        if args.pair_map:
            raw = Path(args.pair_map).read_bytes()
            pair_map_sha = hashlib.sha256(raw).hexdigest()
            pair_map = json.loads(raw.decode("utf-8"))
        report = compute_agreement(ann_a, ann_b, pair_map=pair_map,
                                   pair_map_sha256=pair_map_sha)
    except (OSError, json.JSONDecodeError, AgreementInputError,
            KeyError, TypeError, IndexError, ValueError) as exc:
        print("输入错误: %s" % exc, file=sys.stderr)
        return 2

    resolved = [g for g in report["ambiguous_groups"] if g["resolved"]]
    if args.cmd == "plan":
        rows = []
        for g in _open_groups(report):
            alone_pass, alone_below = _alone_flags(report, g)
            rows.append({
                "group": _group_label(g),
                "side_a": g["side_a"],
                "side_b": g["side_b"],
                "matched": g["matched"],
                "contribution_lower": g["contribution_lower"],
                "contribution_upper": g["contribution_upper"],
                "gap": g["contribution_upper"] - g["contribution_lower"],
                "alone_pass": alone_pass,
                "alone_below": alone_below,
            })
        rows.sort(key=lambda r: (not (r["alone_pass"] or r["alone_below"]),
                                 -r["gap"], r["group"]))
        if args.json:
            payload = {
                "tool": "stage9_identity_view.plan",
                "doc_id": report["doc_id"],
                "decision": report["decision"],
                "agree_lower": report["agree_lower"],
                "agree_upper": report["agree_upper"],
                "union": report["union"],
                "threshold_rational": [THRESHOLD_NUM, THRESHOLD_DEN],
                "open_group_count": len(rows),
                "resolved_group_count": len(resolved),
                "groups": rows,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=1))
        else:
            print("doc_id: %s decision=%s 区间计数 [%d, %d] / union %d"
                  % (report["doc_id"], report["decision"],
                     report["agree_lower"], report["agree_upper"],
                     report["union"]))
            print("未消解 gap>0 组 %d 个（已消解 %d 个）"
                  % (len(rows), len(resolved)))
            if report["decision"] != "indeterminate" and rows:
                print("注：整篇判定已定（不跨线），无需 identity "
                      "resolution；以下仅供诊断。")
            for r in rows:
                flag = []
                if r["alone_pass"]:
                    flag.append("alone=pass")
                if r["alone_below"]:
                    flag.append("alone=below")
                print("  %s a=%d b=%d matched=%d 贡献=[%d,%d] gap=%d %s"
                      % (r["group"], r["side_a"], r["side_b"],
                         r["matched"], r["contribution_lower"],
                         r["contribution_upper"], r["gap"],
                         " ".join(flag) if flag else "-"))
        return 0

    # blind：解析者视图
    by_label = {_group_label(g): g
                for g in report["ambiguous_groups"]}
    if args.groups:
        selected = []
        for family, page, raw in _parse_group_names(args.groups):
            label = "%s|%s" % (family, page)
            g = by_label.get(label)
            if g is None:
                print("输入错误: 组不存在: %s（存在: %s）"
                      % (raw, ", ".join(sorted(by_label)) or "无"),
                      file=sys.stderr)
                return 2
            if g["resolved"]:
                print("输入错误: 组已消解: %s" % label, file=sys.stderr)
                return 2
            if g["contribution_upper"] > g["contribution_lower"]:
                selected.append(g)
            else:
                print("注: 组 %s 区间退化（gap=0），无需消解，已跳过"
                      % label, file=sys.stderr)
    else:
        selected = _open_groups(report)
    text = _render_blind(report["doc_id"], report, selected,
                         ann_a, ann_b, args.skeleton)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print("解析者视图已写 %s（%d 组）" % (args.out, len(selected)))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
