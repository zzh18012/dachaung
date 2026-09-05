# -*- coding: utf-8 -*-
"""Stage 9 批次 26：基线 N 网格评测与选优测试。

ARI 数值不在此手算（test_stage9_baselines_ari.py 已锁死 ARI 实现）；
本文件锁：投影全覆盖不变量（B1/B2 均为流的精确划分）、与
ari_units_vs_chunks 直算一致、macro 平均、平局取最小 N、CLI 契约。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from stage9.ari import ari_units_vs_chunks
from stage9.baseline_eval import (
    BASELINE_CONFIG,
    evaluate_doc,
    macro_average,
    pick_best,
    select_baselines,
)
from stage9.baselines import B2_VARIANT, b1_fixed_length, b2_recursive
from stage9.project import project_chunks_to_units

ROOT = Path(__file__).resolve().parents[1]


def _ann(stream, unit_texts, segs):
    units = []
    pos = 0
    parts = []
    for idx, (text, seg) in enumerate(zip(unit_texts, segs)):
        if parts:
            parts.append(" ")
            pos += 1
        start = pos
        parts.append(text)
        pos += len(text)
        units.append({"unit_id": "u%04d" % (idx + 1), "kind": "sentence",
                      "char_span": [start, pos],
                      "gold_segment_id": seg})
    return {"doc_id": "fixture", "stream": stream,
            "units": units + [
                {"unit_id": "u%04d" % (len(unit_texts) + 1),
                 "kind": "nontext", "char_span": None,
                 "nontext_ref": "img:f1", "gold_segment_id": segs[0]}]}


STREAM = ("aaaa。 bbbb。 cccc。 dddd。 eeee。 ffff。 "
          "gggg。 hhhh。 iiii。 jjjj。")
UNIT_TEXTS = [t + "。" for t in STREAM.replace("。", "").split()]
SEGS = ["g01"] * 5 + ["g02"] * 5


def test_full_coverage_invariant_both_baselines():
    ann = _ann(STREAM, UNIT_TEXTS, SEGS)
    text_units = [u for u in ann["units"] if u["char_span"] is not None]
    for chunks in (b1_fixed_length(STREAM, 12),
                   b2_recursive(STREAM, 12)):
        assert "".join(chunks) == STREAM
        proj = project_chunks_to_units(chunks, STREAM, text_units)
        assert proj.unmatched_chunk_indexes == ()
        assert len(proj.attributions) == len(text_units)


def test_evaluate_doc_matches_direct_ari():
    ann = _ann(STREAM, UNIT_TEXTS, SEGS)
    rep = evaluate_doc(ann, n_grid=(7, 12))
    text_units = [u for u in ann["units"] if u["char_span"] is not None]
    seg_ids = [u["gold_segment_id"] for u in text_units]
    for bl, fn in (("B1", b1_fixed_length), (B2_VARIANT, b2_recursive)):
        for n in (7, 12):
            proj = project_chunks_to_units(fn(STREAM, n), STREAM,
                                           text_units)
            labels = [proj.attributions.get(u["unit_id"])
                      for u in text_units]
            expect, _ = ari_units_vs_chunks(seg_ids, labels)
            got = rep["results"][bl][n]["ari"]
            assert got == pytest.approx(expect), (bl, n)


def test_evaluate_doc_disclosure_fields():
    rep = evaluate_doc(_ann(STREAM, UNIT_TEXTS, SEGS), n_grid=(12,))
    assert rep["doc_id"] == "fixture"
    assert rep["text_units"] == 10 and rep["nontext_units"] == 1
    cell = rep["results"]["B1"][12]
    assert cell["unmatched_chunks"] == 0
    assert cell["uncovered_units"] == 0
    assert cell["n_ari_units"] == 10
    assert cell["cross_chunk_units"] >= 0


def test_macro_average_and_selection():
    ann = _ann(STREAM, UNIT_TEXTS, SEGS)
    reps = [evaluate_doc(ann, n_grid=(12, 24)) for _ in range(3)]
    for bl in ("B1", B2_VARIANT):
        for n in (12, 24):
            per_doc = reps[0]["results"][bl][n]["ari"]
            assert macro_average(reps, bl, n) == pytest.approx(per_doc)
    macro, selection = select_baselines(reps, n_grid=(12, 24))
    for bl in ("B1", B2_VARIANT):
        best_n, best_v = pick_best(macro[bl])
        assert selection[bl]["n"] == best_n
        assert selection[bl]["macro_ari"] == best_v
        assert best_v == pytest.approx(macro[bl][best_n])


def test_pick_best_tie_smallest_n():
    assert pick_best({200: 0.5, 800: 0.7, 1200: 0.7}) == (800, 0.7)
    assert pick_best({200: 0.9, 800: 0.7}) == (200, 0.9)
    assert pick_best({200: None}) == (None, None)
    assert pick_best({800: 0.1, 200: None}) == (800, 0.1)


def test_b2_variant_frozen_contract():
    assert B2_VARIANT == "B2-foldws-v1"
    cfg = BASELINE_CONFIG[B2_VARIANT]
    assert cfg["input_view"] == "fold_ws"
    assert cfg["newline_level_hits"] == 0
    rep = evaluate_doc(_ann(STREAM, UNIT_TEXTS, SEGS), n_grid=(12,))
    assert set(rep["results"]) == {"B1", B2_VARIANT}
    assert "B2" not in rep["results"]


def test_cli_report_and_exit_codes(tmp_path):
    script = ROOT / "scripts" / "stage9_baseline_select.py"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(
        {"docs": [{"doc_id": "fixture", "domain": "x", "split": "dev"}]}),
        encoding="utf-8")
    ann = _ann(STREAM, UNIT_TEXTS, SEGS)
    ann_dir = tmp_path / "annotations"
    ann_dir.mkdir()
    (ann_dir / "fixture.json").write_text(
        json.dumps(ann, ensure_ascii=False), encoding="utf-8")
    report = tmp_path / "report.json"

    def run(*args):
        return subprocess.run(
            [sys.executable, str(script),
             "--manifest", str(manifest),
             "--annotations", str(ann_dir), *args],
            capture_output=True, text=True, cwd=str(ROOT))

    ok = run("--report", str(report), "--json")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    payload = json.loads(ok.stdout)
    assert payload["doc_count"] == 1
    assert payload["selection"]["B1"]["n"] is not None
    assert payload["selection_rule"].startswith("macro ARI")
    disk = json.loads(report.read_text(encoding="utf-8"))
    assert disk["selection"] == payload["selection"]
    holdout = run("--split", "holdout")
    assert holdout.returncode == 2
    missing = run("--split", "comparison")
    assert missing.returncode == 2
