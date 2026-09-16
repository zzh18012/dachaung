# -*- coding: utf-8 -*-
"""Stage 9 批次 26：对象级抽取 P/R 指标（外部评审 R-C，G⑦ 前置件）。

预注册：stage9/extraction_preregistration.json（先于任何真实语料运行
提交）。与 system_eval 同纪律：G⑥ 冻结前不触真实 gold——本模块是
纯函数（标注 dict × 系统 elements → 指标 dict），不提供 CLI、不产生
真实评分；G⑦ 接线时按 gold revision 门禁落 CLI。

口径（评审 R-C 骨架 + 本预注册补全的匹配规则）：
- gold 对象 = 标注 nontext unit 的 nontext_ref（img:*/tab:*），家族 =
  前缀，阅读序 = units 列表序；
- 预测对象 = 系统 Document elements 中 type ∈ {image, table}（归一
  img/tab 家族），阅读序 = elements 列表序；
- 一对一匹配（家族内）：
  - PDF（gold page = 物理页；element source_locator.page）——页码
    序列 difflib 对齐（autojunk=False，匹配块内页码相等即配对），
    对插入/删除/错位稳健：gold [2,5] vs pred [5] → TP1 FN1 FP0；
  - DOCX（双方均无物理页）——家族内序数对齐（第 k 个 ↔ 第 k 个，
    TP = min(|G|,|P|)），预注册明示这是序数口径非身份口径；
- TP/FP/FN 家族内计；precision = TP/(TP+FP)（分母 0 → null +
  reason=no_predictions，评审"零预测 N/A"）；recall = TP/(TP+FN)
  （分母 0 → null + reason=no_gold_objects）；F1 任一亲代 null 即
  null——**不虚构 1.0**（Stage 2 零分母纪律）；
- 文档级 N/A（parse_failed:<code> / empty_result / annotation_invalid）
  → 全家族 null + reason，聚合时计数披露不静默剔除；
- 聚合：format（pdf/docx）× domain（academic/tech_report/
  product_manual）格内家族 TP/FP/FN micro 求和后出 P/R/F1 + N/A
  文档数；不做全局单一"抽取准确率"合成分。
"""
from difflib import SequenceMatcher

FAMILY_BY_ELEMENT_TYPE = {"image": "img", "table": "tab"}
PREREGISTRATION_DEFAULT_FIELDS = ("metric", "matching_rule", "na_rules",
                                  "aggregation")


def extract_gold_objects(ann, doc_format):
    """标注 → 家族序对象列表（阅读序）。

    返回 [{"ref", "family", "key"}]；PDF key=page（int，缺页 None 降
    级为不可配对哨兵），DOCX key 恒 None（序数口径）。非法 unit 不在
    本模块职责（validator 已挡），此处 defensive 跳过非 str ref。
    """
    units = ann.get("units") if isinstance(ann, dict) else None
    out = []
    if not isinstance(units, list):
        return out
    for u in units:
        if not isinstance(u, dict) or u.get("kind") != "nontext":
            continue
        ref = u.get("nontext_ref")
        if not isinstance(ref, str) or ":" not in ref:
            continue
        family, _, _rest = ref.partition(":")
        key = u.get("page") if doc_format == "pdf" else None
        out.append({"ref": ref, "family": family,
                    "key": key if isinstance(key, int) else None})
    return out


def extract_predicted_objects(elements):
    """系统 elements → 家族序对象列表（elements 列表序）。

    接受真实 Element dataclass 或鸭子类型（.type + .source_locator
    dict）；page 取 source_locator["page"]（PDF），DOCX 元素无 page →
    key=None。非 image/table 类型不参与（预注册范围）。
    """
    out = []
    for el in elements or []:
        etype = getattr(el, "type", None)
        family = FAMILY_BY_ELEMENT_TYPE.get(etype)
        if family is None:
            continue
        locator = getattr(el, "source_locator", None) or {}
        page = locator.get("page") if isinstance(locator, dict) else None
        out.append({"family": family,
                    "key": page if isinstance(page, int) else None})
    return out


def _match_family(gold_keys, pred_keys, doc_format):
    """家族内一对一配对，返回 (tp, fp, fn)。

    PDF：页码序列 difflib 对齐（相等页码按序配对）；DOCX：序数对齐
    （第 k ↔ 第 k）。非 int 键（缺页哨兵 None）永不配对——预测缺页
    即无法主张身份，宁可 FN/FP 不虚 TP。
    """
    if doc_format == "docx":
        tp = min(len(gold_keys), len(pred_keys))
        return tp, len(pred_keys) - tp, len(gold_keys) - tp
    g = [k for k in gold_keys if isinstance(k, int)]
    p = [k for k in pred_keys if isinstance(k, int)]
    matcher = SequenceMatcher(None, g, p, autojunk=False)
    tp = sum(block.size for block in matcher.get_matching_blocks())
    fn_dropped = len(gold_keys) - len(g)
    fp_dropped = len(pred_keys) - len(p)
    return tp, (len(p) - tp) + fp_dropped, (len(g) - tp) + fn_dropped


