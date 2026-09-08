# -*- coding: utf-8 -*-
"""Stage 9 批次 26：linked_nontext 施加工具（七轮裁决 B1/B2 配套）。

用途：把人工判读的关联边表（links 文件）施加到标注 JSON——**只改
linked_nontext 字段**，其余一律不动（B2 硬边界：relation 标注与原
segmentation 修订严格分流，本工具机械拒绝任何越界改动）。施加后就地
校验，失败不写盘。

links 文件格式（Python，exec 执行；判读记录本身是标注产物，存
samples/private 层，gitignored，永不进 git）：

    LINKS = {
        "u0032": ["img:fig-join-flow"],   # text unit → 其锚定的 ref 列表
        "u0007": [],                      # 空表 = 移除该 unit 的字段
    }

判读纪律（gold independence，七轮裁决 B1 追认强化）：正则/检索脚本
只能产生候选；每条边必须人工对照 PDF 核对；禁止读取本系统 parser 的
relations；禁止按当前系统预测结果决定加/删边；禁止为提高未来关联
指标调整 gold 范围。

用法（项目 venv python）：
  python scripts/stage9_link_apply.py \
      --manifest samples/private/stage9-corpus/manifest.json \
      --annotation samples/private/stage9-corpus/annotations/<doc_id>.json \
      --links samples/private/stage9-corpus/annotations/links_<doc>.py

--replace（九轮 C 非阻塞维护建议，默认关闭）：全量替换语义——LINKS
视为该文档 linked_nontext 的完整目标状态，表外 text unit 残留的边
（stale edge）一并清除并在 stderr 逐 id 报告。默认模式仅覆盖表内
unit，但检测到表外带边 unit 时在 stderr 提示（不改动、不影响退出
码）——两种模式下 B2 硬边界守卫与施加后校验均不变。

退出码：0 成功写盘；1 施加后校验失败（不写盘）；2 输入/越界错误。
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.validation import load_json, validate_annotation  # noqa: E402


def strip_links(data):
    """返回剥离全部 linked_nontext 后的深拷贝（B2 边界守卫用）。"""
    out = copy.deepcopy(data)
    for u in out.get("units", []):
        if isinstance(u, dict):
            u.pop("linked_nontext", None)
    return out


def load_links(path):
    ns = {}
    exec(compile(Path(path).read_text(encoding="utf-8"),
                 str(path), "exec"), ns)
    links = ns.get("LINKS")
    if not isinstance(links, dict):
        raise ValueError("links 文件须定义 LINKS 字典（unit_id -> [ref,...]）")
    for uid, refs in links.items():
        if not isinstance(uid, str) or not isinstance(refs, list) \
                or not all(isinstance(r, str) for r in refs):
            raise ValueError("LINKS 须为 unit_id(str) -> [ref(str), ...]")
    return links


def serialize(data, raw_original):
    """按原文件风格序列化（保持 CRLF/LF 与结尾换行有无，diff 最小）。"""
    text = json.dumps(data, ensure_ascii=False, indent=1)
    crlf = b"\r\n" in raw_original
    if crlf:
        text = text.replace("\n", "\r\n")
    if raw_original.endswith((b"\n", b"\r")):
        text += "\r\n" if crlf else "\n"
    return text.encode("utf-8")


def main(argv=None):
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(
        description="linked_nontext 施加（只改关联字段，越界拒绝）")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--annotation", required=True)
    parser.add_argument("--links", required=True,
                        help="links 文件（定义 LINKS 字典的 Python 文件）")
    parser.add_argument("--replace", action="store_true",
                        help="全量替换语义：LINKS 视为该文档关联边的完整"
                             "目标状态，表外 text unit 的 linked_nontext "
                             "一并清除（防 stale edge；默认仅覆盖表内 unit）")
    args = parser.parse_args(argv)

    try:
        manifest_data = load_json(args.manifest)
        raw = Path(args.annotation).read_bytes()
        ann = json.loads(raw.decode("utf-8"))
        links = load_links(args.links)
    except (OSError, json.JSONDecodeError, ValueError,
            UnicodeDecodeError, SyntaxError) as exc:
        print("输入错误: %s" % exc, file=sys.stderr)
        return 2

    manifest_index = {d.get("doc_id"): d
                      for d in manifest_data.get("docs", [])
                      if isinstance(d, dict)}
    by_id = {u.get("unit_id"): u for u in ann.get("units", [])
             if isinstance(u, dict) and isinstance(u.get("unit_id"), str)}

    for uid, _refs in links.items():
        u = by_id.get(uid)
        if u is None:
            print("输入错误: LINKS 引用不存在的 unit_id=%s" % uid,
                  file=sys.stderr)
            return 2
        if u.get("kind") == "nontext":
            print("输入错误: %s 是 nontext unit——linked_nontext 是 "
                  "text→nontext 边" % uid, file=sys.stderr)
            return 2

    new_ann = copy.deepcopy(ann)
    applied = 0
    pruned = []
    for u in new_ann.get("units", []):
        uid = u.get("unit_id")
        if uid in links:
            refs = links[uid]
            if refs:
                u["linked_nontext"] = list(refs)
            else:
                u.pop("linked_nontext", None)
            applied += 1
        elif args.replace and u.get("kind") != "nontext" \
                and u.get("linked_nontext"):
            pruned.append(uid)
            u.pop("linked_nontext", None)
    if applied != len(links):
        print("输入错误: LINKS 含未匹配 unit_id", file=sys.stderr)
        return 2
    if pruned:
        print("--replace：清除 %d 个表外 unit 的 stale 边: %s"
              % (len(pruned), ",".join(pruned[:20])
                 + ("..." if len(pruned) > 20 else "")), file=sys.stderr)
    if not args.replace:
        stale = [u.get("unit_id") for u in ann.get("units", [])
                 if isinstance(u, dict) and u.get("kind") != "nontext"
                 and u.get("linked_nontext")
                 and u.get("unit_id") not in links]
        if stale:
            print("stale 提示（未改动）: %d 个 unit 带边但不在 LINKS 表: "
                  "%s —— 如需清除请用 --replace" % (
                      len(stale), ",".join(stale[:20])
                      + ("..." if len(stale) > 20 else "")),
                  file=sys.stderr)

    if strip_links(new_ann) != strip_links(ann):
        print("越界改动：施加结果除 linked_nontext 外存在差异——拒绝写盘",
              file=sys.stderr)
        return 2

    doc_id, fails = validate_annotation(new_ann, manifest_index)
    if fails:
        for fail in fails:
            print("[%s] %s: %s" % (fail.code, doc_id, fail.detail),
                  file=sys.stderr)
        print("施加后校验失败（%d 项）——未写盘" % len(fails),
              file=sys.stderr)
        return 1

    Path(args.annotation).write_bytes(serialize(new_ann, raw))
    print("已施加 %d 个 unit 的关联边（%d 条）%s→ %s"
          % (applied, sum(len(v) for v in links.values()),
             ("+ 清除 %d 个 stale 边 unit " % len(pruned)
              if args.replace else ""), args.annotation))
    return 0


if __name__ == "__main__":
    sys.exit(main())
