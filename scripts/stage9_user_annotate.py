# -*- coding: utf-8 -*-
"""Stage 9 批次 26：第二标注人（用户独立复核）辅助工具（指南 §7.1）。

零判断原则：本工具只做机械工作（逐行抽取、fold-ws-v1 规范化、冻结 v1
切分、span 平铺、hash 计算、schema 组装）；一切标注判断（哪些行入流、
heading/句子分类、语义段分组、排除项、图/表登记）全部由 blocks 文件
中用户的判断表达。工具不读、不显示、不依赖第一标注人（Claude 草案）
的任何产物。

两个子命令（项目 venv python 运行，均以 --doc 指定 doc_id）：

  dump     逐页列出全部文本行（稳定 ID：pNNN + 列标记 L/R/C + 行号）、
           图片、find_tables 检测提示 → 供用户逐行挑块：
    python scripts/stage9_user_annotate.py dump --doc tech-08-cnnic57
    （默认写 outputs/userannot_<短名>_dump.txt；--stdout 直接打印）

  assemble 按用户 blocks 文件组装 v1.1 标注 JSON 并就地校验：
    python scripts/stage9_user_annotate.py assemble \
        --doc tech-08-cnnic57 \
        --blocks samples/private/stage9-corpus/annotations-user/blocks_tech-08.py \
        --dump outputs/userannot_tech-08_dump.txt
    （默认写 annotations-user/<doc_id>.json；--dump 传 dump 输出文件以
    核对行注册表指纹未漂移）

行注册表（dump 与 assemble 同源，保证 ID 稳定；与第一标注人 builder 的
crop 方案同源）：
  (p,"L",i)/(p,"R",i)  左/右半栏行（页面中线裁剪后 extract_text_lines，
                       仅非空行，0 基连续编号）。双栏文档分栏干净——全页
                       extract_text_lines 会把基线对齐的左右行融合成一行，
                       不可用；单栏文档的宽行左半落 L、右半落 R。
  (p,"C",k)            全页 extract_text_lines 中横跨中线的整行（题名/
                       整宽题注/跨栏表格行/单栏宽行），0 基连续编号。
  ≈Liii+Rjjj 标记：该 C 行与两个半行是同一视觉行（top 差 <3 且左半+
  右半 ≈ 整行，容差同 builder）。引用该 C 键即自动消费其两个半行；
  再单独引用其中半行 = 同一视觉行重复计数，assemble 报错。
fingerprint = 全部注册行文本+键序的 sha256（dump/assemble 漂移核对）。

blocks 文件格式（Python，exec 执行；工具注入 P 辅助函数）：

  ANNOTATOR = "user-independent（自署）"
  NOTES = "处理口径说明（页眉页脚/表格单元格/图内标签如何处理）"
  SEGMENTS = [("g00", "封面+摘要", "frontmatter"), ("g01", "§1 引言", "body")]
  EXCLUDE = set(P(1,"L",3,5))           # 可选：明确排除的行（安全网）
  BLOCKS = [
      (P(1,"C",0),     "heading", "g00", True),  # 跨中线标题=1 heading
      (P(1,"L",9,27),  "para",    "g00", False), # 段落=冻结 v1 切句
      (P(1,"L",28),    "lines",   "g00", False), # 每行 1 sentence unit
      (1,              "nontext", "g01", "img:fig-1"),  # 页 1 图标记
      (1,              "nontext", "g02", "tab:1"),      # 页 1 表标记
      (P(2,"L",5,60),  "entries", "g08", False, re.compile(r"^\\[\\d+\\]\\s*")),
                                        # 条目区（指南 §3.1）：编号行开
                                        # 新条目；折行并入同条目；条目内
                                        # 冻结 v1。无编号条目区第 5 元素
                                        # 改显式起点行号（块内 0-based）
  ]
  # P(page, col, a, b=None)：col=L/R/C；b 省略=单行，给出=闭区间 a..b。
  # BLOCKS 顺序=阅读序；nontext 首参=物理页码，ref 命名建议 img:fig-N /
  # tab:N（N=阅读序 1-based；agreement 按 家族+页+页内序 对齐，与命名无关）。
  # 参考文献区/作者块/版权块禁用 lines/整块 para，一律 entries（§3.1）。

机械规则与第一标注人 builder 完全同源：stream=fold_ws("\\n".join(块文本))；
heading 块整体一 unit；para 块 split_sentences(fold_ws(...))；lines 块每行
一 unit；entries 块先按条目边界分组再条目内 v1（unit 页码取起始源行页）；
span 平铺=unit_i 末=unit_{i+1} 首；hash/preview 取流切片。
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber

from stage9.entries import partition_entries
from stage9.normalize import fold_ws
from stage9.splitter import split_sentences
from stage9.validation import validate_annotation

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "samples" / "private" / "stage9-corpus" / "files"
ANNO_USER = (ROOT / "samples" / "private" / "stage9-corpus"
             / "annotations-user")

FROZEN_KEYS = {
    "annotation_schema": "v1.1",
    "sentence_splitter": "v1",
    "normalization": "fold-ws-v1",
}


def _sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _font_of(name):
    return name.split("+")[-1] if name else "?"


def _fuzzy_join_match(a, b, c):
    """整行 c 是否 ≈ 左半 a + 右半 b（同 builder 容差：跨界重叠 ≤8 字符，
    或左右各删 ≤2 字符的连字符断词）。"""
    for k in range(0, 9):
        if a + b[k:] == c or a[:len(a) - k or None] + b == c:
            return True
    for kl in range(0, 3):
        for kr in range(0, 3):
            aa = a[:len(a) - kl or None] if kl else a
            bb = b[kr:] if kr else b
            if aa + bb == c:
                return True
    return False


def _norm(s):
    return "".join(s.split())


def load_registry(doc_id):
    """逐页行注册表（dump 与 assemble 共用，保证 ID 稳定）。

    返回 (reg, reg_meta, fingerprint, pages_meta, matched_halves)：
    - reg[(p,col,i)] = 行文本；reg_meta 同键 = x0/top/字号/字体众数
    - matched_halves[(p,"C",k)] = ((p,"L",li), (p,"R",ri))
    - pages_meta[p] = {"L","R","C": 行数, "imgs": [(top,x0,x1)],
      "ftabs": [bbox]}
    """
    reg = {}
    reg_meta = {}
    matched_halves = {}
    fp_parts = []
    pages_meta = {}
    src = FILES / (doc_id + ".pdf")
    if not src.is_file():
        raise SystemExit("源文件不存在: %s" % src)
    with pdfplumber.open(src) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            mid = page.width / 2
            halves = {}
            for col, box in (("L", (0, 0, mid, page.height)),
                             ("R", (mid, 0, page.width, page.height))):
                crop = page.crop(box)
                lines = [ln for ln in crop.extract_text_lines()
                         if ln["text"].strip()]
                halves[col] = lines
                for i, ln in enumerate(lines):
                    key = (pno, col, i)
                    reg[key] = ln["text"].strip()
                    sz, fn = line_meta(crop, ln)
                    reg_meta[key] = {"x0": ln["x0"], "top": ln["top"],
                                     "sz": sz, "fn": fn}
                    fp_parts.append("%d:%s:%d:%s" % (pno, col, i, reg[key]))
            nc = 0
            for ln in page.extract_text_lines():
                if not (ln["x0"] < mid < ln["x1"]):
                    continue
                txt = ln["text"].strip()
                if not txt:
                    continue
                key = (pno, "C", nc)
                nc += 1
                reg[key] = txt
                sz, fn = line_meta(page, ln)
                reg_meta[key] = {"x0": ln["x0"], "top": ln["top"],
                                 "sz": sz, "fn": fn}
                fp_parts.append("%d:C:%d:%s" % (pno, key[2], txt))
                li = ri = None
                for i, hl in enumerate(halves["L"]):
                    if abs(hl["top"] - ln["top"]) < 3:
                        li = i
                        break
                for j, hr in enumerate(halves["R"]):
                    if abs(hr["top"] - ln["top"]) < 3:
                        ri = j
                        break
                if li is not None and ri is not None \
                        and _fuzzy_join_match(
                            _norm(halves["L"][li]["text"]),
                            _norm(halves["R"][ri]["text"]), _norm(txt)):
                    matched_halves[key] = ((pno, "L", li), (pno, "R", ri))
            pages_meta[pno] = {
                "L": len(halves["L"]), "R": len(halves["R"]), "C": nc,
                "imgs": [(im["top"], im["x0"], im["x1"])
                         for im in page.images],
                "ftabs": [tuple(tab.bbox) for tab in page.find_tables()],
            }
    fingerprint = hashlib.sha256(
        "\n".join(fp_parts).encode("utf-8")).hexdigest()
    return reg, reg_meta, fingerprint, pages_meta, matched_halves


def line_meta(page, ln):
    """行的字号/字体众数（辅助识别标题，机械统计）。page 可为 crop。"""
    win = [c for c in page.chars
           if ln["top"] - 1.5 <= c["top"] <= ln["bottom"] + 1.5
           and c["x0"] >= ln["x0"] - 1 and c["x1"] <= ln["x1"] + 1]
    if not win:
        return 0.0, "?"
    sz = collections.Counter(round(c["size"], 1) for c in win)
    fn = collections.Counter(_font_of(c["fontname"]) for c in win)
    return sz.most_common(1)[0][0], fn.most_common(1)[0][0]


def cmd_dump(args):
    doc_id = args.doc
    reg, reg_meta, fingerprint, pages_meta, matched_halves = load_registry(
        doc_id)
    half_of_c = {}
    for ckey, (lk, rk) in matched_halves.items():
        half_of_c[lk] = ckey
        half_of_c[rk] = ckey
    out = []
    out.append("# doc=%s  行注册表指纹=%s" % (doc_id, fingerprint))
    out.append("# 键=pNNN 列 行号：L/R=左/右半栏行（中线裁剪，0 基连续）；"
               "C=跨中线整行（0 基连续）")
    out.append("# 单栏宽行同时以 L半+R半+C整行 出现：引用 C 键即自动消费其"
               "两个半行（标 ≈Ckkk 的半行勿单独引用）")
    out.append("# C 行标 ≈Liii+Rjjj = 与两半行同一视觉行；未标 = 无匹配半行"
               "（如表格行/断词失败），引用 C 后其半行需自行 EXCLUDE 或引用")
    out.append("# IMG=页内图片；FTAB=pdfplumber find_tables 检测提示（可能"
               "假阳性，是否登记 tab: 与是否排除其单元格行由标注人判）")
    for pno in sorted(pages_meta):
        meta = pages_meta[pno]
        out.append("")
        out.append("== p%03d  L%d R%d C%d 图%d 表检测%d ==" % (
            pno, meta["L"], meta["R"], meta["C"],
            len(meta["imgs"]), len(meta["ftabs"])))
        for col, label in (("L", "左半"), ("R", "右半")):
            if not meta[col]:
                continue
            out.append("-- %s栏 --" % label)
            for i in range(meta[col]):
                key = (pno, col, i)
                m = reg_meta[key]
                tag = "  ≈C%03d" % half_of_c[key][2] if key in half_of_c \
                    else ""
                out.append("[p%03d %s%03d] x0=%6.1f sz=%4.1f %-12s%s %r" % (
                    pno, col, i, m["x0"], m["sz"], m["fn"], tag, reg[key]))
        if meta["C"]:
            out.append("-- 跨中线整行（C）--")
            for i in range(meta["C"]):
                key = (pno, "C", i)
                m = reg_meta[key]
                pair = matched_halves.get(key)
                tag = "  ≈L%03d+R%03d" % (pair[0][2], pair[1][2]) \
                    if pair else ""
                out.append("[p%03d C%03d] x0=%6.1f sz=%4.1f %-12s%s %r" % (
                    pno, i, m["x0"], m["sz"], m["fn"], tag, reg[key]))
        for k, im in enumerate(meta["imgs"]):
            out.append("[p%03d IMG%d] top=%6.1f (x0=%6.1f x1=%6.1f)"
                       % (pno, k, im[0], im[1], im[2]))
        for k, bb in enumerate(meta["ftabs"]):
            out.append("[p%03d FTAB%d] bbox=(%.1f, %.1f, %.1f, %.1f)"
                       % (pno, k, *bb))
    text = "\n".join(out) + "\n"
    if args.stdout:
        print(text)
    else:
        short = doc_id.split("-")[0] + "-" + doc_id.split("-")[1]
        dst = ROOT / "outputs" / ("userannot_%s_dump.txt" % short)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        print("wrote %s（%d 行，指纹 %s…）" % (dst, len(out), fingerprint[:16]))
    return 0


def _keys(page, col, a, b=None):
    if b is None:
        return ((page, col, a),)
    return tuple((page, col, i) for i in range(a, b + 1))


def build_annotation(blocks_env, reg):
    """blocks_env = exec 后的 blocks 文件全局字典 → (v1.1 标注 dict, seg_ids)。"""
    blocks = blocks_env["BLOCKS"]
    segments = blocks_env["SEGMENTS"]
    seg_ids = [s[0] for s in segments]

    stream = fold_ws("\n".join(
        "\n".join(reg[k] for k in b[0])
        for b in blocks if b[1] != "nontext"))

    units = []
    cursor = 0

    def add_text(page, kind, seg, hard, text):
        nonlocal cursor
        folded = fold_ws(text)
        pos = stream.find(folded, cursor)
        assert pos >= 0, (page, kind, text[:50])
        cursor = pos + len(folded)
        units.append({
            "unit_id": "u%04d" % (len(units) + 1),
            "kind": kind, "page": page, "body_index": None,
            "char_span": [pos, cursor],
            "norm_text_hash": None, "text_preview": None,
            "nontext_ref": None,
            "gold_segment_id": seg, "hard_boundary_before": hard,
        })

    for b in blocks:
        if b[1] == "nontext":
            page, seg, ref = b[0], b[2], b[3]
            units.append({
                "unit_id": "u%04d" % (len(units) + 1),
                "kind": "nontext", "page": page, "body_index": None,
                "char_span": None, "norm_text_hash": None,
                "text_preview": None, "nontext_ref": ref,
                "gold_segment_id": seg, "hard_boundary_before": False,
            })
            continue
        keys, btype, seg, hard = b[0], b[1], b[2], b[3]
        page = keys[0][0]
        joined = "\n".join(reg[k] for k in keys)
        if btype == "heading":
            add_text(page, "heading", seg, hard, joined)
        elif btype == "lines":
            for k, key in enumerate(keys):
                add_text(page, "sentence", seg, hard and k == 0, reg[key])
        elif btype == "para":
            for s in split_sentences(fold_ws(joined)):
                add_text(page, "sentence", seg, False, s)
        elif btype == "entries":
            # §3.1 条目区：第 5 元素 = 条目边界判断（re.Pattern 或显式
            # 起点行号）。机械分组 + 条目内冻结 v1；unit 页码取其起始
            # 源行的页。首组首 unit 取块 hard，其后每组首 unit True。
            if len(b) < 5:
                raise SystemExit("entries 块缺第 5 元素（条目边界判断："
                                 "re.Pattern 或显式起点行号）")
            parts = [reg[k] for k in keys]
            try:
                groups = partition_entries(parts, b[4])
            except ValueError as e:
                raise SystemExit("entries 块（%s, %s…）边界判断错误："
                                 "%s" % (seg, keys[0], e))
            for gi, (_src_idx, eunits) in enumerate(groups):
                for ui, (text, line_idx) in enumerate(eunits):
                    add_text(keys[line_idx][0], "sentence", seg,
                             (hard if gi == 0 else True) and ui == 0,
                             text)
        else:
            raise SystemExit("未知块类型 %r（合法：heading/lines/para/"
                             "entries/nontext）" % (btype,))

    tidx = [i for i, u in enumerate(units)
            if u["kind"] in ("heading", "sentence")]
    for k, i in enumerate(tidx):
        u = units[i]
        u["char_span"][1] = (units[tidx[k + 1]]["char_span"][0]
                             if k + 1 < len(tidx) else len(stream))
        seg_text = stream[u["char_span"][0]:u["char_span"][1]]
        u["norm_text_hash"] = _sha(seg_text)
        u["text_preview"] = seg_text[:60]

    return {
        "doc_id": blocks_env.get("DOC"),
        "annotation_schema": FROZEN_KEYS["annotation_schema"],
        "sentence_splitter": FROZEN_KEYS["sentence_splitter"],
        "normalization": FROZEN_KEYS["normalization"],
        "annotator": blocks_env["ANNOTATOR"],
        "notes": blocks_env.get("NOTES", ""),
        "stream": stream,
        "units": units,
        "segments": [{"gold_segment_id": g, "hint": h, "kind": k}
                     for g, h, k in segments],
    }, seg_ids


def cmd_assemble(args):
    doc_id = args.doc
    reg, _reg_meta, fingerprint, _pages_meta, matched_halves = load_registry(
        doc_id)

    if args.dump:
        head = Path(args.dump).read_text(encoding="utf-8").splitlines()
        for line in head:
            if line.startswith("# doc=") and "指纹=" in line:
                dumped = line.split("指纹=")[1].strip()
                if dumped != fingerprint:
                    print("行注册表指纹漂移：dump=%s assemble=%s\n"
                          "（pdfplumber 版本变化或源文件变动——重新 dump "
                          "并核对已挑行号后再 assemble）"
                          % (dumped[:16], fingerprint[:16]), file=sys.stderr)
                    return 2
                print("指纹核对一致: %s…" % fingerprint[:16])
                break

    env = {"P": _keys, "__builtins__": __builtins__}
    exec(compile(Path(args.blocks).read_text(encoding="utf-8"),
                 args.blocks, "exec"), env)
    if env.get("DOC") and env["DOC"] != doc_id:
        print("blocks 文件 DOC=%r 与 --doc=%r 不符" % (env["DOC"], doc_id),
              file=sys.stderr)
        return 2
    env.setdefault("DOC", doc_id)

    explicit = set()
    for b in env["BLOCKS"]:
        if b[1] != "nontext":
            for key in b[0]:
                if key in explicit:
                    raise SystemExit("行被重复引用: %r" % (key,))
                if key not in reg:
                    raise SystemExit("行 ID 不在注册表: %r" % (key,))
                explicit.add(key)
    used = set(explicit)
    for ckey in sorted(explicit):
        if ckey[1] == "C" and ckey in matched_halves:
            for half in matched_halves[ckey]:
                if half in explicit:
                    raise SystemExit(
                        "同一视觉行重复引用：C 键 %r 已包含半行 %r（引用 C "
                        "即可，勿再单独引用其半行）" % (ckey, half))
                used.add(half)
    exclude = set(env.get("EXCLUDE") or ())
    unknown_excl = exclude - set(reg)
    if unknown_excl:
        raise SystemExit("EXCLUDE 含未知行 ID: %r" % (sorted(unknown_excl)[:5],))
    leftover = sorted(set(reg) - used - exclude)
    by_col = {"L": 0, "R": 0, "C": 0}
    for k in leftover:
        by_col[k[1]] += 1
    print("已用行 %d（显式 %d + C 自动消费半行 %d）/ 注册表 %d / 显式排除"
          " %d / 未处理 %d（L%d R%d C%d）%s" % (
              len(used), len(explicit), len(used) - len(explicit), len(reg),
              len(exclude), len(leftover), by_col["L"], by_col["R"],
              by_col["C"],
              "" if not leftover else "（如下，确认是否都该排除）"))
    for key in leftover[:30]:
        print("  未处理 %r %s" % (key, reg[key][:50]))

    ann, seg_ids = build_annotation(env, reg)

    manifest_path = (ROOT / "samples" / "private" / "stage9-corpus"
                     / "manifest.json")
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index = {d.get("doc_id"): d for d in manifest.get("docs", [])
                 if isinstance(d, dict)}
    else:
        index = None
    doc_id_out, fails = validate_annotation(ann, index)
    if fails:
        for fail in fails:
            print("[校验失败 %s] %s" % (fail.code, fail.detail))
        print("校验失败 %d 项——修正 blocks 后重试（未写盘）" % len(fails))
        return 1

    dst = Path(args.out) if args.out else ANNO_USER / (doc_id + ".json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(ann, fh, ensure_ascii=False, indent=1)
    n_text = sum(1 for u in ann["units"]
                 if u["kind"] in ("heading", "sentence"))
    n_nt = len(ann["units"]) - n_text
    hard = sum(1 for u in ann["units"] if u["hard_boundary_before"])
    print("wrote %s" % dst)
    print("stream %d chars / units %d（text %d + nontext %d）/ segments %d"
          " / hard %d——校验 0 失败" % (len(ann["stream"]), len(ann["units"]),
                                       n_text, n_nt, len(seg_ids), hard))
    return 0


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Stage 9 批次 26 第二标注人辅助工具（dump 摘行 / "
                    "assemble 组装+校验；零判断，机械同源 builder）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dump = sub.add_parser("dump", help="逐页行/图/表检测清单")
    p_dump.add_argument("--doc", required=True, help="doc_id（如 tech-08-cnnic57）")
    p_dump.add_argument("--stdout", action="store_true", help="打印而非写文件")

    p_asm = sub.add_parser("assemble", help="按 blocks 文件组装标注 JSON")
    p_asm.add_argument("--doc", required=True)
    p_asm.add_argument("--blocks", required=True, help="blocks Python 文件")
    p_asm.add_argument("--dump", help="dump 输出文件（核对行表指纹）")
    p_asm.add_argument("--out", help="输出 JSON 路径（默认 annotations-user/）")

    args = parser.parse_args(argv)
    return cmd_dump(args) if args.cmd == "dump" else cmd_assemble(args)


if __name__ == "__main__":
    sys.exit(main())
