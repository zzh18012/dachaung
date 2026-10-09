# -*- coding: utf-8 -*-
"""r83 Q4 Phase 1 gold evaluation baseline（stage9-eval-baseline-r1）。

Layer A extraction：evaluation.cli（冻结 runner，零改动）逐 parser 跑 24 核心
docs；chunk_boundary_anchors 由 gold 硬边界诚实派生（唯一可从 gold 直接派生
的 devset 制式字段；figure/table caption pairs 与 heading_order 不派生——
gold 无对应直接表示，强派生即启发式捏造）。
Layer B gold alignment（本脚本，系统性能口径；与 agreement 冻结算法分立实
现、不混算）：
  - unit alignment accuracy（全 24 篇；严格 normalize 相等一对一贪心对齐，
    sentence-gold vs paragraph-pred 的粒度天花板如实披露）
  - extraction coverage（gold 文本单元在预测规范化流中的子串覆盖率）
  - nontext detection（gold nontext 对象 vs 预测 image/table 元素，家族+页）
  - boundary error rate（gold 硬边界 vs 预测 chunk 边界，容差 30 chars，
    流中不可定位的 anchor 单独计 not_extracted 不入分母）
  - relation edge P/R + anchor classification accuracy（仅 acad-03：gold a
    侧全语料链接通道为零（24 篇清点），金标准 = credential 绑定抽查记录
    review/rec-acad-03-layoutlmv3.json 的 20 条边；范围限定如实披露）
产物：samples/private/stage9-corpus/evaluation/stage9-eval-baseline-r1/
（gitignored，不进 freeze 包）。每输出绑定 gold_revision + evaluation_revision
+ parser_revision（r83 Q4-6）。
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CORPUS = BASE / "samples" / "private" / "stage9-corpus"
OUT = CORPUS / "evaluation" / "stage9-eval-baseline-r1"
GOLD_REV = "stage9-b26-gold-r1"
FREEZE_REV = "stage9-g6-freeze-r1"
EVAL_REV = "stage9-eval-baseline-r1"
PARSERS = ["fallback", "kreuzberg"]
MAX_CHARS = 800
TOLERANCE = 30
MARKER_MAX = 40
SPOTCHECK_POS = CORPUS / "review" / "rec-acad-03-layoutlmv3.json"
ANCHOR_DOC = "acad-03-layoutlmv3"
R1_METRICS = CORPUS / "evaluation" / "stage9-eval-baseline-r1" / "metrics.json"
GATE_REL_DROP = 0.05  # comparison 回归门阈值：相对下降 >5% 判 regression
PARSER_CODE_REVS = {
    "stage9-eval-baseline-r1": "main 6c6d398（pre-W1）",
    "stage9-eval-baseline-r2": ("main ee80799（W1 caption delimiter fix；"
                                "adoption cherry-pick 0e5f1d4）"),
}

sys.path.insert(0, str(BASE))
from app.chunkers.structural import normalize_text  # noqa: E402


def norm(s):
    return normalize_text(s or "")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(json.dumps(
        obj, ensure_ascii=False, indent=1).encode("utf-8"))


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def null_metric(reason):
    return {"value": None, "reason": reason}


def ratio(v):
    return {"value": round(v, 4), "reason": None}


def core_docs():
    cm = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    return [d for d in cm["docs"] if d.get("split")]


def gold_of(doc_id):
    return json.loads(
        (CORPUS / "annotations" / (doc_id + ".json")).read_text(
            encoding="utf-8"))


def unit_marker(gold, unit):
    cs = unit.get("char_span")
    if not cs:
        return None
    return norm(gold["stream"][cs[0]:cs[1]])[:MARKER_MAX]


def hb_units(gold):
    out = []
    for i, u in enumerate(gold["units"]):
        if u["kind"] == "nontext" or not u.get("hard_boundary_before"):
            continue
        if i == 0:
            continue
        out.append(u)
    return out


# ---------------- prepare ----------------

def cmd_prepare():
    devset = json.loads(
        (BASE / "samples" / "private" / "devset" / "manifest.json")
        .read_text(encoding="utf-8"))
    mv = devset["manifest_version"]
    docs = []
    for d in core_docs():
        doc_id = d["doc_id"]
        ext = "pdf" if d["format"] == "pdf" else "docx"
        gold = gold_of(doc_id)
        anchors = []
        for u in hb_units(gold):
            m = unit_marker(gold, u)
            if m and len(m) >= 8:
                anchors.append({"marker": m, "position": "before"})
        write_json(OUT / "derived_annotations" / (doc_id + ".json"), {
            "doc_id": doc_id,
            "derived_from": "stage9-corpus gold a-side (G6 FROZEN)",
            "gold_annotation_sha256": sha(CORPUS / "annotations" /
                                          (doc_id + ".json")),
            "derivation": ("hard_boundary_before 文本单元 -> "
                           "chunk_boundary_anchors（marker=单元规范化文本"
                           "前 40 字符，position=before；首单元不计）"),
            "chunk_boundary_anchors": anchors,
        })
        docs.append({
            "doc_id": doc_id,
            "path": "samples/private/stage9-corpus/files/%s.%s" % (doc_id, ext),
            "source_type": ext,
            "sha256": d["sha256"],
            "categories": [d["domain"], d["split"], d["format"]],
            "annotation_file": ("samples/private/stage9-corpus/evaluation/"
                                "%s/derived_annotations/%s.json"
                                % (EVAL_REV, doc_id)),
        })
    write_json(OUT / "manifest.json", {
        "manifest_version": mv,
        "devset_status": "complete",
        "documents": docs,
        "expected_failures": [],
    })
    total_hb = sum(len(hb_units(gold_of(d["doc_id"]))) for d in core_docs())
    print(json.dumps({"step": "prepare", "docs": len(docs),
                      "total_hard_boundaries": total_hb,
                      "manifest_version": mv}))


# ---------------- layer A ----------------

def cmd_layera():
    py = str(BASE / ".venv" / "Scripts" / "python.exe")
    audit = []
    for p in PARSERS:
        outp = OUT / ("layerA_%s.json" % p)
        r = subprocess.run(
            [py, "-m", "evaluation.cli", "run",
             "--manifest", str(OUT / "manifest.json"),
             "--output", str(outp), "--parser", p,
             "--max-chars", str(MAX_CHARS)],
            cwd=str(BASE), capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        v = subprocess.run(
            [py, "-m", "evaluation.cli", "validate-report", str(outp)],
            cwd=str(BASE), capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        audit.append({"parser": p, "run_rc": r.returncode,
                      "run_stderr_tail": (r.stderr or "")[-400:],
                      "validate_rc": v.returncode,
                      "validate_stdout_tail": (v.stdout or "")[-200:]})
        print(json.dumps({"step": "layerA", "parser": p,
                          "run_rc": r.returncode,
                          "validate_rc": v.returncode}))
    write_json(OUT / "layerA_audit.json", {
        "generated_at": now_utc(), "max_chars": MAX_CHARS, "audit": audit})


# ---------------- layer B ----------------

def element_page(el):
    loc = el.get("source_locator") or {}
    if isinstance(loc, dict):
        p = loc.get("page")
        if isinstance(p, int):
            return p
    return None


def layerb_metrics(doc_id, gold, document):
    els = document.get("elements") or []
    relations = document.get("relations") or []
    units = gold["units"]
    m = {"doc_id": doc_id}

    # -- unit alignment（严格 normalize 相等，一对一按序贪心）--
    text_els = [e for e in els if e.get("type") in
                ("heading", "paragraph", "list_item", "caption")
                and isinstance(e.get("content"), str)]
    el_norm = [norm(e["content"]) for e in text_els]
    by_text = {}
    for i, t in enumerate(el_norm):
        if t:
            by_text.setdefault(t, []).append(i)
    used = set()
    text_units = [u for u in units if u["kind"] != "nontext"
                  and u.get("char_span")]
    aligned = 0
    kind_correct = 0
    aligned_kinds = {"heading": 0, "sentence": 0}
    for u in text_units:
        ut = norm(gold["stream"][u["char_span"][0]:u["char_span"][1]])
        cands = [i for i in by_text.get(ut, []) if i not in used]
        if not cands:
            continue
        i = cands[0]
        used.add(i)
        aligned += 1
        aligned_kinds[u["kind"]] = aligned_kinds.get(u["kind"], 0) + 1
        et = text_els[i].get("type")
        ok = ((u["kind"] == "heading" and et == "heading") or
              (u["kind"] == "sentence" and et in
               ("paragraph", "list_item", "caption")))
        if ok:
            kind_correct += 1
    m["unit_alignment"] = {
        "text_units": len(text_units),
        "aligned_pairs": aligned,
        "aligned_by_gold_kind": aligned_kinds,
        "kind_correct": kind_correct,
        "unit_alignment_accuracy": (
            ratio(kind_correct / aligned) if aligned else
            null_metric("no_aligned_pairs")),
        "granularity_note": ("gold=heading/sentence 粒度 vs 预测=块级元素"
                             "（paragraph 等），严格相等对齐只对短单元（标题/"
                             "单句段）可能命中——结构性天花板，非实现缺陷"),
    }

    # -- extraction coverage --
    joined = norm(" ".join(t for t in el_norm if t))
    covered = 0
    not_extracted_units = 0
    for u in text_units:
        ut = norm(gold["stream"][u["char_span"][0]:u["char_span"][1]])
        if not ut:
            continue
        if ut in joined:
            covered += 1
        else:
            not_extracted_units += 1
    denom = covered + not_extracted_units
    m["extraction_coverage"] = {
        "denominator": denom,
        "covered": covered,
        "coverage": ratio(covered / denom) if denom else
        null_metric("no_text_units"),
        "not_extracted_units": not_extracted_units,
    }

    # -- nontext detection（家族+页）--
    fam_of = {"img": "image", "tab": "table"}
    nts = [u for u in units if u["kind"] == "nontext"]
    pred_imgs = [e for e in els if e.get("type") == "image"]
    pred_tabs = [e for e in els if e.get("type") == "table"]
    detected = 0
    for u in nts:
        ref = u.get("nontext_ref") or ""
        fam = fam_of.get(ref.split(":")[0], None)
        pool = pred_imgs if fam == "image" else (
            pred_tabs if fam == "table" else pred_imgs + pred_tabs)
        pages = [element_page(e) for e in pool]
        upage = u.get("page")
        hit = any(
            (upage is None or pp is None or pp == upage) for pp in pages)
        if hit:
            detected += 1
    m["nontext_detection"] = {
        "gold_nontext_objects": len(nts),
        "predicted_images": len(pred_imgs),
        "predicted_tables": len(pred_tabs),
        "detected": detected,
        "detection_ratio": (
            ratio(detected / len(nts)) if nts else
            null_metric("no_gold_nontext")),
        "match_rule": ("ref 家族 img->image / tab->table；页相等（任一侧页"
                       "缺失则忽略页条件）"),
    }

    # -- boundary error rate --
    chunks = document.get("chunks") or []
    hbs = hb_units(gold)
    if len(chunks) >= 2 and joined:
        cs = [norm(c.get("text") or "") for c in chunks]
        stream = norm(" ".join(t for t in cs if t))
        boundaries = []
        pos = 0
        for i, t in enumerate(cs):
            if i == len(cs) - 1 or not t:
                continue
            fp = stream.find(t, pos)
            if fp < 0:
                pos += len(t) + 1
                continue
            boundaries.append(fp + len(t))
            pos = fp + len(t) + 1
        matched = 0
        missing = 0
        not_extracted = 0
        for u in hbs:
            mk = unit_marker(gold, u)
            if not mk:
                continue
            fp = stream.find(mk)
            if fp < 0:
                not_extracted += 1
                continue
            if any(abs(b - fp) <= TOLERANCE for b in boundaries):
                matched += 1
            else:
                missing += 1
        dm = matched + missing
        m["boundary_error_rate"] = {
            "gold_hard_boundaries": len(hbs),
            "matched_within_tolerance": matched,
            "missing": missing,
            "not_extracted": not_extracted,
            "tolerance_chars": TOLERANCE,
            "boundary_error_rate": (
                ratio(missing / dm) if dm else
                null_metric("no_located_boundaries")),
        }
    else:
        m["boundary_error_rate"] = {
            "gold_hard_boundaries": len(hbs),
            "boundary_error_rate": null_metric("no_predicted_chunks"),
        }

    # -- relation edges（Layer C graph layer）+ anchor classification
    #    （仅 acad-03；r85 Q3：edge P/R/F1 与结构层 unit_alignment 分立）--
    if doc_id == ANCHOR_DOC:
        rec = json.loads(SPOTCHECK_POS.read_text(encoding="utf-8"))
        edges = rec["edge_classifications"]
        by_id = {e.get("element_id"): e for e in els}
        cap_els = []   # has_caption / table_has_caption（from=图/表 → to=题注）
        ref_els = []   # references_figure / references_table（from=文本 → to=图/表）
        for rel in relations:
            t = rel.get("type")
            if t not in ("has_caption", "table_has_caption",
                         "references_figure", "references_table"):
                continue
            src = by_id.get(rel.get("from_id"))
            dst = by_id.get(rel.get("to_id"))
            if src is None or dst is None:
                continue
            (cap_els if t in ("has_caption", "table_has_caption")
             else ref_els).append((src, dst))
        matched_caption = 0
        matched_reference = 0
        used_c = set()
        used_r = set()
        anchor_hits = []
        for ed in edges:
            mk = unit_marker(gold, next(
                u for u in units if u["unit_id"] == ed["unit_id"]))
            fam = "image" if ed["nontext_ref"].startswith("img") else "table"
            is_cap = ed["anchor_kind"] == "caption"
            # caption 边：from 侧图/表家族 + gold 题注单元 marker ⊂ to.content
            # explicit 边：to 侧图/表家族 + gold 引用句 marker ⊂ from.content
            pool, used = (cap_els, used_c) if is_cap else (ref_els, used_r)
            hit = None
            for pi, (src, dst) in enumerate(pool):
                if pi in used:
                    continue
                if is_cap:
                    if src.get("type") != fam:
                        continue
                    if mk and mk in norm(dst.get("content") or ""):
                        hit = pi
                        break
                else:
                    if dst.get("type") != fam:
                        continue
                    if mk and mk in norm(src.get("content") or ""):
                        hit = pi
                        break
            if hit is not None:
                used.add(hit)
                if is_cap:
                    matched_caption += 1
                else:
                    matched_reference += 1
                anchor_hits.append(True)
            else:
                anchor_hits.append(None)
        matched_edges = matched_caption + matched_reference
        pred_total = len(cap_els) + len(ref_els)
        p_val = (matched_edges / pred_total) if pred_total else None
        r_val = (matched_edges / len(edges)) if edges else None
        f_val = (2 * p_val * r_val / (p_val + r_val)
                 if p_val is not None and r_val is not None and
                 (p_val + r_val) > 0 else None)
        gold_caps = sum(1 for e in edges if e["anchor_kind"] == "caption")
        gold_refs = len(edges) - gold_caps
        m["relation_edges"] = {
            "layer": "C（graph layer；r85 Q3 与结构层分立报告）",
            "scope": ("仅 acad-03：gold a 侧链接通道 24 篇全零，金标准 = "
                      "credential 绑定抽查记录 20 边（题注 %d + 显式引用 %d；"
                      "勘误后权威计数，errata REC_ACAD03_BASIS_COUNT_ERRATA）"
                      % (gold_caps, gold_refs)),
            "gold_edges_caption": gold_caps,
            "gold_edges_reference": gold_refs,
            "predicted_caption_edges": len(cap_els),
            "predicted_reference_edges": len(ref_els),
            "matched_caption": matched_caption,
            "matched_reference": matched_reference,
            "match_rule": ("caption：from∈{image,table} 家族 + marker⊂to"
                           "(题注).content；explicit：to∈{image,table} 家族"
                           " + marker⊂from(文本).content；各自一对一贪心"),
            "relation_edge_precision": (
                ratio(p_val) if pred_total else
                null_metric("no_predicted_relations")),
            "relation_edge_recall": (
                ratio(r_val) if edges else null_metric("no_gold_edges")),
            "relation_edge_F1": (
                ratio(f_val) if f_val is not None else
                null_metric("zero_precision_recall_sum")),
        }
        pred_caption_flags = []
        for ed, hit in zip(edges, anchor_hits):
            if hit is None:
                pred_caption_flags.append(None)
            else:
                pred_caption_flags.append(True)
        # 未被任何预测边覆盖的 gold 单元：系统未给出题注判断 -> False
        pred_caption_flags = [
            (f if f is not None else False)
            for f in pred_caption_flags]
        gold_caption_flags = [
            ed["anchor_kind"] == "caption" for ed in edges]
        correct = sum(1 for p, g in zip(pred_caption_flags,
                                        gold_caption_flags) if p == g)
        m["anchor_classification"] = {
            "scope": "仅 acad-03（20 分类锚；显式引用无对应预测 relation "
                     "类型——系统只可能经 has_caption 表达题注判断，recall "
                     "天花板结构性受限，此处报分类一致率）",
            "units": len(edges),
            "correct": correct,
            "accuracy": ratio(correct / len(edges)) if edges else
            null_metric("no_gold_anchors"),
        }
    return m


def cmd_layerb():
    from app.pipeline import process_single
    parser_versions = {}
    per_doc = {p: [] for p in PARSERS}
    failures = []
    for d in core_docs():
        doc_id = d["doc_id"]
        ext = "pdf" if d["format"] == "pdf" else "docx"
        src = CORPUS / "files" / (doc_id + "." + ext)
        gold = gold_of(doc_id)
        for p in PARSERS:
            outp = OUT / "parsed" / p / (doc_id + ".json")
            outp.parent.mkdir(parents=True, exist_ok=True)
            t0 = time.perf_counter()
            document, errors = process_single(
                src, outp, parser_name=p, max_chars=MAX_CHARS,
                write_json=True)
            wall = round(time.perf_counter() - t0, 2)
            if errors or document is None:
                code = errors[0].code if errors else "unknown"
                failures.append({
                    "doc_id": doc_id, "parser": p, "error_code": code,
                    "class": "PARSER_FAILURE",
                    "message": errors[0].message if errors else None,
                })
                per_doc[p].append({
                    "doc_id": doc_id, "split": d["split"],
                    "layerB": {"pipeline_failed": code}})
                print(json.dumps({"doc": doc_id, "parser": p,
                                  "FAILED": code}))
                continue
            dd = document.to_dict()
            parser_versions[p] = document.parser_version
            metrics = layerb_metrics(doc_id, gold, dd)
            metrics["split"] = d["split"]
            metrics["wall_seconds"] = wall
            per_doc[p].append(metrics)
            print(json.dumps({
                "doc": doc_id, "parser": p, "wall": wall,
                "acc": metrics["unit_alignment"]
                ["unit_alignment_accuracy"]["value"],
                "cov": metrics["extraction_coverage"]["coverage"]["value"],
                "ber": metrics["boundary_error_rate"].get(
                    "boundary_error_rate", {}).get("value")}))
    write_json(OUT / "layerB_per_doc_raw.json", {
        "generated_at": now_utc(), "parser_versions": parser_versions,
        "per_doc": per_doc, "failures": failures})
    print(json.dumps({"step": "layerB", "parser_versions": parser_versions,
                      "failures": len(failures)}))


# ---------------- aggregate ----------------

def macro(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return null_metric("no_evaluated_docs")
    return ratio(sum(vals) / len(vals))


def dig(metric_block, *keys):
    cur = metric_block
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur.get("value") if isinstance(cur, dict) else None


def cmd_aggregate():
    raw = json.loads((OUT / "layerB_per_doc_raw.json").read_text(
        encoding="utf-8"))
    splits = ["dev", "comparison", "holdout"]
    agg = {}
    for p in PARSERS:
        docs = raw["per_doc"][p]
        per_split = {}
        for sp in splits + ["overall"]:
            sel = [d for d in docs if sp == "overall" or
                   d.get("split") == sp]
            per_split[sp] = {
                "doc_count": len(sel),
                "unit_alignment_accuracy": macro([
                    dig(d, "unit_alignment", "unit_alignment_accuracy")
                    for d in sel if "unit_alignment" in d]),
                "extraction_coverage": macro([
                    dig(d, "extraction_coverage", "coverage")
                    for d in sel if "extraction_coverage" in d]),
                "nontext_detection_ratio": macro([
                    dig(d, "nontext_detection", "detection_ratio")
                    for d in sel if "nontext_detection" in d]),
                "boundary_error_rate": macro([
                    dig(d, "boundary_error_rate", "boundary_error_rate")
                    for d in sel if "boundary_error_rate" in d]),
            }
        anchor_docs = [d for d in docs if "relation_edges" in d]
        per_split["layerC_relation_evaluation"] = {
            "layer": "C（graph layer，与结构层 unit_alignment 分立报告，"
                     "r85 Q3）",
            "scope": "仅 acad-03（credential 抽查 20 边；gold 链接通道全零）",
            "relation_edge_precision": macro([
                dig(d, "relation_edges", "relation_edge_precision")
                for d in anchor_docs]),
            "relation_edge_recall": macro([
                dig(d, "relation_edges", "relation_edge_recall")
                for d in anchor_docs]),
            "relation_edge_F1": macro([
                dig(d, "relation_edges", "relation_edge_F1")
                for d in anchor_docs]),
            "anchor_classification_accuracy": macro([
                dig(d, "anchor_classification", "accuracy")
                for d in anchor_docs]),
        }
        if p == "kreuzberg":
            per_split["comparison_only"] = True  # r84 Q4
        agg[p] = per_split
    write_json(OUT / "metrics.json", {
        "evaluation_revision": EVAL_REV,
        "gold_revision": GOLD_REV,
        "freeze_revision": FREEZE_REV,
        "parser_revisions": raw["parser_versions"],
        "parser_code_revision": PARSER_CODE_REVS.get(EVAL_REV),
        "generated_at": now_utc(),
        "layerB": agg,
    })

    per_doc_results = {}
    for p in PARSERS:
        la = json.loads((OUT / ("layerA_%s.json" % p)).read_text(
            encoding="utf-8"))
        la_by_id = {r["doc_id"]: r for r in la.get("per_doc", [])}
        rows = []
        for d in raw["per_doc"][p]:
            row = {"doc_id": d["doc_id"], "split": d.get("split")}
            row["layerA"] = la_by_id.get(d["doc_id"])
            row["layerB"] = d
            rows.append(row)
        per_doc_results[p] = rows
    write_json(OUT / "per_doc_results.json", {
        "evaluation_revision": EVAL_REV,
        "gold_revision": GOLD_REV,
        "per_parser": per_doc_results,
    })

    system_errors = list(raw["failures"])
    for p in PARSERS:
        for d in raw["per_doc"][p]:
            if "extraction_coverage" not in d:
                continue
            ne = d["extraction_coverage"]["not_extracted_units"]
            if ne > 0:
                system_errors.append({
                    "doc_id": d["doc_id"], "parser": p,
                    "class": "NORMALIZATION_FAILURE",
                    "count": ne,
                    "note": "gold 文本单元未在预测规范化流中定位",
                })
            rel = d.get("relation_edges")
            if rel and rel["predicted_caption_edges"] == 0:
                system_errors.append({
                    "doc_id": d["doc_id"], "parser": p,
                    "class": "LINKING_FAILURE",
                    "note": "gold 有锚边（抽查记录）而预测零题注 relation",
                })
    write_json(OUT / "error_registry.json", {
        "evaluation_revision": EVAL_REV,
        "system_error_taxonomy": ["PARSER_FAILURE", "LINKING_FAILURE",
                                  "NORMALIZATION_FAILURE"],
        "system_errors": system_errors,
        "gold_disagreement_taxonomy_reference": {
            "classes": ["GRANULARITY", "RULE_NON_APPLICATION",
                        "PLAN_DEFICIENCY", "RENUMBERING",
                        "NAMING_NON_COMPARABLE", "BORDER_JUDGMENT"],
            "record": "samples/private/stage9-corpus/freeze/arbitration/"
                      "R-D-arbitration-v1.json（G⑥ freeze 包内）",
            "note": "gold 分歧六类与系统错误三类分层登记，不混入同一统计"
                    "字段（r83 Q4-4）",
        },
    })

    write_json(OUT / "config.json", {
        "evaluation_revision": EVAL_REV,
        "gold_revision": GOLD_REV,
        "freeze_revision": FREEZE_REV,
        "ruling_source": ("r83 Q4（r1 首测）；r85 Q4（r2 = W1 merge 触发"
                          "全量重测）" if EVAL_REV.endswith("r2") else
                          "r83 Q4（AUTHORIZED 直接执行）"),
        "runner": "evaluation.cli（Layer A 冻结 runner）+ 本脚本 Layer B/C",
        "parsers": PARSERS,
        "max_chars": MAX_CHARS,
        "tolerance_chars": TOLERANCE,
        "marker_max_chars": MARKER_MAX,
        "splits": {"dev": "允许调参", "comparison": "禁止调参（回归门）",
                   "holdout": "盲评，禁止查看反馈（r2 为 W1 后重测，"
                              "盲评纪律不变，不得用于 W1/W2 调参）"},
        "parser_revisions": raw["parser_versions"],
        "parser_code_revision": PARSER_CODE_REVS.get(EVAL_REV),
        "kreuzberg_role": "registered stable comparator（comparison_only，"
                          "r84 Q4）",
        "generated_at": now_utc(),
    })
    print(json.dumps({"step": "aggregate", "parsers": PARSERS,
                      "system_errors": len(system_errors)}))


# ---------------- comparison regression gate（r84 Q1 首战，r85 Q4）--

def cmd_gate():
    r1 = json.loads(R1_METRICS.read_text(encoding="utf-8"))
    r2 = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    keys = ["unit_alignment_accuracy", "extraction_coverage",
            "nontext_detection_ratio", "boundary_error_rate"]
    rows = []
    regressions = 0
    for sp in ("comparison", "overall", "holdout"):
        for k in keys:
            v1 = r1["layerB"]["fallback"][sp][k]["value"]
            v2 = r2["layerB"]["fallback"][sp][k]["value"]
            if v1 is None or v2 is None:
                rows.append({"split": sp, "metric": k, "r1": v1, "r2": v2,
                             "delta": None, "relative_delta": None,
                             "verdict": "n/a_null_metric"})
                continue
            rel = (v2 - v1) / v1 if v1 else None
            # boundary_error_rate 越低越好
            lower_better = k == "boundary_error_rate"
            reg = (rel < -GATE_REL_DROP if not lower_better
                   else rel > GATE_REL_DROP)
            verdict = ("regression" if reg else
                       "improved" if rel and (rel > 0) != lower_better
                       else "ok")
            if reg and sp == "comparison":
                regressions += 1
            rows.append({"split": sp, "metric": k, "r1": v1, "r2": v2,
                         "delta": round(v2 - v1, 4),
                         "relative_delta": (
                             round(rel, 4) if rel is not None else None),
                         "verdict": verdict, "gated": sp == "comparison"})
    layer_c = []
    for k in ("relation_edge_precision", "relation_edge_recall",
              "relation_edge_F1"):
        v1 = (r1["layerB"]["fallback"]
              .get("anchor_scope_acad03", {}).get(
                  {"relation_edge_precision": "edge_precision",
                   "relation_edge_recall": "edge_recall"}.get(k, k), {})
              or {}).get("value") if k != "relation_edge_F1" else None
        v2 = (r2["layerB"]["fallback"]["layerC_relation_evaluation"]
              .get(k, {}) or {}).get("value")
        layer_c.append({"metric": k, "r1": v1, "r2": v2})
    write_json(OUT / "comparison_gate.json", {
        "gate": "comparison 回归门（r84 Q1 (a)；r85 Q4 首次实战）",
        "baseline": r1["evaluation_revision"],
        "candidate": r2["evaluation_revision"],
        "threshold": (f"核心指标相对劣化 >{round(GATE_REL_DROP * 100)}% 判 regression"
                      "（沿 r84 revision 升版条件 B 的 5% 精度；数值阈值为 "
                      "coordinator 选择，裁决未见明文，如实披露）"),
        "gated_split": "comparison",
        "informational_splits": ["overall", "holdout（盲评，不入门）"],
        "overall_verdict": "PASS" if regressions == 0 else "FAIL",
        "regression_count": regressions,
        "metrics": rows,
        "layerC_informational": layer_c,
        "generated_at": now_utc(),
    })
    print(json.dumps({"step": "gate", "verdict":
                      "PASS" if regressions == 0 else "FAIL",
                      "regressions": regressions}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True,
                    choices=["prepare", "layera", "layerb", "aggregate",
                             "gate"])
    ap.add_argument("--revision", default="stage9-eval-baseline-r1")
    a = ap.parse_args()
    g = globals()
    g["EVAL_REV"] = a.revision
    g["OUT"] = CORPUS / "evaluation" / a.revision
    {"prepare": cmd_prepare, "layera": cmd_layera, "layerb": cmd_layerb,
     "aggregate": cmd_aggregate, "gate": cmd_gate}[a.step]()


if __name__ == "__main__":
    main()
