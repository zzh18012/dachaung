# -*- coding: utf-8 -*-
"""编号不变性辅助审计（外部评审 R-A，2026-09-16 裁决：评审执行序第一项）。

冻结 v1 一致率（stage9/agreement.py）在对齐对上要求
gold_segment_id **字符串全等**；两份标注若分组完全相同仅段编号
不同（改名 g01→g03，或编号漂移：一方多切一段导致后续 g 序号整
体错位），一致率会从 1 跌到 0。本模块不改冻结算法、不改任何原
始报告，只提供**辅助口径**：把段标签按"对齐单元等价类"规范化
后重算一致率，两者之差 = 纯编号伪分歧的量级估计。

规范化方法：按 compute_agreement 同样的对齐键（文本 strip /
nontext 页族）用 difflib.SequenceMatcher(None, keys_a, keys_b,
autojunk=False) 取对齐对，每对赋一个 pair_index（任意双射即可，
两侧一致）；每份标注里，段的 canonical key = 该段所含**对齐**
单元的 pair_index 升序元组；把每个对齐单元的 gold_segment_id
替换为该 key 的 repr 后，用未修改的 compute_agreement 重算。
两段（A 一段、B 一段）key 相等 ⟺ 它们覆盖完全相同的对齐单元
集合（在可比对象上的分组相同）。未对齐单元不进任何比较，其
标签保持原值。

分解语义：
- label_only_pairs：字符串口径 segment_diff、分区口径相等的对
  ——纯编号差异（改名/漂移），分组其实相同；
- partition_only_pairs：分区口径 segment_diff、字符串口径相等
  ——分区口径更严（一方把某段拆开/合并时，整个受影响段的每个
  对齐单元都算分组变了，而字符串口径可能因标签碰巧相同只罚
  边界单元）；
- 两口径都 diff 的对：真实分组分歧。
"""
import difflib

from stage9.agreement import (  # noqa: F401
    AgreementInputError,
    annotation_unit_keys,
    compute_agreement,
)


def _aligned_pairs(ann_a, ann_b):
    """镜像 compute_agreement 的对齐（键不含 gold_segment_id，
    规范化前后恒同），返回 [(a_index, b_index), ...]。"""
    keys_a = annotation_unit_keys(ann_a)
    keys_b = annotation_unit_keys(ann_b)
    sm = difflib.SequenceMatcher(None, keys_a, keys_b, autojunk=False)
    pairs = []
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            pairs.append((block.a + k, block.b + k))
    return pairs


def _canonicalize(ann, pair_side):
    """pair_side: {unit_index_in_ann: pair_index}。返回副本，其中
    含对齐单元的段被改写为 canonical key；段内无对齐单元时保持
    原标签（该段不进比较）。"""
    units = [dict(u) for u in ann["units"]]
    seg_members = {}
    for i, u in enumerate(units):
        seg_members.setdefault(u["gold_segment_id"], []).append(i)
    seg_key = {}
    for seg, members in seg_members.items():
        pidx = sorted(pair_side[i] for i in members if i in pair_side)
        seg_key[seg] = ("seg%s" % (pidx,)) if pidx else None
    for i, u in enumerate(units):
        if i in pair_side:
            u["gold_segment_id"] = seg_key[u["gold_segment_id"]]
    return dict(ann, units=units)


def audit_agreement(ann_a, ann_b, pair_map=None, pair_map_sha256=None):
    """返回审计报告 dict（原始口径 + 分区口径 + 分解 + 词表统计）。

    不修改入参；不落盘；原始报告语义见 compute_agreement。
    """
    if ann_a.get("doc_id") != ann_b.get("doc_id"):
        raise AgreementInputError(
            "doc_id mismatch: %r vs %r"
            % (ann_a.get("doc_id"), ann_b.get("doc_id")))
    original = compute_agreement(ann_a, ann_b, pair_map=pair_map,
                                 pair_map_sha256=pair_map_sha256)
    pairs = _aligned_pairs(ann_a, ann_b)
    side_a = {ai: n for n, (ai, _) in enumerate(pairs)}
    side_b = {bi: n for n, (_, bi) in enumerate(pairs)}
    canonical = compute_agreement(_canonicalize(ann_a, side_a),
                                  _canonicalize(ann_b, side_b),
                                  pair_map=pair_map,
                                  pair_map_sha256=pair_map_sha256)
    orig_diff = {(d["a"]["unit_id"], d["b"]["unit_id"])
                 for d in original["segment_diff"]}
    canon_diff = {(d["a"]["unit_id"], d["b"]["unit_id"])
                  for d in canonical["segment_diff"]}
    ids_a = {u["gold_segment_id"] for u in ann_a["units"]}
    ids_b = {u["gold_segment_id"] for u in ann_b["units"]}
    return {
        "doc_id": original["doc_id"],
        "audit": "renaming-invariant-auxiliary",
        "original": {k: original[k] for k in (
            "agreement", "agreement_lower", "agreement_upper",
            "decision", "matched", "agree", "union",
            "units_a", "units_b")},
        "original_segment_diff_count": len(original["segment_diff"]),
        "original_kind_diff_count": len(original["kind_diff"]),
        "partition": {k: canonical[k] for k in (
            "agreement", "agreement_lower", "agreement_upper",
            "decision", "agree", "union")},
        "partition_segment_diff_count": len(canonical["segment_diff"]),
        "label_only_pairs": sorted(orig_diff - canon_diff),
        "partition_only_pairs": sorted(canon_diff - orig_diff),
        "both_diff_pair_count": len(orig_diff & canon_diff),
        "segment_vocab": {
            "ids_a": len(ids_a), "ids_b": len(ids_b),
            "overlap": len(ids_a & ids_b),
            "style": "gNN-both" if all(
                isinstance(s, str) and s.startswith("g")
                and s[1:].isdigit() for s in ids_a | ids_b) else None,
        },
        "aligned_pair_count": len(pairs),
    }
