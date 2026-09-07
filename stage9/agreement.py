# -*- coding: utf-8 -*-
"""Stage 9 批次 26：双标注一致率（标注指南 §7 契约实现）。

比对口径：unit 级（切分一致 + gold_segment 一致）；
一致率 = 一致 unit 数 / 双方 unit 并集数；<0.85 且仲裁不收敛为停机
条件（脚本只报告阈值，是否停机由仲裁判定）。

对齐方法：同一文档的两份标注按人工阅读序各成一个 unit 序列，unit
对齐键 = 规范化文本（文本单元取 stream 上 char_span 的 strip 文本；
nontext 单元无文本，对齐键 = 家族(img/tab)+物理页，**与
nontext_ref 命名字符串无关**——跨标注人命名从未冻结；也**不含任何
按标注自身 nontext 出现顺序的编号**——2026-09-07 裁决 B 硬约束：
序号须来自共同源注册表且不随任一方多登/漏登漂移，而机械注册表
（pdfplumber page.images / find_tables）经实证无法枚举语义图形
（tech-03 标注 241 图 vs 2308 个栅格、多页语义图 2 张而栅格 0 个、
FTAB 151 检测 vs 17 语义表），source ordinal 不可表达，故取零编号
的最粗源稳定粒度=同页同族）。两序列经
difflib.SequenceMatcher(autojunk=False) 对齐——同文档同 splitter 冻结
规则下分歧局部化，序对齐即位置对应；重复文本（如告示框标签 "Note"
×269）依赖序列位置而非文本唯一性。对齐只认键（文本切分/非文本
页族），kind 与 gold_segment 在对齐对上另行比较。

nontext 身份不可辨识区间（v3-page-family-bounded，裁决 B' 2026-09-07
二轮）：同页同族**双方均多对象**的组（歧义组）内，"哪个 A 对象与
哪个 B 对象是同一视觉语义对象"无观测依据——结构位置配对仅为诊断，
不作为最终口径。计数层（presence）追认为精确：matched/union 不随
组内配对选择变化（多登/漏登只罚该对象自身）。一致数层对该组枚举
**所有合法一对一配对**（恰 matched_g 对、单射、m×n 全空间），取
per-pair 一致贡献之和的 min/max（二分图最大匹配精确求解），全篇合成
agreement_lower/agreement_upper。判定：lower≥0.85 过 / upper<0.85
照走仲裁 / lower<0.85≤upper 不可判定 → 仅对跨线组做 identity
resolution（解析者只看 PDF 页面+结构位置、对 gold_segment 与得分
盲态，不得改任一标注人的切分/kind/segment；pair map 单独保存+hash，
经 CLI --pair-map 代入后计算确定最终一致率）。各配对贡献相同的组
lower=upper 自然退化单值。单侧 ≤1 对象的组不属歧义组（裁决口径
"≤1 对象正常算"）：结构配对照算，kind/seg 差异逐条可见。

并集数 = len(units_a) + len(units_b) - 对齐对数（对齐到的同文本 pair
视为同一 unit，双方各自独有的进并集）。
一致 pair 要求 kind 与 gold_segment 全等；kind 不等/segment 不等的
对齐对计入并集但不计入一致数，单列供仲裁。
"""
import difflib

THRESHOLD = 0.85
NONTEXT_ALIGNMENT = "v3-page-family-bounded"


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
    键不含任何按标注自身 nontext 顺序的编号（裁决 B 硬约束），也
    与 nontext_ref 命名无关。同页同族多对象键值相同：presence 计数
    精确，组内配对身份见 v3-page-family-bounded 区间口径（模块
    docstring）。
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


def _group_key_of(u):
    return (str(u.get("nontext_ref", "")).split(":", 1)[0], u.get("page"))


def _pair_map_key(group_key):
    return "%s|%s" % group_key


