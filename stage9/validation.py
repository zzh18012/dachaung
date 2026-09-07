# -*- coding: utf-8 -*-
"""Stage 9 批次 26：标注文件校验（契约实现）。

契约（docs/stage9-batch26-design.md §7）：输入 = 标注 JSON + manifest；
检查 = schema 符合、char_span 连续无重叠全覆盖、norm_hash 复算一致、
gold_segment 引用闭合、split 分层约束；退出码 0/1/2 + 失败报告。

格式版本 annotation_schema=v1.1（2026-09-05 GPT 裁决 C1/C2 正式化）：
v1.0 = 设计 §3 原字段；v1.1 = ①`stream`（文档规范化字符流全文）由偏差
转正——norm_hash 复算与 span 全覆盖检查以该流为唯一基准（标注流是人工
阅读序，独立于任何解析器输出，无法从源文档再推导）；unit 间分隔空格
归前一 unit 的 span 末尾（平铺规则，写入指南 §4）；②page 只表物理页码
（DOCX 无物理页 → null），DOCX 定位改用 body_index（body 元素 1-based
连续序）——禁一字段两义。
"""
import hashlib
import json
import re

from stage9.normalize import is_folded

UNIT_ID_RE = re.compile(r"^u\d{4,}$")
NONTEXT_REF_RE = re.compile(r"^(img|tab):\S+$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
KINDS = ("heading", "sentence", "nontext")
TEXT_KINDS = ("heading", "sentence")
PREVIEW_MAX = 60
FROZEN_SPLITTER = "v1"
FROZEN_NORMALIZATION = "fold-ws-v1"
FROZEN_ANNOTATION_SCHEMA = "v1.1"


class Failure:
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail

    def to_json(self):
        return {"code": self.code, "detail": self.detail}


def _sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_annotation(data, manifest_index):
    """校验单篇标注 JSON。manifest_index: doc_id -> manifest 条目（可 None）。

    返回 (doc_id, failures)。
    """
    fails = []

    def f(code, detail):
        fails.append(Failure(code, detail))

    if not isinstance(data, dict):
        return None, [Failure("bad_type", "顶层不是 JSON 对象")]
    doc_id = data.get("doc_id")
    if not isinstance(doc_id, str) or not doc_id:
        return None, [Failure("missing_field", "doc_id 缺失或非字符串")]

    if data.get("annotation_schema") != FROZEN_ANNOTATION_SCHEMA:
        f("frozen_value", "annotation_schema 必须为 %r"
          % FROZEN_ANNOTATION_SCHEMA)
    if data.get("sentence_splitter") != FROZEN_SPLITTER:
        f("frozen_value", "sentence_splitter 必须为 %r" % FROZEN_SPLITTER)
    if data.get("normalization") != FROZEN_NORMALIZATION:
        f("frozen_value", "normalization 必须为 %r" % FROZEN_NORMALIZATION)
    if not isinstance(data.get("annotator"), str) or not data.get("annotator"):
        f("missing_field", "annotator 缺失或为空")

    stream = data.get("stream")
    if not isinstance(stream, str) or not stream:
        f("missing_field", "stream 缺失或非字符串")
        stream = ""
    elif not is_folded(stream):
        f("stream_not_folded", "stream 不符合 fold-ws-v1（空白折叠+strip）")

    units = data.get("units")
    if not isinstance(units, list) or not units:
        return doc_id, fails + [Failure("missing_field",
                                        "units 缺失或为空")]
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        return doc_id, fails + [Failure("missing_field",
                                        "segments 缺失或为空")]

    segment_ids = []
    for seg in segments:
        if not isinstance(seg, dict):
            f("bad_type", "segment 不是对象")
            continue
        sid = seg.get("gold_segment_id")
        if not isinstance(sid, str) or not sid:
            f("missing_field", "segment.gold_segment_id 缺失或为空")
            continue
        if sid in segment_ids:
            f("duplicate_segment_id", sid)
        segment_ids.append(sid)

    seen_unit_ids = set()
    nontext_refs = set()
    text_units = []
    entry = (manifest_index.get(doc_id)
             if isinstance(manifest_index, dict) else None)
    doc_format = entry.get("format") if isinstance(entry, dict) else None
    for idx, unit in enumerate(units):
        where = "units[%d]" % idx
        if not isinstance(unit, dict):
            f("bad_type", where + " 不是对象")
            continue
        uid = unit.get("unit_id")
        if not isinstance(uid, str) or not UNIT_ID_RE.match(uid):
            f("bad_unit_id_format", where + " unit_id 不匹配 ^u\\d{4,}$")
            uid = where
        elif uid in seen_unit_ids:
            f("duplicate_unit_id", uid)
        seen_unit_ids.add(uid)

        kind = unit.get("kind")
        if kind not in KINDS:
            f("bad_type", "%s.kind 必须为 %s 之一" % (where, "/".join(KINDS)))
            kind = None

        page = unit.get("page")
        if page is not None and (not isinstance(page, int)
                                 or isinstance(page, bool) or page < 1):
            f("bad_type", where + ".page 必须为 null 或 >=1 整数（物理页码）")
        body_index = unit.get("body_index")
        if body_index is not None and (
                not isinstance(body_index, int)
                or isinstance(body_index, bool) or body_index < 1):
            f("bad_type",
              where + ".body_index 必须为 null 或 >=1 整数（body 元素序）")
        if page is not None and body_index is not None:
            f("dual_locator",
              "%s 同时设 page 与 body_index（定位字段互斥，禁一字段两义）"
              % uid)
        if doc_format == "docx" and page is not None:
            f("locator_format_mismatch",
              "%s DOCX 篇 page 必须为 null（无物理页码）" % uid)
        if doc_format == "pdf" and body_index is not None:
            f("locator_format_mismatch",
              "%s PDF 篇 body_index 必须为 null（定位用物理页 page）" % uid)

        if not isinstance(unit.get("hard_boundary_before"), bool):
            f("bad_type", where + ".hard_boundary_before 必须为布尔")

        if kind in TEXT_KINDS:
            span = unit.get("char_span")
            if not (isinstance(span, list) and len(span) == 2
                    and all(isinstance(x, int) and not isinstance(x, bool)
                            for x in span)):
                f("bad_type", where + ".char_span 必须为 [int, int]")
            elif not (0 <= span[0] < span[1] <= len(stream)):
                f("span_out_of_range",
                  "%s char_span=%r 越界（流长 %d）" % (uid, span, len(stream)))
            else:
                text_units.append((uid, span))
                expect = _sha(stream[span[0]:span[1]])
                if unit.get("norm_text_hash") != expect:
                    f("hash_mismatch",
                      "%s norm_text_hash 复算不一致（期望 %s）"
                      % (uid, expect))
                preview = unit.get("text_preview")
                unit_text = stream[span[0]:span[1]]
                if not isinstance(preview, str) or not preview \
                        or len(preview) > PREVIEW_MAX \
                        or not unit_text.startswith(preview):
                    f("preview_mismatch",
                      "%s text_preview 须为 unit 文本的非空前缀且 ≤%d 字"
                      % (uid, PREVIEW_MAX))
        elif kind == "nontext":
            if unit.get("char_span") is not None:
                f("span_not_null_nontext",
                  uid + " nontext unit 的 char_span 必须为 null")
            if unit.get("norm_text_hash") is not None:
                f("bad_type", uid + " nontext unit 的 norm_text_hash 须 null")
            ref = unit.get("nontext_ref")
            if not isinstance(ref, str) or not NONTEXT_REF_RE.match(ref):
                f("bad_nontext_ref",
                  uid + " nontext_ref 须匹配 ^(img|tab):\\S+$")
            elif ref in nontext_refs:
                f("duplicate_nontext_ref", ref)
            else:
                nontext_refs.add(ref)

        gid = unit.get("gold_segment_id")
        if not isinstance(gid, str) or not gid:
            f("missing_field", uid + " 缺 gold_segment_id")
        elif segment_ids and gid not in segment_ids:
            f("unknown_segment", "%s 引用不存在的 gold_segment_id=%s"
              % (uid, gid))

        linked = unit.get("linked_nontext")
        if linked is not None:
            if not isinstance(linked, list) or \
                    not all(isinstance(x, str) for x in linked):
                f("bad_type", uid + ".linked_nontext 须为字符串列表")

    # linked_nontext 引用闭合（两遍：先收集全部 nontext_ref）。
    # 七轮裁决 B1 确定性约束（2026-09-07）：同一 text unit 禁重复 ref；
    # 多 ref 必须按目标 nontext unit 在 units 列表（阅读序）中的顺序
    # 排列——语义相同的关系集合不得因填写顺序不同产生随机 gold hash。
    all_nontext_refs = {u.get("nontext_ref") for u in units
                        if isinstance(u, dict)
                        and u.get("kind") == "nontext"}
    ref_reading_order = {}
    for i, u in enumerate(units):
        if isinstance(u, dict) and u.get("kind") == "nontext" \
                and isinstance(u.get("nontext_ref"), str):
            ref_reading_order[u["nontext_ref"]] = i
    for unit in units:
        if not isinstance(unit, dict):
            continue
        linked = unit.get("linked_nontext")
        if not isinstance(linked, list):
            continue  # 非 list 已在第一遍报 bad_type
        uid = unit.get("unit_id", "?")
        if len(set(linked)) != len(linked):
            f("duplicate_linked_ref",
              "%s linked_nontext 存在重复 ref: %r" % (uid, linked))
        positions = [ref_reading_order[r] for r in linked
                     if r in ref_reading_order]
        if positions != sorted(positions):
            f("linked_ref_order",
              "%s linked_nontext 未按目标 nontext unit 的阅读序排列: %r"
              % (uid, linked))
        for ref in linked:
            if ref not in all_nontext_refs:
                f("unknown_nontext_ref",
                  "%s linked_nontext 引用不存在的 nontext_ref=%s"
                  % (uid, ref))

    # 引用闭合另一方向：segment 必须被至少一个 unit 引用
    referenced = {u.get("gold_segment_id") for u in units
                  if isinstance(u, dict)}
    for sid in segment_ids:
        if sid not in referenced:
            f("unreferenced_segment", sid)

    # C1（裁决 2026-09-05）：units 列表序 = 阅读序，text unit 的
    # char_span 在列表序中必须单调递增（此前先排序再查覆盖，序违规被吞）
    for k in range(1, len(text_units)):
        prev_uid, (_pa, pb) = text_units[k - 1]
        cur_uid, (a, _cb) = text_units[k]
        if a < pb:
            f("unit_order",
              "%s char_span 起点落在前一 text unit（%s）span 内——"
              "units 列表序与流序不一致" % (cur_uid, prev_uid))

    # char_span 连续无重叠全覆盖（仅 text units）
    text_units.sort(key=lambda t: t[1][0])
    pos = 0
    for uid, (a, b) in text_units:
        if a < pos:
            f("span_overlap", "%s char_span 与前一 unit 重叠" % uid)
        elif a > pos:
            f("span_gap", "%s 前有 %d 字符未覆盖间隙" % (uid, a - pos))
        pos = max(pos, b)
    if stream and text_units and pos != len(stream):
        f("span_gap", "流尾有 %d 字符未覆盖" % (len(stream) - pos))
    if stream and not text_units:
        f("span_gap", "流非空但没有任何 text unit")

    # manifest 交叉核对
    if manifest_index is not None and entry is None:
        f("doc_not_in_manifest", doc_id)

    return doc_id, fails


def validate_split_constraints(manifest_data, annotated_doc_ids):
    """--full-set：split 分层约束。返回 (failures, summary)。"""
    fails = []
    docs = [d for d in manifest_data.get("docs", [])
            if isinstance(d, dict) and d.get("split")]
    by_split = {}
    for d in docs:
        by_split.setdefault(d["split"], []).append(d)
    expected = {"dev": 14, "comparison": 4, "holdout": 6}
    for split, want in expected.items():
        got = len(by_split.get(split, []))
        if got != want:
            fails.append(Failure(
                "split_count_mismatch",
                "%s 数量 %d != %d" % (split, got, want)))
        domains = {d.get("domain") for d in by_split.get(split, [])}
        for dom in ("academic", "tech_report", "product_manual"):
            if dom not in domains:
                fails.append(Failure(
                    "split_domain_coverage",
                    "%s 缺少域 %s" % (split, dom)))
    for d in docs:
        if d["doc_id"] not in annotated_doc_ids:
            fails.append(Failure("missing_annotation", d["doc_id"]))
    summary = {
        "split_counts": {k: len(v) for k, v in sorted(by_split.items())},
        "annotated": len(annotated_doc_ids),
        "total": len(docs),
    }
    return fails, summary


def validate_manifest_consistency(manifest_data):
    """D1 规则（2026-09-06 裁决轮4）：声明的 split_counts 若存在，逐键
    必须等于逐篇 split 重算结果；不一致判 manifest consistency failure。

    检查两处声明（_meta.split_counts 与顶层 split_counts，均"若存在才查"）：
    每个声明键的重算值 = split==key 的文档数；键 unassigned_spares 例外，
    重算值 = 无 split 字段的文档数。校验器本身从不消费这些声明字段
    （--full-set 一律独立重算），本检查只保证声明与逐篇字段不矛盾。
    """
    fails = []
    if not isinstance(manifest_data, dict):
        return fails
    docs = [d for d in manifest_data.get("docs", []) if isinstance(d, dict)]
    meta = manifest_data.get("_meta")
    declared_fields = []
    if isinstance(meta, dict) and isinstance(meta.get("split_counts"), dict):
        declared_fields.append(("_meta.split_counts", meta["split_counts"]))
    if isinstance(manifest_data.get("split_counts"), dict):
        declared_fields.append(("split_counts", manifest_data["split_counts"]))
    for where, declared in declared_fields:
        for key, value in declared.items():
            if not isinstance(value, int) or isinstance(value, bool):
                fails.append(Failure(
                    "manifest_consistency_failure",
                    "%s.%s 值非整数: %r" % (where, key, value)))
                continue
            if key == "unassigned_spares":
                got = sum(1 for d in docs if not d.get("split"))
            else:
                got = sum(1 for d in docs if d.get("split") == key)
            if value != got:
                fails.append(Failure(
                    "manifest_consistency_failure",
                    "%s.%s=%d 与逐篇 split 重算 %d 不一致"
                    % (where, key, value, got)))
    return fails


def compute_link_stats(data):
    """七轮裁决 B3（2026-09-07）：linked_nontext 计算型披露统计。

    从标注实际字节现场重算（不信任任何手填 _meta）：
    - linked_pairs = 去重后 text→nontext gold 边数（(unit, ref) 对）；
    - linked_objects = 有 ≥1 入边的 unique nontext 对象数；
    - anchorless_count = 无入边对象数；
    - nontext_total = nontext 对象总数。
    恒等式 linked_objects + anchorless_count = nontext_total 由构造
    保证（两者按同一出现次数口径计数）。纯诊断披露，无通过阈值——
    anchorless_count > 0 完全合法，不构成校验失败。
    """
    units = data.get("units") if isinstance(data, dict) else None
    if not isinstance(units, list):
        return {"linked_pairs": 0, "linked_objects": 0,
                "anchorless_count": 0, "nontext_total": 0}
    nontext_refs = [u["nontext_ref"] for u in units
                    if isinstance(u, dict) and u.get("kind") == "nontext"
                    and isinstance(u.get("nontext_ref"), str)]
    linked_refs = set()
    pairs = 0
    for u in units:
        if not isinstance(u, dict):
            continue
        linked = u.get("linked_nontext")
        if not isinstance(linked, list):
            continue
        uniq = [r for r in linked if isinstance(r, str)]
        pairs += len(set(uniq))
        linked_refs.update(uniq)
    linked_objects = sum(1 for r in nontext_refs if r in linked_refs)
    return {
        "linked_pairs": pairs,
        "linked_objects": linked_objects,
        "anchorless_count": len(nontext_refs) - linked_objects,
        "nontext_total": len(nontext_refs),
    }


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
