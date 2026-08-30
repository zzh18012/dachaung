"""人工标注指标：figure-caption（消费 has_caption relation）+ chunk_boundary P/R/F1。

约定（docs/relation-consumption-contract.md，2026-08-30 冻结）：
- figure_caption_*：直接消费 document.relations 中 type=="has_caption" 的
  relation，对照 annotation.figure_caption_pairs（figure_marker/caption_text）
  计 P/R/F1；匹配器为 relation-type 参数化纯函数（批次 7 复用）。
  降级矩阵（pipeline_failed / no_annotation / no_annotation_pairs /
  no_predicted_relations）见契约 §3。
- chunk_boundary_*：基于人工标注的 marker（在规范化全文流中可定位的子串）。
  匹配是一对一的：一个预测边界只能命中一个标注 anchor，反之亦然。
  容差（tolerance_chars）必须在报告中明确记录。
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from app.chunkers.structural import normalize_text

from evaluation.metrics import _null, _ratio


def _element_identifying_text(el: dict[str, Any]) -> str:
    """from 侧元素的可识别文本：content + metadata.alt + resource 文件名。

    顺序固定（契约 §2.3）：docx/pdf image 的 content=None、识别信息在
    resource 文件名；md/html image 在 metadata.alt。非 str 字段跳过。
    """
    parts: list[str] = []
    if isinstance(el.get("content"), str):
        parts.append(el["content"])
    alt = (el.get("metadata") or {}).get("alt")
    if isinstance(alt, str):
        parts.append(alt)
    rp = el.get("resource_path")
    if isinstance(rp, str) and rp:
        parts.append(PurePosixPath(rp.replace("\\", "/")).name)
    return normalize_text(" ".join(parts))


def match_relation_pairs(
    document: dict[str, Any] | None,
    pairs: list[dict[str, str]] | None,
    *,
    relation_type: str,
    from_marker_key: str,
    to_marker_key: str,
) -> tuple[int, int, int] | None:
    """relation 对匹配（契约 §2，签名冻结——批次 7 只许换参数）。

    返回 (num_predicted, num_ground_truth, num_matched)。
    document 为 None 或 pairs 为 None/空 → 返回 None（调用方降级）。

    语义：预测对 = type 匹配的 relations（端点缺失不计入）；GT 对 =
    pairs；from 侧按识别文本子串匹配、to 侧按 content 子串匹配
    （均 normalize 后）；一对一贪心按 (pred_idx, gt_idx) 字典序。
    """
    if document is None or not pairs:
        return None

    elements_by_id = {e.get("element_id"): e for e in document.get("elements") or []}

    predicted: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rel in document.get("relations") or []:
        if rel.get("type") != relation_type:
            continue
        src = elements_by_id.get(rel.get("from_id"))
        dst = elements_by_id.get(rel.get("to_id"))
        if src is None or dst is None:
            continue  # 契约 §2.1：端点缺失不计入预测
        predicted.append((src, dst))

    gt: list[tuple[str, str]] = []
    for p in pairs:
        fm = p.get(from_marker_key)
        tm = p.get(to_marker_key)
        if isinstance(fm, str) and isinstance(tm, str):
            gt.append((fm, tm))

    matched = 0
    used_pred: set[int] = set()
    used_gt: set[int] = set()
    for pi, (src, dst) in enumerate(predicted):
        if pi in used_pred:
            continue
        src_txt = _element_identifying_text(src)
        dst_txt = normalize_text(dst.get("content") or "")
        for gi, (fm, tm) in enumerate(gt):
            if gi in used_gt:
                continue
            if normalize_text(fm) in src_txt and normalize_text(tm) in dst_txt:
                used_pred.add(pi)
                used_gt.add(gi)
                matched += 1
                break

    return len(predicted), len(gt), matched


def _pair_prf(
    counts: tuple[int, int, int] | None,
    *,
    prefix: str,
) -> dict[str, dict[str, Any]]:
    """(num_pred, num_gt, matched) → P/R/F1 三键（契约 §3 降级矩阵）。"""
    out: dict[str, dict[str, Any]] = {}
    p_key = f"{prefix}_precision"
    r_key = f"{prefix}_recall"
    f_key = f"{prefix}_f1"
    if counts is None:
        for k in (p_key, r_key, f_key):
            out[k] = _null("pipeline_failed")
        return out
    num_pred, num_gt, matched = counts
    if num_pred == 0:
        out[p_key] = _null("no_predicted_relations")
        out[r_key] = _ratio(0.0) if num_gt > 0 else _null("no_ground_truth_pairs")
    else:
        out[p_key] = _ratio(matched / num_pred)
        out[r_key] = (
            _ratio(matched / num_gt) if num_gt > 0 else _null("no_ground_truth_pairs")
        )
    p_val = out[p_key]["value"]
    r_val = out[r_key]["value"]
    if p_val is None or r_val is None:
        out[f_key] = _null("precision_or_recall_not_evaluated")
    else:
        denom = p_val + r_val
        out[f_key] = _ratio(2 * p_val * r_val / denom) if denom > 0 else _ratio(0.0)
    return out


def figure_caption_prf(
    document: dict[str, Any] | None,
    annotation: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """图表关联 P/R/F1：消费 has_caption relation（契约 §2/§3）。"""
    if document is None:
        counts = None
    elif not annotation:
        return {
            "figure_caption_precision": _null("no_annotation"),
            "figure_caption_recall": _null("no_annotation"),
            "figure_caption_f1": _null("no_annotation"),
        }
    else:
        pairs = annotation.get("figure_caption_pairs") or []
        if not pairs:
            return {
                "figure_caption_precision": _null("no_annotation_pairs"),
                "figure_caption_recall": _null("no_annotation_pairs"),
                "figure_caption_f1": _null("no_annotation_pairs"),
            }
        counts = match_relation_pairs(
            document,
            pairs,
            relation_type="has_caption",
            from_marker_key="figure_marker",
            to_marker_key="caption_text",
        )
    return _pair_prf(counts, prefix="figure_caption")


def table_caption_prf(
    document: dict[str, Any] | None,
    annotation: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """表题注关联 P/R/F1：消费 table_has_caption relation（契约 §2/§3）。"""
    if document is None:
        counts = None
    elif not annotation:
        return {
            "table_caption_precision": _null("no_annotation"),
            "table_caption_recall": _null("no_annotation"),
            "table_caption_f1": _null("no_annotation"),
        }
    else:
        pairs = annotation.get("table_caption_pairs") or []
        if not pairs:
            return {
                "table_caption_precision": _null("no_annotation_pairs"),
                "table_caption_recall": _null("no_annotation_pairs"),
                "table_caption_f1": _null("no_annotation_pairs"),
            }
        counts = match_relation_pairs(
            document,
            pairs,
            relation_type="table_has_caption",
            from_marker_key="table_marker",
            to_marker_key="caption_text",
        )
    return _pair_prf(counts, prefix="table_caption")


def chunk_boundary_prf(
    document: dict[str, Any] | None,
    annotation: dict[str, Any] | None,
    tolerance_chars: int = 30,
) -> dict[str, dict[str, Any]]:
    """分块边界 P/R/F1。

    算法：
    1. 规范化全文流 = normalize_text(Σ chunk.text)
    2. 预测边界位置：在规范化流中，第 i 个 chunk 结束位置（共 N-1 个，N 是 chunk 数）
    3. 标注 anchor 位置：marker 子串在规范化流中查找；
       position="before" → marker 起始位置；position="after" → marker 结束位置
    4. 一对一匹配（贪心，按距离排序）：每个 anchor 只能匹配一个预测，反之亦然
    5. precision = matched / num_predicted
       recall = matched / num_anchors
       分母为 0 时返回 null + reason

    Args:
        document: Document.to_dict()
        annotation: 标注 dict（含 chunk_boundary_anchors）
        tolerance_chars: 容差（字符数）。必须在报告中记录。
    """
    out: dict[str, dict[str, Any]] = {}

    if document is None:
        for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
            out[k] = _null("pipeline_failed")
        out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}
        return out

    if not annotation:
        for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
            out[k] = _null("no_annotation")
        out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}
        return out

    anchors = annotation.get("chunk_boundary_anchors") or []
    chunks = document.get("chunks") or []

    if not chunks or len(chunks) < 2:
        # 少于 2 个 chunk → 没有内部边界
        out["chunk_boundary_precision"] = _null("no_predicted_boundaries")
        out["chunk_boundary_recall"] = (
            _null("no_predicted_boundaries") if not anchors else _ratio(0.0)
        )
        out["chunk_boundary_f1"] = _null("no_predicted_boundaries")
        out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}
        return out

    if not anchors:
        # 有预测但无标注 anchor
        out["chunk_boundary_precision"] = _null("no_ground_truth_anchors")
        out["chunk_boundary_recall"] = _null("no_ground_truth_anchors")
        out["chunk_boundary_f1"] = _null("no_ground_truth_anchors")
        out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}
        return out

    # 1. 规范化流（保留 chunk 文本之间的分隔）
    norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]
    # 拼接：与 metrics._text_preservation 保持一致（" " 连接后再 normalize）
    # 但边界位置需要在拼接后的字符串里定位，所以重新规范化拼接结果
    joined_raw = " ".join(norm_chunks)
    stream = normalize_text(joined_raw)

    # 2. 预测边界：在 stream 里第 i 个 chunk 末尾的位置
    predicted: list[int] = []
    pos = 0
    for i, txt in enumerate(norm_chunks):
        if i == len(norm_chunks) - 1:
            break  # 最后一个 chunk 后面不算边界
        # 在 stream[pos:] 中找 txt 的下一个出现位置（容错：直接顺序匹配）
        # 因为 stream 是 normalize 后的拼接，理论上 txt 应当原样出现
        find_pos = stream.find(txt, pos)
        if find_pos < 0:
            # 找不到（理论上不该发生）→ 跳过这个 chunk 的右边界
            pos += len(txt) + 1
            continue
        end = find_pos + len(txt)
        predicted.append(end)
        pos = end + 1  # 跨过空格

    # 3. 标注 anchor → stream 位置
    gt_positions: list[int] = []
    missing_markers: list[str] = []
    for a in anchors:
        marker = a.get("marker", "")
        position = a.get("position", "after")
        find_pos = stream.find(marker)
        if find_pos < 0:
            missing_markers.append(marker)
            continue
        if position == "before":
            gt_positions.append(find_pos)
        else:  # "after"
            gt_positions.append(find_pos + len(marker))

    # 4. 一对一匹配（贪心：按 (|pred - gt|) 升序）
    pairs: list[tuple[int, int, int]] = []  # (distance, pred_idx, gt_idx)
    used_pred = set()
    used_gt = set()
    for pi, pv in enumerate(predicted):
        for gi, gv in enumerate(gt_positions):
            d = abs(pv - gv)
            if d <= tolerance_chars:
                pairs.append((d, pi, gi))
    pairs.sort(key=lambda x: x[0])
    matched = 0
    for _, pi, gi in pairs:
        if pi in used_pred or gi in used_gt:
            continue
        used_pred.add(pi)
        used_gt.add(gi)
        matched += 1

    num_pred = len(predicted)
    num_gt = len(gt_positions)

    # 5. precision / recall
    if num_pred == 0:
        out["chunk_boundary_precision"] = _null("no_predicted_boundaries")
    else:
        out["chunk_boundary_precision"] = _ratio(matched / num_pred)

    if num_gt == 0:
        out["chunk_boundary_recall"] = _null(
            "no_ground_truth_anchors_in_stream"
        )
    else:
        out["chunk_boundary_recall"] = _ratio(matched / num_gt)

    # f1
    p_val = out["chunk_boundary_precision"]["value"]
    r_val = out["chunk_boundary_recall"]["value"]
    if p_val is None or r_val is None:
        out["chunk_boundary_f1"] = _null("precision_or_recall_not_evaluated")
    else:
        denom = p_val + r_val
        if denom <= 0:
            out["chunk_boundary_f1"] = _ratio(0.0)
        else:
            out["chunk_boundary_f1"] = _ratio(2 * p_val * r_val / denom)

    out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}
    if missing_markers:
        out["_missing_markers"] = {"value": missing_markers, "reason": None}
    return out


def heading_order_prf(
    document: dict[str, Any] | None,
    annotation: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """heading 序列 P/R/F1（批次 11 契约：Option 1 序列匹配）。

    匹配键 = (metadata.level 相等) AND (normalize_text(content) ==
    normalize_text(text))——严格相等而非子串（heading 短文本，子串
    易误配；融合段落等失配情形属诚实的 recall 信号）。对齐 = LCS
    有序一对一（matched = LCS 长度）。

    降级矩阵：document=None → pipeline_failed；无 annotation →
    no_annotation；heading_order 键缺失/空 → no_ground_truth_headings；
    parser 0 个 heading → no_predicted_headings（GT>0 时 recall=0.0）。
    """
    p_key = "heading_order_precision"
    r_key = "heading_order_recall"
    f_key = "heading_order_f1"
    out: dict[str, dict[str, Any]] = {}

    if document is None:
        for k in (p_key, r_key, f_key):
            out[k] = _null("pipeline_failed")
        return out
    if not annotation:
        for k in (p_key, r_key, f_key):
            out[k] = _null("no_annotation")
        return out

    gt = annotation.get("heading_order") or []
    if not gt:
        for k in (p_key, r_key, f_key):
            out[k] = _null("no_ground_truth_headings")
        return out

    pred = [
        e for e in document.get("elements") or [] if e.get("type") == "heading"
    ]
    if not pred:
        out[p_key] = _null("no_predicted_headings")
        out[r_key] = _ratio(0.0)
        out[f_key] = _null("no_predicted_headings")
        return out

    pred_keys = [
        ((e.get("metadata") or {}).get("level"), normalize_text(e.get("content") or ""))
        for e in pred
    ]
    gt_keys = [
        (g.get("level"), normalize_text(g.get("text") or "")) for g in gt
    ]

    n, m = len(pred_keys), len(gt_keys)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        row, prev = dp[i], dp[i - 1]
        for j in range(1, m + 1):
            if pred_keys[i - 1] == gt_keys[j - 1]:
                row[j] = prev[j - 1] + 1
            else:
                row[j] = prev[j] if prev[j] >= row[j - 1] else row[j - 1]
    matched = dp[n][m]

    p_val = matched / n
    r_val = matched / m
    out[p_key] = _ratio(p_val)
    out[r_key] = _ratio(r_val)
    denom = p_val + r_val
    out[f_key] = _ratio(2 * p_val * r_val / denom) if denom > 0 else _ratio(0.0)
    return out


__all__ = [
    "match_relation_pairs",
    "figure_caption_prf",
    "table_caption_prf",
    "chunk_boundary_prf",
    "heading_order_prf",
]
