# -*- coding: utf-8 -*-
"""Stage 9 批次 26：双标注一致率（标注指南 §7 契约实现）。

比对口径：unit 级（切分一致 + gold_segment 一致）；
一致率 = 一致 unit 数 / 双方 unit 并集数；<0.85 且仲裁不收敛为停机
条件（脚本只报告阈值，是否停机由仲裁判定）。

对齐方法：同一文档的两份标注按人工阅读序各成一个 unit 序列，unit
对齐键 = 规范化文本（文本单元取 stream 上 char_span 的 strip 文本；
nontext 单元无文本，对齐键 = 家族(img/tab)+物理页（v3-page-family），
**与 nontext_ref 命名字符串无关**——跨标注人命名从未冻结，按字符串
对齐会因 img:fig-1 vs img:1 之类前缀差异系统性错配；也**不含任何按
标注自身 nontext 出现顺序的编号**——2026-09-07 裁决 B 硬约束：序号
须来自共同源注册表且不随任一方多登/漏登漂移，而机械注册表
（pdfplumber page.images / find_tables）经实证无法枚举语义图形
（tech-03 标注 241 图 vs 2308 个栅格、多页语义图 2 张而栅格 0 个、
FTAB 151 检测 vs 17 语义表），source ordinal 不可表达，故取消序号，
取零编号的最粗源稳定粒度=同页同族）。两序列经
difflib.SequenceMatcher(autojunk=False) 对齐——同文档同 splitter 冻结
规则下分歧局部化，序对齐即位置对应；重复文本（如告示框标签 "Note"
×269）依赖序列位置而非文本唯一性。对齐只认键（文本切分/非文本
页族），kind 与 gold_segment 在对齐对上另行比较。
粒度限制（披露）：同页同族多对象按结构位置配对，多登/漏登一对象
只影响该对象自身的并集计数（matched/union 精确不变），但页内族内
的语义配对可能置换，至多使 kind/seg 比较在置换对上错位——计量上
有界且方向中性，仲裁清单逐条可见。

并集数 = len(units_a) + len(units_b) - 对齐对数（对齐到的同文本 pair
视为同一 unit，双方各自独有的进并集）。
一致 pair 要求 kind 与 gold_segment 全等；kind 不等/segment 不等的
对齐对计入并集但不计入一致数，单列供仲裁。
"""
import difflib

THRESHOLD = 0.85
NONTEXT_ALIGNMENT = "v3-page-family"


class AgreementInputError(ValueError):
    pass


def unit_key(ann, u):
    if u["kind"] == "nontext":
        raise AgreementInputError(
            "nontext 键按页族整体计算——用 annotation_unit_keys(ann)")
    return ann["stream"][u["char_span"][0]:u["char_span"][1]].strip()


def annotation_unit_keys(ann):
    """按 units 阅读序生成对齐键序列。

    文本单元 = stream 切片 strip；nontext 单元 = (家族, 物理页)——
    v3-page-family：键不含任何按标注自身 nontext 顺序的编号（裁决 B
    硬约束：编号不得随任一方多登/漏登漂移；机械注册表 ordinal 经实证
    不可表达语义图形，见模块 docstring）。同页同族多对象键值相同，
    由 SequenceMatcher 按结构位置配对：多登/漏登只影响该对象自身
    计数，matched/union 精确；语义配对仅在页内族内可能置换（有界、
    方向中性、仲裁可见）。
    """
    keys = []
    for u in ann["units"]:
        if u["kind"] == "nontext":
            family = str(u.get("nontext_ref", "")).split(":", 1)[0]
            page = u.get("page")
            keys.append(("nontext", family, page))
        else:
            keys.append(ann["stream"][u["char_span"][0]:u["char_span"][1]]
                        .strip())
    return keys


def _brief(ann, u):
    if u["kind"] == "nontext":
        preview = u["nontext_ref"]
    else:
        preview = ann["stream"][u["char_span"][0]:u["char_span"][1]].strip()
    return {
        "unit_id": u["unit_id"],
        "kind": u["kind"],
        "page": u["page"],
        "gold_segment_id": u["gold_segment_id"],
        "preview": preview[:60],
    }


def compute_agreement(ann_a, ann_b):
    """计算两份同文档标注的 unit 级一致率。

    返回 dict：agreement（None = 双方 unit 均为空，无法定义）、
    matched / agree 计数、四类分歧清单（kind_diff / segment_diff /
    only_a / only_b）、hard_boundary_diff（信息项，不入一致判据）、
    below_threshold。
    抛 AgreementInputError：doc_id 不一致或输入形态非法。
    """
    if ann_a.get("doc_id") != ann_b.get("doc_id"):
        raise AgreementInputError(
            "doc_id mismatch: %r vs %r"
            % (ann_a.get("doc_id"), ann_b.get("doc_id")))
    for name, ann in (("a", ann_a), ("b", ann_b)):
        if "stream" not in ann or "units" not in ann:
            raise AgreementInputError(
                "annotation %s missing stream/units" % name)

    units_a = list(ann_a["units"])
    units_b = list(ann_b["units"])
    keys_a = annotation_unit_keys(ann_a)
    keys_b = annotation_unit_keys(ann_b)

    sm = difflib.SequenceMatcher(None, keys_a, keys_b, autojunk=False)
    matched = 0
    agree = 0
    hard_boundary_diff = 0
    kind_diff = []
    segment_diff = []
    aligned_a = [False] * len(keys_a)
    aligned_b = [False] * len(keys_b)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            ua = units_a[block.a + k]
            ub = units_b[block.b + k]
            matched += 1
            aligned_a[block.a + k] = True
            aligned_b[block.b + k] = True
            if ua["kind"] != ub["kind"]:
                kind_diff.append({"a": _brief(ann_a, ua),
                                  "b": _brief(ann_b, ub)})
            elif ua["gold_segment_id"] != ub["gold_segment_id"]:
                segment_diff.append({"a": _brief(ann_a, ua),
                                     "b": _brief(ann_b, ub)})
            else:
                agree += 1
                if bool(ua["hard_boundary_before"]) \
                        != bool(ub["hard_boundary_before"]):
                    hard_boundary_diff += 1

    only_a = [i for i, hit in enumerate(aligned_a) if not hit]
    only_b = [j for j, hit in enumerate(aligned_b) if not hit]
    union = len(keys_a) + len(keys_b) - matched
    agreement = (agree / union) if union else None
    return {
        "doc_id": ann_a["doc_id"],
        "agreement": agreement,
        "threshold": THRESHOLD,
        "nontext_alignment": NONTEXT_ALIGNMENT,
        "below_threshold": agreement is not None and agreement < THRESHOLD,
        "units_a": len(keys_a),
        "units_b": len(keys_b),
        "matched": matched,
        "agree": agree,
        "union": union,
        "hard_boundary_diff": hard_boundary_diff,
        "kind_diff": kind_diff,
        "segment_diff": segment_diff,
        "only_a": [_brief(ann_a, units_a[i]) for i in only_a],
        "only_b": [_brief(ann_b, units_b[j]) for j in only_b],
    }
