# -*- coding: utf-8 -*-
"""Stage 9 批次 26：双标注一致率（标注指南 §7 契约实现）。

比对口径：unit 级（切分一致 + gold_segment 一致）；
一致率 = 一致 unit 数 / 双方 unit 并集数；<0.85 且仲裁不收敛为停机
条件（脚本只报告阈值，是否停机由仲裁判定）。

对齐方法：同一文档的两份标注按人工阅读序各成一个 unit 序列，unit
对齐键 = 规范化文本（文本单元取 stream 上 char_span 的 strip 文本；
nontext 单元无文本，用 nontext_ref）。两序列经
difflib.SequenceMatcher(autojunk=False) 对齐——同文档同 splitter 冻结
规则下分歧局部化，序对齐即位置对应；重复文本（如告示框标签 "Note"
×269）依赖序列位置而非文本唯一性。对齐只认文本（切分），kind 与
gold_segment 在对齐对上另行比较。

并集数 = len(units_a) + len(units_b) - 对齐对数（对齐到的同文本 pair
视为同一 unit，双方各自独有的进并集）。
一致 pair 要求 kind 与 gold_segment 全等；kind 不等/segment 不等的
对齐对计入并集但不计入一致数，单列供仲裁。
"""
import difflib

THRESHOLD = 0.85


class AgreementInputError(ValueError):
    pass


def unit_key(ann, u):
    if u["kind"] == "nontext":
        return ("nontext", u["nontext_ref"])
    return ann["stream"][u["char_span"][0]:u["char_span"][1]].strip()


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
    keys_a = [unit_key(ann_a, u) for u in units_a]
    keys_b = [unit_key(ann_b, u) for u in units_b]

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
