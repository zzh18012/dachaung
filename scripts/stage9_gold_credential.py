# -*- coding: utf-8 -*-
"""Stage 9 批次 26：G⑥ gold freeze 凭证机械组装 CLI（等待期并行件）。

格式来源（预裁定，勿改语义；工具只组装不裁决）：
- 凭证格式与 G⑥ 封口顺序：docs/stage9-annotation-guide.md §7.3
  （五轮裁决 C 锁定，ADOPTION.md §八十四）；
- relation_spotcheck 字段：十轮裁决 R3 锁定格式；
- 逐文件 hash 与 gold_digest：复用 stage9.system_eval.compute_gold_digest
  （单一实现，不复制聚合逻辑）；
- 单篇校验：复用 stage9.validation（与 stage9_validate_annotations.py
  同一实现——validator 在最终 gold 字节状态现场重跑，不只信任历史运行）。

G⑥ 封口顺序的机械可执行部分（§7.3，不得倒置）：
manifest 冻结校验 → core 集确定（恰 24）→ 最终 validator（24 core
逐篇 + manifest 一致性）→ 24 篇逐文件 hash → gold_digest → 双标注
记录装配（恰 4，decision 须闭合）→ relation 抽查记录校验（≥2）→
抽查覆盖门禁（外部评审 R-D：r10 R3 audit_type 词汇表、domain ≥2、
positive 逐边全查、negative anchorless 计数、defects/corrections
闭环——从最终 gold 字节现场重算）→ 组装 credential → 写盘（已存在
即拒，immutable：r2 须新裁决不得覆盖 r1）→ 输出 credential 字节
sha256（外部台账登记；不写入自身，非自指）。

用法（项目 venv python；G⑥ 双前置闭合后执行）：
  python scripts/stage9_gold_credential.py \
      --manifest samples/private/stage9-corpus/manifest.json \
      --expected-manifest-sha 51d3d400… \
      --annotations samples/private/stage9-corpus/annotations \
      --agreement-report tech-03-report.json --agreement-report …（×4）\
      --secondary tech-03-…=samples/private/stage9-corpus/annotations-user/….json …（×4）\
      [--arbitration <doc_id>=resolved …] \
      --spotcheck rec-prod-05.json --spotcheck rec-tech-01.json …（≥2）\
      --validator-commit <sha> --agreement-commit 1817d3b… \
      [--gold-revision stage9-b26-gold-r1] [--out <path>] [--dry-run]

退出码：0 = 凭证写出（或 --dry-run 演练通过）；1 = gold 状态不干净
（最终 validator 存在失败——须先处理再冻结，不写盘）；2 = 输入/门禁
错误（冻结校验不符、core 集不完整、decision 未闭合、字段缺失、
目标文件已存在等，不写盘）。
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.system_eval import compute_gold_digest  # noqa: E402
from stage9.validation import (  # noqa: E402
    compute_link_stats,
    load_json,
    validate_annotation,
    validate_manifest_consistency,
)

CORE_SPLITS = ("dev", "comparison", "holdout")
CORE_DOC_COUNT = 24          # G④ 冻结核心集规模（manifest 为权威，不符即拒）
DOUBLE_ANNOTATION_COUNT = 4  # G⑤ 四篇双标注
SPOTCHECK_MIN = 2            # r10 R3：relation 专项抽查下限
ARBITRATION_CONVERGED = ("resolved", "converged")
_LINK_KEYS = ("linked_pairs", "linked_objects", "anchorless_count",
              "nontext_total")
_SPOTCHECK_REQUIRED = ("doc_id", "annotation_sha256_reviewed", "audit_type",
                       "checked_count", "result", "review_date")
_SPOTCHECK_RESULTS = ("pass", "defects_found")
_SPOTCHECK_AUDIT_TYPES = ("positive", "negative")  # r10 R3 词汇表
DOMAIN_MIN = 2               # 指南 G⑥ 前置 3：抽查覆盖 ≥2 个 domain
ANCHORLESS_MIN = 10          # 指南：每篇 ≥10 anchorless（不足 10 全查）


def _err(msg):
    print("gold credential 门禁失败：%s" % msg, file=sys.stderr)


def _load(path, what):
    try:
        return load_json(Path(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("%s 读取失败 %s: %s" % (what, path, exc))


def _doc_link_sets(data):
    """R-D 机械核对：从最终标注字节现场提取 relation 引用集合。

    positive_refs = 出现在任一 unit linked_nontext 的引用（有入边对象）；
    anchorless_refs = nontext 对象中无入边者（与 compute_link_stats
    同口径，但保留对象身份供覆盖比对）；unit_linked = unit_id → 该
    unit 声明的 linked_nontext 原样列表（推导 checked 边覆盖）。
    """
    units = data.get("units") if isinstance(data, dict) else None
    positive, nontext_all, unit_linked = set(), set(), {}
    if not isinstance(units, list):
        return positive, nontext_all - positive, unit_linked
    for u in units:
        if not isinstance(u, dict):
            continue
        if u.get("kind") == "nontext" and \
                isinstance(u.get("nontext_ref"), str):
            nontext_all.add(u["nontext_ref"])
        linked = u.get("linked_nontext")
        if isinstance(linked, list):
            refs = [r for r in linked if isinstance(r, str)]
            unit_linked[u.get("unit_id")] = refs
            positive.update(refs)
    return positive, nontext_all - positive, unit_linked


def _parse_pairs(items, what):
    out = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key or not value:
            raise ValueError("%s 形如 DOC_ID=值，收到: %r" % (what, item))
        if key in out:
            raise ValueError("%s 重复 doc_id: %s" % (what, key))
        out[key] = value
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="G⑥ gold freeze 凭证机械组装（格式预裁定见 "
                    "docs/stage9-annotation-guide.md §7.3；本工具不裁决、"
                    "不修改任何标注字节）")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-manifest-sha", required=True,
                        help="G④ 冻结 manifest 字节 sha256")
    parser.add_argument("--annotations", required=True,
                        help="核心集标注目录（<doc_id>.json）")
    parser.add_argument("--agreement-report", action="append",
                        required=True,
                        help="stage9_agreement.py --json 报告（恰 %d 份）"
                             % DOUBLE_ANNOTATION_COUNT)
    parser.add_argument("--secondary", action="append", required=True,
                        metavar="DOC_ID=PATH",
                        help="第二标注人交回 JSON（恰 %d 份，计算 "
                             "secondary_annotation_sha256）"
                             % DOUBLE_ANNOTATION_COUNT)
    parser.add_argument("--arbitration", action="append", default=[],
                        metavar="DOC_ID=STATUS",
                        help="已完成人工仲裁结果的声明（r27 D-N：仅记录、"
                             "不替代仲裁本身）；below_threshold 篇必填且须"
                             " resolved/converged，pass 篇默认 not_needed；"
                             "声明值与所引 agreement report 哈希随凭证保留")
    parser.add_argument("--spotcheck", action="append", required=True,
                        help="relation 抽查记录 JSON（r10 R3 字段，≥%d 份）"
                             % SPOTCHECK_MIN)
    parser.add_argument("--validator-commit", required=True,
                        help="validator 代码 commit（显式提供，不自动推断）")
    parser.add_argument("--agreement-commit", required=True,
                        help="agreement authoritative 实现 commit")
    parser.add_argument("--gold-revision", default="stage9-b26-gold-r1",
                        help="默认 stage9-b26-gold-r1；rN 单调，改 core gold "
                             "须重新裁决签 r2")
    parser.add_argument("--out",
                        help="凭证输出路径（默认 <manifest 目录>/"
                             "gold-freeze-credential.<rev>.json）")
    parser.add_argument("--dry-run", action="store_true",
                        help="全链校验+组装但不写盘（演练/预检）")
    args = parser.parse_args(argv)

    # ---- 步骤 1：manifest 冻结校验 ----
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        _err("manifest 不存在: %s" % manifest_path)
        return 2
    try:
        manifest_sha = hashlib.sha256(
            manifest_path.read_bytes()).hexdigest()
    except OSError as exc:
        _err("manifest 读取失败: %s" % exc)
        return 2
    if manifest_sha != args.expected_manifest_sha.strip().lower():
        _err("manifest SHA-256 与 G④ 冻结值不符（冻结层被改动须重新"
             "裁决）:\n  got      %s\n  expected %s"
             % (manifest_sha, args.expected_manifest_sha))
        return 2

    try:
        manifest_data = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        _err("manifest 解析失败: %s" % exc)
        return 2

    # ---- 步骤 2：core 集确定（恰 24）----
    docs = [d for d in manifest_data.get("docs", [])
            if isinstance(d, dict)]
    core_docs = [d for d in docs if d.get("split") in CORE_SPLITS]
    if len(core_docs) != CORE_DOC_COUNT:
        _err("core 集（split ∈ %s）须恰 %d 篇，实际 %d 篇"
             % ("/".join(CORE_SPLITS), CORE_DOC_COUNT, len(core_docs)))
        return 2
    core_ids = {d["doc_id"] for d in core_docs if d.get("doc_id")}
    if len(core_ids) != CORE_DOC_COUNT:
        _err("core 集 doc_id 不唯一/缺失")
        return 2

    # ---- 步骤 3：最终 validator（最终 gold 字节状态现场重跑）----
    manifest_index = {d.get("doc_id"): d for d in docs}
    failures = []
    for fail in validate_manifest_consistency(manifest_data):
        failures.append({"file": str(manifest_path), "doc_id": None,
                         **fail.to_json()})
    annotations_dir = Path(args.annotations)
    link_totals = {k: 0 for k in _LINK_KEYS}
    doc_positive = {}      # R-D：per-doc positive/anchorless 引用集（步骤 7b 消费）
    doc_anchorless = {}
    doc_unit_linked = {}
    for doc in sorted(core_docs, key=lambda d: d["doc_id"]):
        doc_id = doc["doc_id"]
        path = annotations_dir / (doc_id + ".json")
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            _err("核心标注不可读: %s: %s" % (path, exc))
            return 2
        out_id, fails = validate_annotation(data, manifest_index)
        if out_id != doc_id:
            failures.append({"file": str(path),
                             "doc_id": out_id,
                             "code": "doc_id_mismatch",
                             "detail": "manifest=%s annotation=%s"
                                       % (doc_id, out_id)})
        for fail in fails:
            failures.append({"file": str(path), "doc_id": out_id,
                             **fail.to_json()})
        stats = compute_link_stats(data)
        for k in _LINK_KEYS:
            link_totals[k] += stats[k]
        pos, anch, ulinks = _doc_link_sets(data)
        doc_positive[doc_id] = pos
        doc_anchorless[doc_id] = anch
        doc_unit_linked[doc_id] = ulinks
    if failures:
        for item in failures:
            print("[%s] %s %s: %s" % (item["code"], item["doc_id"] or "-",
                                      item["file"], item["detail"]),
                  file=sys.stderr)
        _err("最终 validator 存在 %d 项失败——gold 状态不干净，拒绝冻结"
             % len(failures))
        return 1

    # ---- 步骤 4+5：24 篇逐文件 hash + gold_digest（单一实现）----
    try:
        gold_digest, per_file_sha = compute_gold_digest(
            str(annotations_dir), core_docs)
    except ValueError as exc:
        _err("gold digest 计算失败: %s" % exc)
        return 2

    # ---- 步骤 6：双标注记录装配（恰 4，decision 须闭合）----
    try:
        agreements = {}
        report_shas = {}
        for rp in args.agreement_report:
            try:
                raw = Path(rp).read_bytes()
                report = json.loads(raw.decode("utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("agreement report 读取失败 %s: %s"
                                 % (rp, exc))
            did = report.get("doc_id")
            decision = report.get("decision")
            if did not in core_ids:
                raise ValueError("agreement report doc_id=%r 不在 core 集"
                                 % did)
            if did in agreements:
                raise ValueError("agreement report 重复 doc_id: %s" % did)
            if decision == "indeterminate":
                raise ValueError(
                    "doc %s decision=indeterminate——identity resolution "
                    "未闭合，G⑥ 不得签发" % did)
            if decision not in ("pass", "below_threshold"):
                raise ValueError("doc %s decision 非法: %r" % (did, decision))
            for key in ("agreement", "agreement_lower", "agreement_upper"):
                if not isinstance(report.get(key), (int, float)):
                    raise ValueError("doc %s agreement report 缺数值字段 %s"
                                     % (did, key))
            agreements[did] = report
            report_shas[did] = hashlib.sha256(raw).hexdigest()
        if len(agreements) != DOUBLE_ANNOTATION_COUNT:
            raise ValueError("agreement report 须恰 %d 份，实际 %d 份"
                             % (DOUBLE_ANNOTATION_COUNT, len(agreements)))

        secondary = _parse_pairs(args.secondary, "--secondary")
        if set(secondary) != set(agreements):
            raise ValueError("--secondary 与 agreement report 的 doc_id 集"
                             "不一致: %s vs %s"
                             % (sorted(secondary), sorted(agreements)))
        secondary_sha = {}
        for did, spath in secondary.items():
            raw = Path(spath).read_bytes()
            secondary_sha[did] = hashlib.sha256(raw).hexdigest()
            if json.loads(raw.decode("utf-8")).get("doc_id") != did:
                raise ValueError("secondary 文件 doc_id 与键不符: %s" % spath)

        arbitration = _parse_pairs(args.arbitration, "--arbitration")
        unknown = set(arbitration) - set(agreements)
        if unknown:
            raise ValueError("--arbitration 含非双标注 doc: %s"
                             % sorted(unknown))
        double_records = []
        for did in sorted(agreements):
            report = agreements[did]
            decision = report["decision"]
            if decision == "below_threshold":
                status = arbitration.get(did)
                if status not in ARBITRATION_CONVERGED:
                    raise ValueError(
                        "doc %s below_threshold——仲裁未收敛（须 "
                        "--arbitration %s=resolved/converged；不收敛=停机"
                        "条件）" % (did, did))
            else:
                status = arbitration.get(did, "not_needed")
            lower, upper = (report["agreement_lower"],
                            report["agreement_upper"])
            resolution = report.get("identity_resolution") or {}
            double_records.append({
                "doc_id": did,
                "decision": decision,
                "agreement_lower": lower,
                "agreement_upper": upper,
                "agreement_final": lower if lower == upper else None,
                "secondary_annotation_sha256": secondary_sha[did],
                "agreement_report_sha256": report_shas[did],
                "agreement_implementation_commit":
                    args.agreement_commit.strip().lower(),
                "pair_map_sha256": resolution.get("pair_map_sha256"),
                "arbitration_status": status,
            })
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        _err(str(exc))
        return 2

    # ---- 步骤 7：relation 抽查记录校验（r10 R3 字段）----
    try:
        spotcheck_records = []
        seen_spot = set()
        for sp in args.spotcheck:
            rec = _load(sp, "spotcheck record")
            missing = [k for k in _SPOTCHECK_REQUIRED if k not in rec]
            if missing:
                raise ValueError("spotcheck 记录缺字段 %s: %s"
                                 % (missing, sp))
            if rec["doc_id"] not in core_ids:
                raise ValueError("spotcheck doc_id=%r 不在 core 集"
                                 % rec["doc_id"])
            if rec["doc_id"] in seen_spot:
                raise ValueError("spotcheck 重复 doc_id: %s" % rec["doc_id"])
            seen_spot.add(rec["doc_id"])
            if rec["result"] not in _SPOTCHECK_RESULTS:
                raise ValueError("spotcheck result 非法: %r（须 %s）"
                                 % (rec["result"], "/".join(
                                     _SPOTCHECK_RESULTS)))
            if rec["result"] == "defects_found" and \
                    not (rec.get("defects") or rec.get("corrections")):
                raise ValueError("result=defects_found 须含非空 defects 或"
                                 " corrections 字段（r10 R3 词汇表）: %s" % sp)
            if not (rec.get("checked_unit_ids")
                    or rec.get("nontext_refs")):
                raise ValueError("spotcheck 须含 checked_unit_ids 或 "
                                 "nontext_refs: %s" % sp)
            spotcheck_records.append(rec)
        if len(spotcheck_records) < SPOTCHECK_MIN:
            raise ValueError("relation 抽查记录须 ≥%d 份，实际 %d 份"
                             % (SPOTCHECK_MIN, len(spotcheck_records)))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        _err(str(exc))
        return 2

    # ---- 步骤 7b：抽查覆盖门禁（指南 G⑥ 前置 3 + r10 R3 词汇表）----
    # 外部评审 R-D 采纳：domain 覆盖、positive 逐边全查、negative
    # anchorless 计数、defects/corrections 闭环——全部从最终 gold 字节
    # 现场重算（步骤 3 采集），不信任记录自述。
    audit_lines = []
    try:
        domains = {}
        for d in core_docs:
            dom = d.get("domain")
            if not isinstance(dom, str) or not dom:
                raise ValueError(
                    "manifest core doc %s 缺 domain 字段（domain ≥%d 覆盖"
                    "核对需要它；manifest 为 G④ 冻结层）"
                    % (d["doc_id"], DOMAIN_MIN))
            domains[d["doc_id"]] = dom
        spot_domains = sorted({domains[r["doc_id"]]
                               for r in spotcheck_records})
        if len(spot_domains) < DOMAIN_MIN:
            raise ValueError("抽查记录仅覆盖 %d 个 domain（%s），须 ≥%d"
                             % (len(spot_domains), "/".join(spot_domains),
                                DOMAIN_MIN))
        for rec in spotcheck_records:
            did = rec["doc_id"]
            atype = rec.get("audit_type")
            if atype not in _SPOTCHECK_AUDIT_TYPES:
                raise ValueError(
                    "doc %s audit_type=%r 非法（r10 R3 词汇表须 %s）"
                    % (did, atype, "/".join(_SPOTCHECK_AUDIT_TYPES)))
            pos = doc_positive[did]
            anchorless = doc_anchorless[did]
            unit_linked = doc_unit_linked[did]
            rec_refs = set(r for r in (rec.get("nontext_refs") or [])
                           if isinstance(r, str))
            if atype == "positive":
                if not pos:
                    raise ValueError(
                        "doc %s 无 linked pairs，不能作为 positive 抽查对象"
                        "（指南 G⑥ 前置 3：抽查文档须有 linked pairs）" % did)
                checked_ids = set(rec.get("checked_unit_ids") or [])
                edges = {(uid, ref) for uid, refs in unit_linked.items()
                         for ref in refs}
                covered = {(uid, ref) for uid in checked_ids
                           if uid in unit_linked
                           for ref in unit_linked[uid]}
                covered |= {(uid, ref) for uid, refs in unit_linked.items()
                            for ref in refs if ref in rec_refs}
                missing = edges - covered
                if missing:
                    raise ValueError(
                        "doc %s positive 抽查未逐条覆盖全部 linked pairs"
                        "（缺 %d/%d 条边）——指南 G⑥ 前置 3：逐条核对"
                        % (did, len(missing), len(edges)))
                audit_lines.append(
                    "doc %s domain=%s positive：边覆盖 %d/%d（全）"
                    % (did, domains[did], len(edges), len(edges)))
            else:
                if not anchorless:
                    raise ValueError(
                        "doc %s 无 anchorless 对象，不满足 negative 抽查"
                        "条件（指南：每篇 ≥%d anchorless，不足全查）"
                        % (did, ANCHORLESS_MIN))
                required = min(ANCHORLESS_MIN, len(anchorless))
                covered_anch = len(rec_refs & anchorless)
                if covered_anch < required:
                    raise ValueError(
                        "doc %s negative 抽查 anchorless 覆盖 %d/%d"
                        "（对象共 %d）——每篇 ≥%d 或不足全查"
                        % (did, covered_anch, required, len(anchorless),
                           ANCHORLESS_MIN))
                audit_lines.append(
                    "doc %s domain=%s negative：anchorless 覆盖 %d/%d"
                    "（对象共 %d）"
                    % (did, domains[did], covered_anch, required,
                       len(anchorless)))
            audit_lines.append(
                "  result=%s %s" % (
                    rec["result"],
                    "（含 defects/corrections 记录）"
                    if rec["result"] == "defects_found" else "（无缺陷）"))
    except ValueError as exc:
        _err("抽查覆盖门禁: %s" % exc)
        return 2

    for rec in spotcheck_records:
        reviewed = str(rec.get("annotation_sha256_reviewed", ""))
        final = per_file_sha.get(rec["doc_id"], "")
        if reviewed and final and reviewed != final:
            print("注：doc %s 抽查 reviewed SHA ≠ 冻结最终字节（R1 修正"
                  "分支合法——G⑥ digest 用最终字节）" % rec["doc_id"],
                  file=sys.stderr)

    # ---- 步骤 8：组装 credential ----
    credential = {
        "gold_revision": args.gold_revision,
        "issued_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "manifest_sha256": manifest_sha,
        "per_doc_sha256": per_file_sha,
        "gold_digest": gold_digest,
        "digest_definition": {
            "algorithm": "sha256",
            "encoding": "UTF-8",
            "order": "doc_id ascending",
            "line_format": "{doc_id}:{file_sha256}\\n",
            "scope": "%d core (split in %s)"
                     % (CORE_DOC_COUNT, "/".join(CORE_SPLITS)),
        },
        "double_annotation": double_records,
        "relation_spotcheck": spotcheck_records,
        "validator_record": {
            "validator": "stage9.validation (validate_annotation + "
                         "validate_manifest_consistency + compute_link_stats)",
            "validator_commit": args.validator_commit.strip().lower(),
            "scope": "manifest consistency + %d core annotation files"
                     % CORE_DOC_COUNT,
            "result": {
                "checked_files": CORE_DOC_COUNT,
                "failures": 0,
                "core_link_stats": link_totals,
            },
            "executed_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
        },
    }

    # ---- 步骤 9：写盘（immutable：已存在即拒）----
    out_path = (Path(args.out) if args.out else
                manifest_path.parent /
                ("gold-freeze-credential.%s.json" % args.gold_revision))
    if out_path.exists():
        _err("凭证文件已存在: %s\n（immutable：覆盖 r1 禁止；core gold "
             "改动须重新裁决签 r2）" % out_path)
        return 2
    payload = json.dumps(credential, ensure_ascii=False, indent=1)

    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(payload.encode("utf-8"))

    # ---- 步骤 10：credential 字节 SHA（外部登记，不写入自身）----
    credential_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print("gold_revision=%s" % args.gold_revision)
    print("gold_digest=%s" % gold_digest)
    print("core=%d docs; double_annotation=%d; relation_spotcheck=%d"
          % (CORE_DOC_COUNT, len(double_records),
             len(spotcheck_records)))
    print("core_link_stats=%s"
          % json.dumps(link_totals, ensure_ascii=False))
    print("spotcheck_audit:")
    for line in audit_lines:
        print("  %s" % line)
    if args.dry_run:
        print("dry-run：全链门禁通过，未写盘（credential SHA 以签发时"
              "实际写出字节为准）")
    else:
        print("credential 写出: %s" % out_path)
        print("credential_sha256=%s （外部台账/G⑦ provenance 登记，"
              "不写入凭证自身）" % credential_sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
