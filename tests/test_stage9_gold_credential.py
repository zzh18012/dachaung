# -*- coding: utf-8 -*-
"""Stage 9 批次 26：G⑥ gold freeze 凭证组装 CLI 测试（合成夹具）。

格式契约来源：docs/stage9-annotation-guide.md §7.3（五轮裁决 C 预裁定）
+ 十轮裁决 R3（relation_spotcheck 字段）。全部用合成微缩语料驱动
（24 core + 4 双标注 + 抽查记录），零真实 gold 接触。

覆盖：
- happy path：写出凭证、字段完备、digest 独立复算一致、immutable SHA
- 门禁拒绝：manifest 冻结不符 / core 数量 / validator 失败（rc 1）/
  indeterminate 未闭合 / below_threshold 无收敛仲裁 / 抽查字段缺失
  或不足 / secondary doc_id 不符 / 目标文件已存在（immutable）
- --dry-run 不写盘
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from stage9.validation import compute_link_stats

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "stage9_gold_credential",
    str(ROOT / "scripts" / "stage9_gold_credential.py"))
gc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gc)

STREAM = "Alpha beta gamma. Delta epsilon. Zeta eta theta."


def _sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _annotation(doc_id):
    """合法 v1.1 合成标注（同 test_stage9_validation 的平铺样例）。"""
    return {
        "doc_id": doc_id,
        "annotation_schema": "v1.1",
        "sentence_splitter": "v1",
        "normalization": "fold-ws-v1",
        "annotator": "claude-draft + user-review",
        "stream": STREAM,
        "units": [
            {"unit_id": "u0001", "kind": "heading", "page": 1,
             "body_index": None,
             "char_span": [0, 18], "norm_text_hash": _sha(STREAM[0:18]),
             "text_preview": STREAM[0:18], "gold_segment_id": "g01",
             "hard_boundary_before": True},
            {"unit_id": "u0002", "kind": "sentence", "page": 1,
             "body_index": None,
             "char_span": [18, 33], "norm_text_hash": _sha(STREAM[18:33]),
             "text_preview": STREAM[18:33], "gold_segment_id": "g02",
             "hard_boundary_before": False,
             "linked_nontext": ["img:figure1"]},
            {"unit_id": "u0003", "kind": "sentence", "page": 2,
             "body_index": None,
             "char_span": [33, 48], "norm_text_hash": _sha(STREAM[33:48]),
             "text_preview": STREAM[33:48], "gold_segment_id": "g02",
             "hard_boundary_before": True},
            {"unit_id": "u0004", "kind": "nontext", "page": 1,
             "body_index": None,
             "char_span": None, "norm_text_hash": None,
             "nontext_ref": "img:figure1", "gold_segment_id": "g02",
             "hard_boundary_before": False},
        ],
        "segments": [
            {"gold_segment_id": "g01", "hint": "标题", "kind": "frontmatter"},
            {"gold_segment_id": "g02", "hint": "正文", "kind": "body"},
        ],
    }


DOC_IDS = ["doc-%02d" % i for i in range(24)]
SPLITS = (["dev"] * 14) + (["comparison"] * 4) + (["holdout"] * 6)
DOUBLE_IDS = DOC_IDS[:4]


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def _build_corpus(tmp_path, mutate_annotation=None):
    manifest = {"docs": [
        {"doc_id": did, "split": split, "format": "pdf"}
        for did, split in zip(DOC_IDS, SPLITS)]}
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)
    annotations = tmp_path / "annotations"
    for did in DOC_IDS:
        data = _annotation(did)
        if mutate_annotation is not None and did == mutate_annotation[0]:
            mutate_annotation[1](data)
        _write_json(annotations / (did + ".json"), data)
    return manifest_path, annotations


def _agreement(doc_id, decision, lower, upper, pair_map_sha=None):
    report = {
        "doc_id": doc_id,
        "decision": decision,
        "agreement": lower,
        "agreement_lower": lower,
        "agreement_upper": upper,
    }
    if pair_map_sha is not None:
        report["identity_resolution"] = {
            "pair_map_sha256": pair_map_sha, "resolved_group_count": 2}
    return report


def _spotcheck(doc_id, result="pass"):
    rec = {
        "doc_id": doc_id,
        "annotation_sha256_reviewed": "0" * 64,
        "audit_type": "positive_edge_full",
        "checked_count": 11,
        "checked_unit_ids": ["u0002"],
        "result": result,
        "review_date": "2026-09-08",
    }
    if result == "defects_found":
        rec["defects"] = ["p6 两张行内截图未登记"]
    return rec


def _build_inputs(tmp_path, agreements=None, spotchecks=None,
                  mutate_annotation=None):
    """标准输入集：4 份 pass 报告 + 2 份抽查记录。"""
    manifest_path, annotations = _build_corpus(
        tmp_path, mutate_annotation=mutate_annotation)
    manifest_sha = hashlib.sha256(
        manifest_path.read_bytes()).hexdigest()

    reports_dir = tmp_path / "reports"
    if agreements is None:
        agreements = [
            _agreement(DOUBLE_IDS[0], "pass", 0.92, 0.92),
            _agreement(DOUBLE_IDS[1], "pass", 0.86, 0.90),
            _agreement(DOUBLE_IDS[2], "pass", 0.95, 0.95,
                       pair_map_sha="f" * 64),
            _agreement(DOUBLE_IDS[3], "pass", 0.99, 0.99),
        ]
    report_paths = []
    for i, report in enumerate(agreements):
        p = reports_dir / ("report-%d.json" % i)
        _write_json(p, report)
        report_paths.append(p)

    secondary_dir = tmp_path / "annotations-user"
    secondary_args = []
    for did in DOUBLE_IDS:
        p = secondary_dir / (did + ".json")
        _write_json(p, _annotation(did))
        secondary_args.append("%s=%s" % (did, p))

    if spotchecks is None:
        spotchecks = [_spotcheck("doc-05"), _spotcheck("doc-06")]
    spot_paths = []
    for i, rec in enumerate(spotchecks):
        p = reports_dir / ("spot-%d.json" % i)
        _write_json(p, rec)
        spot_paths.append(p)

    out = tmp_path / "credential.json"
    argv = [
        "--manifest", str(manifest_path),
        "--expected-manifest-sha", manifest_sha,
        "--annotations", str(annotations),
        "--validator-commit", "aaaa1111",
        "--agreement-commit", "1817d3b8",
        "--out", str(out),
    ]
    for p in report_paths:
        argv += ["--agreement-report", str(p)]
    for item in secondary_args:
        argv += ["--secondary", item]
    for p in spot_paths:
        argv += ["--spotcheck", str(p)]
    return argv, out, manifest_path, annotations


def test_happy_path_writes_credential(tmp_path):
    argv, out, manifest_path, annotations = _build_inputs(tmp_path)
    assert gc.main(argv) == 0
    assert out.is_file()

    cred = json.loads(out.read_text(encoding="utf-8"))
    assert cred["gold_revision"] == "stage9-b26-gold-r1"
    assert cred["manifest_sha256"] == hashlib.sha256(
        manifest_path.read_bytes()).hexdigest()
    assert list(cred["per_doc_sha256"]) == sorted(DOC_IDS)
    # digest 按锁定定义独立复算（sha256 of "{doc}:{sha}\n" 逐行拼接）
    lines = "".join(
        "%s:%s\n" % (did, hashlib.sha256(
            (annotations / (did + ".json")).read_bytes()).hexdigest())
        for did in sorted(DOC_IDS))
    assert cred["gold_digest"] == hashlib.sha256(
        lines.encode("ascii")).hexdigest()
    assert set(cred["digest_definition"]) == {
        "algorithm", "encoding", "order", "line_format", "scope"}
    assert cred["digest_definition"]["algorithm"] == "sha256"

    doubles = cred["double_annotation"]
    assert [d["doc_id"] for d in doubles] == sorted(DOUBLE_IDS)
    by_id = {d["doc_id"]: d for d in doubles}
    assert by_id[DOUBLE_IDS[0]]["agreement_final"] == 0.92  # 塌缩才填
    assert by_id[DOUBLE_IDS[1]]["agreement_final"] is None  # 区间不虚构
    assert by_id[DOUBLE_IDS[2]]["pair_map_sha256"] == "f" * 64
    assert by_id[DOUBLE_IDS[3]]["arbitration_status"] == "not_needed"
    assert by_id[DOUBLE_IDS[0]]["agreement_implementation_commit"] == \
        "1817d3b8"
    secondary_sha = hashlib.sha256(
        (tmp_path / "annotations-user" / (DOUBLE_IDS[0] + ".json"))
        .read_bytes()).hexdigest()
    assert by_id[DOUBLE_IDS[0]]["secondary_annotation_sha256"] == \
        secondary_sha
    # r27 D-N：仲裁声明所引 agreement report 哈希随凭证保留
    report_sha = hashlib.sha256(
        (tmp_path / "reports" / "report-0.json").read_bytes()).hexdigest()
    assert by_id[DOUBLE_IDS[0]]["agreement_report_sha256"] == report_sha

    assert len(cred["relation_spotcheck"]) == 2

    vr = cred["validator_record"]
    assert vr["result"]["failures"] == 0
    assert vr["result"]["checked_files"] == 24
    assert vr["validator_commit"] == "aaaa1111"
    per_doc_stats = compute_link_stats(_annotation("x"))
    expected_totals = {k: 24 * per_doc_stats[k] for k in
                       ("linked_pairs", "linked_objects",
                        "anchorless_count", "nontext_total")}
    assert vr["result"]["core_link_stats"] == expected_totals


def test_credential_sha_printed_not_self_referential(tmp_path, capsys):
    argv, out, _, _ = _build_inputs(tmp_path)
    assert gc.main(argv) == 0
    payload = out.read_bytes()
    cred_sha = hashlib.sha256(payload).hexdigest()
    assert cred_sha.encode("ascii") not in payload  # 非自指
    assert ("credential_sha256=%s" % cred_sha) in capsys.readouterr().out


def test_manifest_sha_mismatch_refused(tmp_path):
    argv, out, _, _ = _build_inputs(tmp_path)
    idx = argv.index("--expected-manifest-sha")
    argv[idx + 1] = "0" * 64
    assert gc.main(argv) == 2
    assert not out.exists()


def test_core_count_not_24_refused(tmp_path):
    argv, out, manifest_path, _ = _build_inputs(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["docs"] = manifest["docs"][:23]
    _write_json(manifest_path, manifest)
    idx = argv.index("--expected-manifest-sha")
    argv[idx + 1] = hashlib.sha256(
        manifest_path.read_bytes()).hexdigest()
    assert gc.main(argv) == 2
    assert not out.exists()


def test_validator_failure_refused_rc1(tmp_path):
    def break_hash(data):
        data["units"][0]["norm_text_hash"] = "sha256:" + "0" * 64
    argv, out, _, _ = _build_inputs(
        tmp_path, mutate_annotation=("doc-07", break_hash))
    assert gc.main(argv) == 1
    assert not out.exists()


def test_indeterminate_refused(tmp_path):
    agreements = [
        _agreement(DOUBLE_IDS[0], "pass", 0.92, 0.92),
        _agreement(DOUBLE_IDS[1], "indeterminate", 0.80, 0.90),
        _agreement(DOUBLE_IDS[2], "pass", 0.95, 0.95),
        _agreement(DOUBLE_IDS[3], "pass", 0.99, 0.99),
    ]
    argv, out, _, _ = _build_inputs(tmp_path, agreements=agreements)
    assert gc.main(argv) == 2
    assert not out.exists()


def test_below_threshold_without_converged_arbitration_refused(tmp_path):
    agreements = [
        _agreement(DOUBLE_IDS[0], "pass", 0.92, 0.92),
        _agreement(DOUBLE_IDS[1], "below_threshold", 0.70, 0.74),
        _agreement(DOUBLE_IDS[2], "pass", 0.95, 0.95),
        _agreement(DOUBLE_IDS[3], "pass", 0.99, 0.99),
    ]
    argv, out, _, _ = _build_inputs(tmp_path, agreements=agreements)
    assert gc.main(argv) == 2
    assert not out.exists()
    # 显式给未收敛状态同样拒绝
    argv += ["--arbitration", "%s=open" % DOUBLE_IDS[1]]
    assert gc.main(argv) == 2
    assert not out.exists()


def test_below_threshold_with_resolved_arbitration_accepted(tmp_path):
    agreements = [
        _agreement(DOUBLE_IDS[0], "pass", 0.92, 0.92),
        _agreement(DOUBLE_IDS[1], "below_threshold", 0.70, 0.74),
        _agreement(DOUBLE_IDS[2], "pass", 0.95, 0.95),
        _agreement(DOUBLE_IDS[3], "pass", 0.99, 0.99),
    ]
    argv, out, _, _ = _build_inputs(tmp_path, agreements=agreements)
    argv += ["--arbitration", "%s=resolved" % DOUBLE_IDS[1]]
    assert gc.main(argv) == 0
    cred = json.loads(out.read_text(encoding="utf-8"))
    by_id = {d["doc_id"]: d for d in cred["double_annotation"]}
    assert by_id[DOUBLE_IDS[1]]["arbitration_status"] == "resolved"
    assert by_id[DOUBLE_IDS[1]]["agreement_final"] is None


def test_secondary_doc_id_mismatch_refused(tmp_path):
    argv, out, _, _ = _build_inputs(tmp_path)
    idx = next(i for i, a in enumerate(argv)
               if a.startswith("--secondary"))
    wrong = tmp_path / "other.json"
    _write_json(wrong, _annotation("doc-99"))
    argv[idx + 1] = "%s=%s" % (DOUBLE_IDS[0], wrong)
    assert gc.main(argv) == 2
    assert not out.exists()


def test_spotcheck_missing_fields_or_too_few_refused(tmp_path):
    argv, out, _, _ = _build_inputs(
        tmp_path, spotchecks=[_spotcheck("doc-05")])  # 仅 1 份
    assert gc.main(argv) == 2
    assert not out.exists()

    bad = _spotcheck("doc-06")
    del bad["annotation_sha256_reviewed"]
    argv, out, _, _ = _build_inputs(
        tmp_path, spotchecks=[_spotcheck("doc-05"), bad])
    assert gc.main(argv) == 2
    assert not out.exists()


def test_defects_found_requires_defects_field(tmp_path):
    argv, out, _, _ = _build_inputs(tmp_path / "ok", spotchecks=[
        _spotcheck("doc-05"),
        _spotcheck("doc-06", result="defects_found")])
    assert gc.main(argv) == 0  # _spotcheck 已带 defects
    bad = _spotcheck("doc-06", result="defects_found")
    del bad["defects"]
    argv, out, _, _ = _build_inputs(tmp_path / "bad", spotchecks=[
        _spotcheck("doc-05"), bad])
    assert gc.main(argv) == 2
    assert not out.exists()


def test_existing_credential_immutable(tmp_path):
    argv, out, _, _ = _build_inputs(tmp_path)
    out.write_text("{}", encoding="utf-8")
    assert gc.main(argv) == 2
    assert out.read_text(encoding="utf-8") == "{}"  # 未覆盖


def test_dry_run_passes_gates_without_writing(tmp_path):
    argv, out, _, _ = _build_inputs(tmp_path)
    assert gc.main(argv + ["--dry-run"]) == 0
    assert not out.exists()


def test_reviewed_sha_mismatch_noted_not_failed(tmp_path, capsys):
    # reviewed SHA（全 0）与最终字节不同 = R1 修正分支合法：仅 stderr
    # 注记，不影响签发
    argv, out, _, _ = _build_inputs(tmp_path)
    assert gc.main(argv) == 0
    assert out.is_file()
    assert "R1 修正分支合法" in capsys.readouterr().err
