"""人工标注指标：figure-caption（本期固定 null）+ chunk_boundary P/R/F1。

约定：
- figure_caption_*：parser 当前不输出 caption↔figure 的 relation，固定 null + reason。
  本期不引入"最近图片"启发式（那是新功能，不是评测）。
- chunk_boundary_*：基于人工标注的 marker（在规范化全文流中可定位的子串）。
  匹配是一对一的：一个预测边界只能命中一个标注 anchor，反之亦然。
  容差（tolerance_chars）必须在报告中明确记录。
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.chunkers.structural import normalize_text

from evaluation.metrics import _null, _ratio

PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"


def figure_caption_prf(
    document: dict[str, Any] | None,
    annotation: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """图表关联 P/R/F1：parser 当前不输出 relation，固定 null。"""
    reason = PARSER_DOES_NOT_EMIT_RELATIONS
    return {
        "figure_caption_precision": _null(reason),
        "figure_caption_recall": _null(reason),
        "figure_caption_f1": _null(reason),
    }


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


__all__ = [
    "PARSER_DOES_NOT_EMIT_RELATIONS",
    "figure_caption_prf",
    "chunk_boundary_prf",
]