def _prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision,
        "precision_na_reason": None if precision is not None
        else "no_predictions",
        "recall": recall,
        "recall_na_reason": None if recall is not None
        else "no_gold_objects",
        "f1": f1,
        "f1_na_reason": None if f1 is not None else "parent_na",
    }


def evaluate_extraction_doc(ann, elements, doc_format, na_reason=None):
    """单篇对象抽取评测（纯函数）。

    返回 {doc_id, families: {family: {tp,fp,fn,precision,recall,f1,
    *_na_reason}}, na_reason}。na_reason 非空 → 全家族指标 null（保留
    家族键与 reason）；家族并集 = gold ∪ pred 出现过的家族。
    """
    families = {}
    gold = extract_gold_objects(ann, doc_format)
    pred = extract_predicted_objects(elements) if na_reason is None else []
    fams = sorted({o["family"] for o in gold} |
                  {o["family"] for o in pred})
    if not fams:
        fams = ["img", "tab"]  # 双家族恒披露（零对象也是证据）
    for fam in fams:
        if na_reason is not None:
            families[fam] = {"tp": 0, "fp": 0, "fn": 0,
                             "precision": None,
                             "precision_na_reason": "doc_na",
                             "recall": None,
                             "recall_na_reason": "doc_na",
                             "f1": None, "f1_na_reason": "doc_na"}
            continue
        g_keys = [o["key"] for o in gold if o["family"] == fam]
        p_keys = [o["key"] for o in pred if o["family"] == fam]
        tp, fp, fn = _match_family(g_keys, p_keys, doc_format)
        families[fam] = _prf(tp, fp, fn)
    return {"doc_id": ann.get("doc_id"), "families": families,
            "na_reason": na_reason}


def aggregate_extraction_cells(doc_reports, docs_meta):
    """format × domain 格聚合（micro 求和家族 TP/FP/FN 后出率）。

    docs_meta：[{doc_id, format, domain}]（manifest 权威）。N/A 文档
    计入 cell 的 na_doc_count 不静默剔除；cell 无任何可评分（非 N/A）
    文档 → 该 cell P/R null + reason=no_scorable_docs。返回
    {(format, domain): {"img": {...}, "tab": {...}, "docs", "na_docs"}}。
    """
    meta_by_id = {d["doc_id"]: d for d in docs_meta
                  if isinstance(d, dict) and d.get("doc_id")}
    cells = {}
    for rep in doc_reports:
        meta = meta_by_id.get(rep["doc_id"])
        if meta is None:
            raise ValueError("aggregate 缺 manifest 元数据: %s"
                             % rep["doc_id"])
        cell_key = (meta.get("format"), meta.get("domain"))
        cell = cells.setdefault(cell_key, {
            "docs": 0, "na_docs": 0,
            "img": {"tp": 0, "fp": 0, "fn": 0},
            "tab": {"tp": 0, "fp": 0, "fn": 0},
        })
        cell["docs"] += 1
        if rep["na_reason"] is not None:
            cell["na_docs"] += 1
            continue
        for fam, m in rep["families"].items():
            if fam in cell:
                for k in ("tp", "fp", "fn"):
                    cell[fam][k] += m[k]
    for cell_key, cell in cells.items():
        for fam in ("img", "tab"):
            counts = cell[fam]
            prf = _prf(counts["tp"], counts["fp"], counts["fn"])
            if cell["docs"] - cell["na_docs"] <= 0 and \
                    prf["precision"] is None:
                prf["precision_na_reason"] = "no_scorable_docs"
                prf["recall_na_reason"] = "no_scorable_docs"
                prf["f1_na_reason"] = "no_scorable_docs"
            cell[fam] = {"tp": counts["tp"], "fp": counts["fp"],
                         "fn": counts["fn"], **{
                             k: prf[k] for k in
                             ("precision", "precision_na_reason",
                              "recall", "recall_na_reason",
                              "f1", "f1_na_reason")}}
    return cells


def load_extraction_preregistration(path=None):
    """加载抽取指标预注册 JSON，返回 (config, sha256)。"""
    import hashlib
    import json
    from pathlib import Path

    if path is None:
        path = Path(__file__).resolve().parent \
            / "extraction_preregistration.json"
    raw = Path(path).read_bytes()
    config = json.loads(raw.decode("utf-8"))
    missing = [k for k in PREREGISTRATION_DEFAULT_FIELDS
               if k not in config]
    if missing:
        raise ValueError("预注册缺字段: %s" % missing)
    return config, hashlib.sha256(raw).hexdigest()
