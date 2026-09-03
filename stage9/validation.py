# -*- coding: utf-8 -*-
"""Stage 9 批次 26：标注文件校验（契约实现）。

契约（docs/stage9-batch26-design.md §7）：输入 = 标注 JSON + manifest；
检查 = schema 符合、char_span 连续无重叠全覆盖、norm_hash 复算一致、
gold_segment 引用闭合、split 分层约束；退出码 0/1/2 + 失败报告。

标注 JSON 在设计 §3 示例字段之外补充一个必要字段 `stream`（文档规范化
字符流全文）：norm_hash 复算与 span 全覆盖检查都必须以该流为基准
（标注流是人工阅读序，独立于任何解析器输出，无法从源文档再推导）。
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

        if not isinstance(unit.get("page"), int) or \
                isinstance(unit.get("page"), bool) or unit.get("page", 0) < 1:
            f("bad_type", where + ".page 必须为 >=1 整数")

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

    # linked_nontext 引用闭合（两遍：先收集全部 nontext_ref）
    all_nontext_refs = {u.get("nontext_ref") for u in units
                        if isinstance(u, dict)
                        and u.get("kind") == "nontext"}
    for unit in units:
        if not isinstance(unit, dict):
            continue
        for ref in unit.get("linked_nontext") or []:
            if ref not in all_nontext_refs:
                f("unknown_nontext_ref",
                  "%s linked_nontext 引用不存在的 nontext_ref=%s"
                  % (unit.get("unit_id", "?"), ref))

    # 引用闭合另一方向：segment 必须被至少一个 unit 引用
    referenced = {u.get("gold_segment_id") for u in units
                  if isinstance(u, dict)}
    for sid in segment_ids:
        if sid not in referenced:
            f("unreferenced_segment", sid)

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
    if manifest_index is not None:
        entry = manifest_index.get(doc_id)
        if entry is None:
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


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