def _validate_pair_map_shape(pair_map):
    if not isinstance(pair_map, dict):
        raise AgreementInputError(
            "pair map 须为 {\"家族|页\": [[a_unit_id, b_unit_id], ...]}")
    for gk, pairs in pair_map.items():
        if not isinstance(gk, str) or not isinstance(pairs, list):
            raise AgreementInputError(
                "pair map 条目形状非法: %r" % (gk,))
        for pair in pairs:
            if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                    or not all(isinstance(x, str) for x in pair)):
                raise AgreementInputError(
                    "pair map 配对须为 [a_unit_id, b_unit_id]: %r"
                    % (pair,))


def _resolve_pairs(spec, map_key, members_a, members_b, k_g):
    """校验并实例化 identity resolution 配对：恰 k_g 对、单射、
    unit_id 只能引用该组对象。"""
    if len(spec) != k_g:
        raise AgreementInputError(
            "pair map 组 %s 配对数 %d ≠ 该组 matched %d"
            % (map_key, len(spec), k_g))
    a_by_id = {u["unit_id"]: u for u in members_a}
    b_by_id = {u["unit_id"]: u for u in members_b}
    used_a = set()
    used_b = set()
    resolved = []
    for a_uid, b_uid in spec:
        if a_uid not in a_by_id or b_uid not in b_by_id:
            raise AgreementInputError(
                "pair map 组 %s 引用了不属于该组的 unit_id: %r/%r"
                % (map_key, a_uid, b_uid))
        if a_uid in used_a or b_uid in used_b:
            raise AgreementInputError(
                "pair map 组 %s 非单射: %r/%r" % (map_key, a_uid, b_uid))
        used_a.add(a_uid)
        used_b.add(b_uid)
        resolved.append((a_by_id[a_uid], b_by_id[b_uid]))
    return resolved


def _max_bipartite_matching(m, n, edge_ok):
    """Kuhn 增广路求二分图最大匹配数；edge_ok(i, j) 为真时 (i, j)
    可配。组内对象数为个位到几十，递归深度无虞。"""
    match_b = [-1] * n

    def _augment(i, seen):
        for j in range(n):
            if edge_ok(i, j) and not seen[j]:
                seen[j] = True
                if match_b[j] == -1 or _augment(match_b[j], seen):
                    match_b[j] = i
                    return True
        return False

    size = 0
    for i in range(m):
        if _augment(i, [False] * n):
            size += 1
    return size


def _group_contribution_bounds(members_a, members_b, k, pair_agrees):
    """歧义组一致贡献区间：所有恰 k 对的单射配对下，全等对数的
    最小/最大值。最大 = min(k, ν1)（全等边最大匹配 ν1，其余对随便
    补齐）；最小 = k - min(k, ν0)（先把非全等边配满，余下被迫
    全等）。k=0 时 (0, 0)。"""
    m = len(members_a)
    n = len(members_b)
    nu1 = _max_bipartite_matching(
        m, n, lambda i, j: pair_agrees(members_a[i], members_b[j]))
    nu0 = _max_bipartite_matching(
        m, n, lambda i, j: not pair_agrees(members_a[i], members_b[j]))
    return k - min(k, nu0), min(k, nu1)


