# -*- coding: utf-8 -*-
"""Stage 9 批次 26：系统侧 max_chars dev 选优评测（G⑦ 预实现，裁决 C）。

预注册：stage9/system_select_preregistration.json（先于任何真实语料
运行提交；网格=镜像冻结 B1 网格 [200,500,800,1200,2000]、macro-ARI、
平局取最小 max_chars、14 dev 篇单列、comparison/holdout 禁参与调参）。

边界（裁决 C 原文）：G⑥ 完成前**不允许**在真实 14-dev gold 上运行
max_chars 参数搜索，即使自称 dry run——CLI 以强制 --gold-revision 落实
（gold revision 只能由 G⑥ 冻结产生）；测试只用合成夹具，真实管线的
接线验证用合成文档（不触真实语料、不产生真实评分）。

评测机械与基线选优同源：系统 chunk 文本 fold-ws 后在 gold 流上定位
（顺序游标+全局回退，失败计 unmatched 不静默）→ 投影到 text unit →
ARI（unit 数据点，gold_segment vs chunk 归属）；解析失败/空结果/
标注无效 → 该文档 ARI=N/A + reason，保留计数披露（指南 §9）。
"""
from pathlib import Path

from stage9.ari import ari_units_vs_chunks
from stage9.normalize import fold_ws
from stage9.project import project_chunks_to_units

EMPTY_RESULT_MIN_ELEMENTS = 10
EMPTY_RESULT_MIN_CHARS = 200


def run_system_chunks(source_path, max_chars, parser_name="fallback"):
    """真实管线：parse+chunk 单文件，返回 (chunk 文本列表 或 None, reason)。

    None + reason ∈ {"parse_failed:<code>", "empty_result"}——按指南 §9
    计 N/A，不静默排除。调用方负责 source_path 存在性（pipeline 对
    缺失文件返回结构化 file_not_found，同样归入 parse_failed）。
    """
    from app.pipeline import process_single

    document, errors = process_single(
        source_path, None, parser_name=parser_name,
        max_chars=max_chars, write_json=False)
    if document is None:
        code = errors[0].code if errors else "unknown"
        return None, "parse_failed:%s" % code
    if len(document.elements) < EMPTY_RESULT_MIN_ELEMENTS:
        return None, "empty_result"
    chunk_texts = [c.text for c in document.chunks if c.text]
    if not chunk_texts or sum(len(t) for t in chunk_texts) \
            < EMPTY_RESULT_MIN_CHARS:
        return None, "empty_result"
    return chunk_texts, None


def evaluate_system_doc(ann, chunks_by_param, params, na_by_param=None):
    """单篇标注 × {max_chars: chunk 文本列表} 评测（纯函数，合成可测）。

    chunks_by_param：{param: chunk 文本列表}；na_by_param：{param:
    reason}（该参数下管线不可用——parse_failed:<code> / empty_result /
    annotation_invalid），两者互斥（na 优先）。返回 {doc_id, chars,
    text_units, results: {param: {ari, n_ari_units, unmatched_chunks,
    cross_chunk_units, uncovered_units, na_reason}}}。
    """
    stream = ann["stream"]
    text_units = [u for u in ann["units"] if u["char_span"] is not None]
    seg_ids = [u["gold_segment_id"] for u in text_units]
    na_by_param = na_by_param or {}
    results = {}
    for p in params:
        if p in na_by_param:
            results[p] = {"ari": None, "n_ari_units": 0,
                          "unmatched_chunks": 0, "cross_chunk_units": 0,
                          "uncovered_units": len(text_units),
                          "na_reason": na_by_param[p]}
            continue
        chunks = [c for c in (fold_ws(t) for t in chunks_by_param[p]) if c]
        chunks = [c for c in chunks if c]
        proj = project_chunks_to_units(chunks, stream, text_units)
        labels = [proj.attributions.get(u["unit_id"]) for u in text_units]
        ari, _stats = ari_units_vs_chunks(seg_ids, labels)
        results[p] = {
            "ari": ari,
            "n_ari_units": sum(1 for x in labels if x is not None),
            "unmatched_chunks": len(proj.unmatched_chunk_indexes),
            "cross_chunk_units": len(proj.cross_chunk_unit_ids),
            "uncovered_units": len(text_units) - len(proj.attributions),
            "na_reason": None,
        }
    return {
        "doc_id": ann["doc_id"],
        "chars": len(stream),
        "text_units": len(text_units),
        "nontext_units": len(ann["units"]) - len(text_units),
        "results": results,
    }


def system_macro_and_select(doc_reports, params):
    """集级 macro 表 + 选优（与基线选优同规则：macro 最大、平局取
    最小参数；全网格无任何非 N/A 值 → 选优失败返回 None）。
    """
    macro = {}
    for p in params:
        vals = [d["results"][p]["ari"] for d in doc_reports
                if d["results"][p]["ari"] is not None]
        macro[p] = sum(vals) / len(vals) if vals else None
    best_p = None
    best_v = None
    for p in sorted(macro):
        v = macro[p]
        if v is None:
            continue
        if best_v is None or v > best_v:
            best_p, best_v = p, v
    return macro, best_p, best_v


def load_preregistration(path=None):
    """加载预注册 JSON 并返回 (config, sha256)。path 缺省 = 包内冻结件。"""
    import hashlib
    import json

    if path is None:
        path = Path(__file__).resolve().parent \
            / "system_select_preregistration.json"
    raw = Path(path).read_bytes()
    return (json.loads(raw.decode("utf-8")),
            hashlib.sha256(raw).hexdigest())
