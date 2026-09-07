# -*- coding: utf-8 -*-
"""Stage 9 批次 26：系统侧 max_chars dev 选优测试（G⑦ 预实现）。

裁决 C 边界：只用合成夹具——真实 14-dev gold 上的 max_chars 参数
探索（含 dry run）被禁止，本文件不触真实语料、不产生真实评分；
真实管线接线用合成 docx 验证（不计算参数优劣）。
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from stage9.system_eval import (
    compute_gold_digest,
    evaluate_system_doc,
    load_preregistration,
    system_macro_and_select,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stage9_system_select_cli", ROOT / "scripts" / "stage9_system_select.py")


def _load_cli():
    mod = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(mod)
    return mod


def _ann(doc_id, texts):
    """texts: [(seg, sentence), ...] → 平铺 span 的合成标注。"""
    parts = []
    units = []
    pos = 0
    for idx, (seg, text) in enumerate(texts):
        if parts:
            parts.append(" ")
            pos += 1
        start = pos
        parts.append(text)
        pos += len(text)
        units.append({
            "unit_id": "u%04d" % (idx + 1), "kind": "sentence",
            "page": 1, "body_index": None, "char_span": [start, pos],
            "norm_text_hash": None, "text_preview": None,
            "nontext_ref": None, "gold_segment_id": seg,
            "hard_boundary_before": idx == 0,
        })
    return {"doc_id": doc_id, "stream": "".join(parts), "units": units}


def test_evaluate_system_doc_perfect_tiling():
    # chunk 边界与 gold_segment 边界重合 → ARI=1
    ann = _ann("d", [("g01", "Alpha beta."), ("g01", "Gamma delta."),
                     ("g02", "Epsilon zeta.")])
    stream = ann["stream"]
    mid = stream.index("Epsilon")
    chunks = {100: [stream[:mid].strip(), stream[mid:].strip()]}
    r = evaluate_system_doc(ann, chunks, [100])
    cell = r["results"][100]
    assert cell["ari"] == pytest.approx(1.0)
    assert cell["unmatched_chunks"] == 0 and cell["uncovered_units"] == 0
    assert cell["na_reason"] is None


def test_evaluate_system_doc_na_reason_disclosed():
    ann = _ann("d", [("g01", "Alpha beta.")])
    r = evaluate_system_doc(ann, {}, [200, 800],
                            na_by_param={800: "parse_failed:no_extracted_elements",
                                         200: "empty_result"})
    assert r["results"][200]["ari"] is None
    assert r["results"][200]["na_reason"] == "empty_result"
    assert r["results"][800]["na_reason"] == \
        "parse_failed:no_extracted_elements"
    assert r["results"][800]["uncovered_units"] == len(ann["units"])


def test_evaluate_system_doc_unmatched_not_silent():
    # 覆盖 unit 横跨两 segment 两 chunk（非退化 contingency，ARI 可定义）
    ann = _ann("d", [("g01", "Alpha beta."), ("g01", "Gamma delta."),
                     ("g02", "Epsilon zeta.")])
    chunks = {100: ["Alpha beta.", "Gamma delta. Epsilon",
                    "系统幻觉文本不在流上"]}
    r = evaluate_system_doc(ann, chunks, [100])
    assert r["results"][100]["unmatched_chunks"] == 1
    assert r["results"][100]["uncovered_units"] == 0
    assert r["results"][100]["ari"] is not None  # 定位成功的照常计


def test_macro_tie_break_smallest_param():
    good = {"doc_id": "d", "results": {
        200: {"ari": 0.5}, 800: {"ari": 0.5}, 2000: {"ari": 0.3}}}
    macro, best_p, best_v = system_macro_and_select(
        [good], [200, 800, 2000])
    assert best_p == 200 and best_v == pytest.approx(0.5)


def test_macro_all_na_selection_fails():
    doc = {"doc_id": "d", "results": {200: {"ari": None},
                                      800: {"ari": None}}}
    macro, best_p, best_v = system_macro_and_select([doc], [200, 800])
    assert best_p is None and best_v is None


def test_preregistration_frozen_shape():
    cfg, sha = load_preregistration()
    assert cfg["preregistration"] == "stage9-system-select-g7"
    assert cfg["candidate_grid"] == [200, 500, 800, 1200, 2000]
    assert cfg["tie_break"].startswith("macro ARI 平局取最小")
    assert cfg["participating_split"] == "dev"
    assert len(cfg["dev_doc_ids"]) == 14
    assert cfg["manifest_sha256_expected"] == (
        "51d3d40057568a35ee8415e30c91824662be216d098e3d639aaa954f4f"
        "140855")
    assert len(sha) == 64
    # 裁决 C' 追加的输入身份校验（不触网格/metric/tie-break）
    assert "sha256" in cfg["gold_digest"]["definition"]
    assert "dev, comparison, holdout" in cfg["gold_digest"]["definition"]
    assert "gold_digest" in cfg["report_provenance_fields"]
    assert "dev_annotation_hashes" in cfg["report_provenance_fields"]
    assert "working_tree" in cfg["gold_digest"]


# ---------- CLI 守卫（合成 manifest + 合成预注册，进程内 monkeypatch） ----------

def _synth_env(tmp_path):
    """合成 manifest + 预注册（1 篇 dev），返回 (manifest, annotations,
    prereg_dict)。"""
    manifest = {"docs": [{"doc_id": "synth-01", "format": "docx",
                          "split": "dev"}]}
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    anns = tmp_path / "annotations"
    anns.mkdir()
    (anns / "synth-01.json").write_text(
        json.dumps(_ann("synth-01", [("g01", "Alpha beta."),
                                     ("g02", "Gamma delta.")]),
                   ensure_ascii=False), encoding="utf-8")
    import hashlib
    msha = hashlib.sha256(mpath.read_bytes()).hexdigest()
    prereg = {
        "preregistration": "synthetic-test", "param": "max_chars",
        "candidate_grid": [200, 800],
        "participating_split": "dev", "dev_doc_ids": ["synth-01"],
        "manifest_sha256_expected": msha,
        "edge_handling": {},
    }
    return mpath, anns, prereg


def test_cli_requires_gold_revision(tmp_path):
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    with pytest.raises(SystemExit) as ei:
        cli.main(["--manifest", str(mpath), "--annotations", str(anns)])
    assert ei.value.code == 2  # argparse 缺必选参数（revision+digest）


def test_cli_rejects_non_dev_split(tmp_path, monkeypatch):
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    monkeypatch.setattr(cli, "load_preregistration",
                        lambda path=None: (prereg, "synthsha"))
    rc = cli.main(["--manifest", str(mpath), "--annotations", str(anns),
                   "--gold-revision", "synthetic-test",
                   "--gold-digest", "0" * 64, "--split",
                   "holdout"])
    assert rc == 2


def test_cli_rejects_manifest_sha_mismatch(tmp_path, monkeypatch):
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    prereg["manifest_sha256_expected"] = "0" * 64
    monkeypatch.setattr(cli, "load_preregistration",
                        lambda path=None: (prereg, "synthsha"))
    monkeypatch.setattr(cli, "_working_tree_dirty",
                        lambda: (False, ""))
    rc = cli.main(["--manifest", str(mpath), "--annotations", str(anns),
                   "--gold-revision", "synthetic-test",
                   "--gold-digest", "0" * 64])
    assert rc == 2


def test_cli_rejects_dev_set_mismatch(tmp_path, monkeypatch):
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    prereg["dev_doc_ids"] = ["another-doc"]
    monkeypatch.setattr(cli, "load_preregistration",
                        lambda path=None: (prereg, "synthsha"))
    monkeypatch.setattr(cli, "_working_tree_dirty",
                        lambda: (False, ""))
    rc = cli.main(["--manifest", str(mpath), "--annotations", str(anns),
                   "--gold-revision", "synthetic-test",
                   "--gold-digest", "0" * 64])
    assert rc == 2


def test_cli_rejects_dirty_working_tree(tmp_path, monkeypatch):
    # 裁决 C'：G⑦ 正式运行拒绝 dirty working tree（其余输入全对）
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    monkeypatch.setattr(cli, "load_preregistration",
                        lambda path=None: (prereg, "synthsha"))
    monkeypatch.setattr(cli, "_working_tree_dirty",
                        lambda: (True, "工作树非干净（fixture）"))
    digest, _ = compute_gold_digest(anns, [{"doc_id": "synth-01",
                                            "split": "dev"}])
    rc = cli.main(["--manifest", str(mpath), "--annotations", str(anns),
                   "--gold-revision", "synthetic-test",
                   "--gold-digest", digest])
    assert rc == 2


def test_cli_rejects_wrong_gold_digest(tmp_path, monkeypatch):
    # 裁决 C'：gold 输入身份校验——重算 digest ≠ 签发值即拒绝
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    monkeypatch.setattr(cli, "load_preregistration",
                        lambda path=None: (prereg, "synthsha"))
    monkeypatch.setattr(cli, "_working_tree_dirty",
                        lambda: (False, ""))
    rc = cli.main(["--manifest", str(mpath), "--annotations", str(anns),
                   "--gold-revision", "synthetic-test",
                   "--gold-digest", "a" * 64])
    assert rc == 2


def test_cli_happy_path_synthetic(tmp_path, monkeypatch, capsys):
    cli = _load_cli()
    mpath, anns, prereg = _synth_env(tmp_path)
    monkeypatch.setattr(cli, "load_preregistration",
                        lambda path=None: (prereg, "synthsha"))
    monkeypatch.setattr(cli, "_working_tree_dirty",
                        lambda: (False, ""))
    digest, per_file = compute_gold_digest(
        anns, [{"doc_id": "synth-01", "split": "dev"}])

    def fake_run(source, max_chars, parser_name="fallback"):
        # 合成 chunk：与两 segment 边界重合（ARI=1，两参数平局→取小）
        return ["Alpha beta.", "Gamma delta."], None

    monkeypatch.setattr(cli, "run_system_chunks", fake_run)
    report = tmp_path / "report.json"
    rc = cli.main(["--manifest", str(mpath), "--annotations", str(anns),
                   "--gold-revision", "synthetic-g6-fixture",
                   "--gold-digest", digest,
                   "--report", str(report), "--json"])
    assert rc == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["preregistration"] == "synthetic-test"
    assert payload["provenance"]["gold_revision"] == "synthetic-g6-fixture"
    assert payload["provenance"]["gold_digest"] == digest
    assert payload["provenance"]["dev_annotation_hashes"] == {
        "synth-01": per_file["synth-01"]}
    assert payload["provenance"]["preregistration_sha256"] == "synthsha"
    assert "implementation_commit" in payload["provenance"]
    assert payload["doc_count"] == 1
    assert payload["selection"]["max_chars"] in (200, 800)


# ---------- gold digest（裁决 C' 输入身份校验） ----------

def test_compute_gold_digest_deterministic_and_sensitive(tmp_path):
    import hashlib
    core = [{"doc_id": "b-02", "split": "dev"},
            {"doc_id": "a-01", "split": "holdout"},
            {"doc_id": "c-03", "split": "dev"}]
    for d in core:
        (tmp_path / (d["doc_id"] + ".json")).write_text(
            json.dumps({"doc_id": d["doc_id"]}), encoding="utf-8")
    d1, per1 = compute_gold_digest(tmp_path, core)
    d2, _ = compute_gold_digest(tmp_path, list(reversed(core)))  # 排序稳定
    assert d1 == d2 and len(d1) == 64
    # 手算锁死聚合式
    lines = []
    for doc_id in sorted(x["doc_id"] for x in core):
        fsha = hashlib.sha256(
            (tmp_path / (doc_id + ".json")).read_bytes()).hexdigest()
        lines.append("%s:%s\n" % (doc_id, fsha))
    assert d1 == hashlib.sha256("".join(lines).encode("ascii")).hexdigest()
    # 逐篇哈希披露；字节变动 → digest 变化
    assert set(per1) == {"a-01", "b-02", "c-03"}
    (tmp_path / "a-01.json").write_text(
        json.dumps({"doc_id": "a-01", "changed": True}), encoding="utf-8")
    d3, _ = compute_gold_digest(tmp_path, core)
    assert d3 != d1


def test_compute_gold_digest_missing_file_raises(tmp_path):
    with pytest.raises(ValueError):
        compute_gold_digest(tmp_path, [{"doc_id": "missing",
                                        "split": "dev"}])


# ---------- 真实管线接线（合成 docx，不计算参数优劣） ----------

def test_run_system_chunks_wiring_synthetic_docx(tmp_path):
    docx = pytest.importorskip("docx")
    from stage9.system_eval import run_system_chunks
    out = tmp_path / "synthetic.docx"
    d = docx.Document()
    for i in range(15):
        d.add_paragraph("段落 %d 的内容，填充文本以保证总量超过二百个字符"
                        "的要求，这里补一些字使得全文档足够长。" % i)
    d.save(str(out))
    chunks, reason = run_system_chunks(out, 800)
    assert reason is None and chunks
    assert all(len(c) <= 800 for c in chunks)
    assert sum(len(c) for c in chunks) >= 200


def test_run_system_chunks_missing_file(tmp_path):
    from stage9.system_eval import run_system_chunks
    chunks, reason = run_system_chunks(tmp_path / "nope.docx", 800)
    assert chunks is None and reason.startswith("parse_failed:")