def compute_agreement(ann_a, ann_b, pair_map=None, pair_map_sha256=None):
    """计算两份同文档标注的 unit 级一致率（v3-page-family-bounded）。

    pair_map（可选）：identity resolution 产物，
    {"家族|页": [[a_unit_id, b_unit_id], ...]}。只允许覆盖歧义组
    （同页同族双方均 ≥2 对象），每组恰 matched 对、单射、unit_id
    只能引用组内对象；提供后该组按解析配对出确定贡献，报告含
    identity_resolution.pair_map_sha256。resolution 只决定"哪个是
    同一视觉语义对象"，不改任一标注人的切分/kind/segment，也不改
    presence 计数。

    返回 dict：agreement（歧义组全部消解时=确定值；否则=结构配对
    诊断值，必落在 [agreement_lower, agreement_upper] 内）、
    agreement_lower/agreement_upper（全部合法配对区间）、
    agree_lower/agree_upper（对应计数）、decision
    （pass/below_threshold/indeterminate；双方 unit 均空时 None）、
    ambiguous_group_count/ambiguous_groups（组明细：成员数、matched、
    贡献区间、双方 unit_id 清单、是否已消解）、四类分歧清单（歧义
    组未消解时该组条目为结构诊断）、hard_boundary_diff（信息项）、
    below_threshold（decision ∈ {below_threshold, indeterminate}——
    二者均需处置，驱动 CLI rc 1）。
    抛 AgreementInputError：doc_id 不一致、输入形态非法或 pair map
    非法。
    """
    if ann_a.get("doc_id") != ann_b.get("doc_id"):
        raise AgreementInputError(
            "doc_id mismatch: %r vs %r"
            % (ann_a.get("doc_id"), ann_b.get("doc_id")))
    for name, ann in (("a", ann_a), ("b", ann_b)):
        if "stream" not in ann or "units" not in ann:
            raise AgreementInputError(
                "annotation %s missing stream/units" % name)
    if pair_map is not None:
        _validate_pair_map_shape(pair_map)

    units_a = list(ann_a["units"])
    units_b = list(ann_b["units"])
    keys_a = annotation_unit_keys(ann_a)
    keys_b = annotation_unit_keys(ann_b)

    groups = {}
    order = []
    for side, units in (("a", units_a), ("b", units_b)):
        for u in units:
            if u["kind"] != "nontext":
                continue
            gk = _group_key_of(u)
            if gk not in groups:
                groups[gk] = {"a": [], "b": []}
                order.append(gk)
            groups[gk][side].append(u)

    def _pair_agrees(ua, ub):
        return (ua["kind"] == ub["kind"]
                and ua["gold_segment_id"] == ub["gold_segment_id"])

    hard_boundary_diff = 0
    kind_diff = []
    segment_diff = []

    def _consume(ua, ub):
        """比对一个配对：kind/seg 差异进清单，全等时比较 hard 边界
        （信息项，仅在全等对上比较）。返回 'kind'/'segment'/'agree'。"""
        nonlocal hard_boundary_diff
        if ua["kind"] != ub["kind"]:
            kind_diff.append({"a": _brief(ann_a, ua),
                              "b": _brief(ann_b, ub)})
            return "kind"
        if ua["gold_segment_id"] != ub["gold_segment_id"]:
            segment_diff.append({"a": _brief(ann_a, ua),
                                 "b": _brief(ann_b, ub)})
            return "segment"
        if bool(ua["hard_boundary_before"]) \
                != bool(ub["hard_boundary_before"]):
            hard_boundary_diff += 1
        return "agree"

    sm = difflib.SequenceMatcher(None, keys_a, keys_b, autojunk=False)
    matched = 0
    aligned_a = [False] * len(keys_a)
    aligned_b = [False] * len(keys_b)
    struct_pairs = {}
    text_agree = 0
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            ua = units_a[block.a + k]
            ub = units_b[block.b + k]
            matched += 1
            aligned_a[block.a + k] = True
            aligned_b[block.b + k] = True
            if ua["kind"] == "nontext":
                struct_pairs.setdefault(_group_key_of(ua),
                                        []).append((ua, ub))
            elif _consume(ua, ub) == "agree":
                text_agree += 1

    cnt_lower = text_agree
    cnt_upper = text_agree
    cnt_struct = text_agree
    cnt_definitive = text_agree
    ambiguous_groups = []
    resolved_count = 0
    unresolved = False
    pair_map_keys = set(pair_map) if pair_map is not None else set()
    touched = set()
    for gk in order:
        members_a = groups[gk]["a"]
        members_b = groups[gk]["b"]
        ambiguous = len(members_a) >= 2 and len(members_b) >= 2
        pairs = struct_pairs.get(gk, [])
        k_g = len(pairs)
        map_key = _pair_map_key(gk)
        if map_key in pair_map_keys:
            touched.add(map_key)
            if not ambiguous:
                raise AgreementInputError(
                    "pair map 组 %s 非歧义组（同页同族双方均多对象才"
                    "可做 identity resolution）" % map_key)
            resolved = _resolve_pairs(pair_map[map_key], map_key,
                                      members_a, members_b, k_g)
            g_agree = sum(1 for ua, ub in resolved if _pair_agrees(ua, ub))
            for ua, ub in resolved:
                _consume(ua, ub)
            g_struct = sum(1 for ua, ub in pairs if _pair_agrees(ua, ub))
            cnt_definitive += g_agree
            cnt_lower += g_agree
            cnt_upper += g_agree
            cnt_struct += g_struct
            resolved_count += 1
            ambiguous_groups.append({
                "group": [gk[0], gk[1]],
                "side_a": len(members_a),
                "side_b": len(members_b),
                "matched": k_g,
                "contribution_lower": g_agree,
                "contribution_upper": g_agree,
                "resolved": True,
                "a_unit_ids": [u["unit_id"] for u in members_a],
                "b_unit_ids": [u["unit_id"] for u in members_b],
            })
            continue
        if not ambiguous:
            for ua, ub in pairs:
                if _consume(ua, ub) == "agree":
                    cnt_definitive += 1
                    cnt_lower += 1
                    cnt_upper += 1
                    cnt_struct += 1
            continue
        # 歧义组未消解：结构配对仅诊断（清单照出，贡献走区间）
        cnt_struct += sum(1 for ua, ub in pairs if _pair_agrees(ua, ub))
        for ua, ub in pairs:
            _consume(ua, ub)
        lo, hi = _group_contribution_bounds(members_a, members_b, k_g,
                                            _pair_agrees)
        cnt_lower += lo
        cnt_upper += hi
        unresolved = True
        ambiguous_groups.append({
            "group": [gk[0], gk[1]],
            "side_a": len(members_a),
            "side_b": len(members_b),
            "matched": k_g,
            "contribution_lower": lo,
            "contribution_upper": hi,
            "resolved": False,
            "a_unit_ids": [u["unit_id"] for u in members_a],
            "b_unit_ids": [u["unit_id"] for u in members_b],
        })
    for map_key in sorted(pair_map_keys - touched):
        raise AgreementInputError(
            "pair map 组在本标注对中不存在: %s" % map_key)

    only_a = [i for i, hit in enumerate(aligned_a) if not hit]
    only_b = [j for j, hit in enumerate(aligned_b) if not hit]
    union = len(keys_a) + len(keys_b) - matched
    if unresolved:
        agree_report = cnt_struct
    else:
        agree_report = cnt_definitive
        cnt_lower = cnt_definitive
        cnt_upper = cnt_definitive
    agreement = (agree_report / union) if union else None
    agreement_lower = (cnt_lower / union) if union else None
    agreement_upper = (cnt_upper / union) if union else None

    if agreement is None:
        decision = None
    elif agreement_lower >= THRESHOLD:
        decision = "pass"
    elif agreement_upper < THRESHOLD:
        decision = "below_threshold"
    else:
        decision = "indeterminate"
    return {
        "doc_id": ann_a["doc_id"],
        "agreement": agreement,
        "agreement_lower": agreement_lower,
        "agreement_upper": agreement_upper,
        "threshold": THRESHOLD,
        "nontext_alignment": NONTEXT_ALIGNMENT,
        "decision": decision,
        "below_threshold": decision in ("below_threshold",
                                        "indeterminate"),
        "units_a": len(keys_a),
        "units_b": len(keys_b),
        "matched": matched,
        "agree": agree_report,
        "agree_lower": cnt_lower,
        "agree_upper": cnt_upper,
        "union": union,
        "hard_boundary_diff": hard_boundary_diff,
        "kind_diff": kind_diff,
        "segment_diff": segment_diff,
        "only_a": [_brief(ann_a, units_a[i]) for i in only_a],
        "only_b": [_brief(ann_b, units_b[j]) for j in only_b],
        "ambiguous_group_count": len(ambiguous_groups),
        "ambiguous_groups": ambiguous_groups,
        "identity_resolution": (
            {"pair_map_sha256": pair_map_sha256,
             "resolved_group_count": resolved_count}
            if pair_map is not None else None),
    }
