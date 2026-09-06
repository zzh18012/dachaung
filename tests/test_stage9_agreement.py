# -*- coding: utf-8 -*-
"""Stage 9 批次 26：双标注一致率测试（指南 §7 口径手算 fixture）。

口径：一致率 = 一致 unit 数 / 双方 unit 并集数；一致 = 文本对齐
（切分一致）且 kind 与 gold_segment 全等。所有分母/分子手算锁死。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from stage9.agreement import (
    AgreementInputError,
    compute_agreement,
    unit_key,
)

ROOT = Path(__file__).resolve().parents[1]


def _ann(doc_id, items):
    """items: (kind, text_or_ref, seg, hard)；kind h/s 文本单元，n 为
    nontext。文本单元以单空格拼接成流并平铺 span（与标注规范一致）。"""
    parts = []
    units = []
    pos = 0
    for idx, (kind, payload, seg, hard) in enumerate(items):
        unit = {"unit_id": "u%04d" % (idx + 1), "page": 1,
                "gold_segment_id": seg, "hard_boundary_before": hard}
        if kind == "n":
            unit.update(kind="nontext", char_span=None,
                        nontext_ref=payload)
        else:
            if parts:
                parts.append(" ")
                pos += 1
            start = pos
            parts.append(payload)
            pos += len(payload)
            unit.update(kind="heading" if kind == "h" else "sentence",
                        char_span=[start, pos], nontext_ref=None)
        units.append(unit)
    return {"doc_id": doc_id, "stream": "".join(parts), "units": units}


def test_identical_annotations_full_agreement():
    items = [("h", "Intro", "g01", True),
             ("s", "One two.", "g02", False),
             ("s", "Three.", "g02", False)]
    r = compute_agreement(_ann("d", items), _ann("d", items))
    assert r["agreement"] == 1.0
    assert (r["matched"], r["agree"], r["union"]) == (3, 3, 3)
    assert r["kind_diff"] == [] and r["segment_diff"] == []
    assert r["only_a"] == [] and r["only_b"] == []
    assert r["below_threshold"] is False


def test_segment_diff_counts_in_union_not_agree():
    a = _ann("d", [("h", "Intro", "g01", True),
                   ("s", "One two.", "g02", False),
                   ("s", "Three.", "g02", False)])
    b = _ann("d", [("h", "Intro", "g01", True),
                   ("s", "One two.", "g02", False),
                   ("s", "Three.", "g03", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 3 and r["agree"] == 2 and r["union"] == 3
    assert r["agreement"] == pytest.approx(2 / 3)
    assert len(r["segment_diff"]) == 1
    assert r["segment_diff"][0]["a"]["gold_segment_id"] == "g02"
    assert r["segment_diff"][0]["b"]["gold_segment_id"] == "g03"
    assert r["below_threshold"] is True


def test_kind_diff_aligned_by_text():
    a = _ann("d", [("h", "Intro", "g01", True),
                   ("s", "One two.", "g02", False),
                   ("s", "Three.", "g02", False)])
    b = _ann("d", [("h", "Intro", "g01", True),
                   ("h", "One two.", "g02", False),
                   ("s", "Three.", "g02", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 3 and r["agree"] == 2 and r["union"] == 3
    assert r["agreement"] == pytest.approx(2 / 3)
    assert len(r["kind_diff"]) == 1
    assert r["kind_diff"][0]["a"]["kind"] == "sentence"
    assert r["kind_diff"][0]["b"]["kind"] == "heading"


def test_split_difference_unmatched_both_sides():
    a = _ann("d", [("h", "Intro", "g01", True),
                   ("s", "Abc def.", "g02", False),
                   ("s", "Ghi.", "g02", False)])
    b = _ann("d", [("h", "Intro", "g01", True),
                   ("s", "Abc.", "g02", False),
                   ("s", "def.", "g02", False),
                   ("s", "Ghi.", "g02", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 2 and r["agree"] == 2
    assert r["union"] == 3 + 4 - 2
    assert r["agreement"] == pytest.approx(2 / 5)
    assert [u["preview"] for u in r["only_a"]] == ["Abc def."]
    assert [u["preview"] for u in r["only_b"]] == ["Abc.", "def."]


def test_repeated_text_aligns_by_position():
    a = _ann("d", [("s", "Note", "g01", False),
                   ("s", "Note", "g01", False),
                   ("s", "Note", "g01", False)])
    b = _ann("d", [("s", "Note", "g01", False),
                   ("s", "Note", "g02", False),
                   ("s", "Note", "g02", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 3 and r["agree"] == 1
    assert r["agreement"] == pytest.approx(1 / 3)
    assert len(r["segment_diff"]) == 2


def test_nontext_identity_independent_of_naming():
    # 跨标注人命名未冻结（img:fig-1 vs img:1 并存）：对齐键=家族+页+
    # 页内阅读序号，与命名字符串无关（2026-09-06 修正，测量前落定）
    a = _ann("d", [("s", "Text one.", "g01", False),
                   ("n", "img:fig-1", "g01", False)])
    b = _ann("d", [("s", "Text one.", "g01", False),
                   ("n", "img:1", "g01", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 2 and r["agree"] == 2
    assert r["union"] == 2 and r["agreement"] == 1.0
    same = compute_agreement(a, a)
    assert same["agreement"] == 1.0 and same["matched"] == 2


def test_nontext_different_family_no_match():
    # img vs tab 同页同序：族不同 → 不匹配
    a = _ann("d", [("n", "img:fig-1", "g01", False)])
    b = _ann("d", [("n", "tab:1", "g01", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 0 and r["union"] == 2
    assert r["agreement"] == 0.0


def test_nontext_missed_image_costs_itself_only():
    # b 漏登一张图：b 的单图按页内序拿序号 1，与 a 的第一张对上；
    # a 的第二张落单（多登记方自付，不殃及对齐）
    a = _ann("d", [("n", "img:fig-1", "g01", False),
                   ("n", "img:fig-2", "g01", False)])
    b = _ann("d", [("n", "img:1", "g01", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 1 and r["agree"] == 1
    assert r["union"] == 2
    assert len(r["only_a"]) == 1 and r["only_a"][0]["kind"] == "nontext"


def test_nontext_ordinal_is_per_page():
    # 页内序：同在页 2 的首图互相匹配；页 2 vs 页 3 的首图不匹配
    a = _ann("d", [("n", "img:fig-1", "g01", False)])
    a["units"][0]["page"] = 2
    b = _ann("d", [("n", "img:1", "g01", False)])
    b["units"][0]["page"] = 2
    assert compute_agreement(a, b)["matched"] == 1
    b["units"][0]["page"] = 3
    assert compute_agreement(a, b)["matched"] == 0


def test_nontext_key_via_annotation_unit_keys():
    from stage9.agreement import (AgreementInputError,
                                  annotation_unit_keys)
    ann = _ann("d", [("n", "img:fig-9", "g01", False),
                     ("n", "img:fig-10", "g01", False),
                     ("n", "tab:2", "g02", False)])
    assert annotation_unit_keys(ann) == [
        ("nontext", "img", 1, 1), ("nontext", "img", 1, 2),
        ("nontext", "tab", 1, 1)]
    with pytest.raises(AgreementInputError):
        unit_key(ann, ann["units"][0])


def test_hard_boundary_is_informational_only():
    a = _ann("d", [("h", "Intro", "g01", True),
                   ("s", "One two.", "g02", False)])
    b = _ann("d", [("h", "Intro", "g01", False),
                   ("s", "One two.", "g02", True)])
    r = compute_agreement(a, b)
    assert r["agreement"] == 1.0
    assert r["hard_boundary_diff"] == 2


def test_doc_id_mismatch_raises():
    with pytest.raises(AgreementInputError):
        compute_agreement(_ann("d1", [("s", "X.", "g01", False)]),
                          _ann("d2", [("s", "X.", "g01", False)]))


def test_empty_union_undefined_agreement():
    empty = {"doc_id": "d", "stream": "", "units": []}
    r = compute_agreement(empty, empty)
    assert r["agreement"] is None
    assert r["union"] == 0 and r["below_threshold"] is False


def test_unit_key_uses_stripped_stream_text():
    # 平铺规则：unit 间分隔空格归前一 unit 的 span 末尾（流为 fold-ws）
    ann = {"doc_id": "d", "stream": "Alpha Beta.",
           "units": [{"kind": "sentence", "char_span": [0, 6],
                      "nontext_ref": None}]}
    assert unit_key(ann, ann["units"][0]) == "Alpha"


def test_cli_exit_codes_and_json(tmp_path):
    script = ROOT / "scripts" / "stage9_agreement.py"
    items = [("h", "Intro", "g01", True),
             ("s", "One two.", "g02", False),
             ("s", "Three.", "g02", False)]
    a = tmp_path / "a.json"
    a.write_text(json.dumps(_ann("d", items), ensure_ascii=False),
                 encoding="utf-8")
    b = tmp_path / "b.json"
    diff = list(items)
    diff[2] = ("s", "Three.", "g03", False)
    b.write_text(json.dumps(_ann("d", diff), ensure_ascii=False),
                 encoding="utf-8")

    def run(*args):
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True, text=True, cwd=str(ROOT))

    full = run("--a", str(a), "--b", str(a))
    assert full.returncode == 0, full.stdout + full.stderr
    assert "1.0000" in full.stdout
    low = run("--a", str(a), "--b", str(b))
    assert low.returncode == 1
    assert "0.6667" in low.stdout
    assert "gold_segment" in low.stdout
    missing = run("--a", str(a), "--b", str(tmp_path / "nope.json"))
    assert missing.returncode == 2
    as_json = run("--a", str(a), "--b", str(b), "--json")
    payload = json.loads(as_json.stdout)
    assert payload["doc_id"] == "d"
    assert payload["agreement"] == pytest.approx(2 / 3)
    assert payload["below_threshold"] is True
    assert len(payload["segment_diff"]) == 1
