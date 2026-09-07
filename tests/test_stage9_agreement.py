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
    # 契约 1（ref 仅改名 agreement 不变）：跨标注人命名未冻结
    # （img:fig-1 vs img:1 并存）：对齐键=家族+物理页（v3-page-family），
    # 与命名字符串无关（2026-09-07 裁决 B 修正：键不含任何标注自序编号）
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
    # img vs tab 同页：族不同 → 不匹配
    a = _ann("d", [("n", "img:fig-1", "g01", False)])
    b = _ann("d", [("n", "tab:1", "g01", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 0 and r["union"] == 2
    assert r["agreement"] == 0.0


def test_nontext_missed_image_costs_itself_only():
    # 契约 2（漏登页首一个 nontext 只罚该对象，后续仍正常对齐）：
    # b 漏登一张图：同页同族其余对象仍按结构位置配对，matched/union
    # 精确；漏登方自付，不殃及后续对齐（无任何按标注自序的编号可漂移）
    a = _ann("d", [("n", "img:fig-1", "g01", False),
                   ("n", "img:fig-2", "g01", False)])
    b = _ann("d", [("n", "img:1", "g01", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 1 and r["agree"] == 1
    assert r["union"] == 2
    assert len(r["only_a"]) == 1 and r["only_a"][0]["kind"] == "nontext"


def test_nontext_page_leading_miss_pollutes_nothing():
    # 契约 2 强化版（裁决 B 原例）：页首 img 漏登后，同页同族后续
    # 两个对象仍全部对上（matched=2），下一页对象也不受影响
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g01", False),
                   ("n", "img:c", "g01", False),
                   ("n", "img:d", "g01", False)])
    a["units"][3]["page"] = 2
    b = _ann("d", [("n", "img:b", "g01", False),
                   ("n", "img:c", "g01", False),
                   ("n", "img:d", "g01", False)])
    b["units"][2]["page"] = 2
    r = compute_agreement(a, b)
    assert r["matched"] == 3 and r["agree"] == 3
    assert r["union"] == 4 and r["agreement"] == pytest.approx(3 / 4)
    assert len(r["only_a"]) == 1 and not r["only_b"]
    # B' 口径：页 1 组（a=3, b=2）属歧义组，但各配对贡献相同（同
    # seg）→ 区间退化单值——漏登恰只罚该对象（上界即 3/4）
    assert r["ambiguous_group_count"] == 1
    g = r["ambiguous_groups"][0]
    assert g["group"] == ["img", 1]
    assert (g["side_a"], g["side_b"], g["matched"]) == (3, 2, 2)
    assert (g["contribution_lower"], g["contribution_upper"]) == (2, 2)
    assert r["agreement_lower"] == pytest.approx(3 / 4)
    assert r["agreement_upper"] == pytest.approx(3 / 4)
    assert r["decision"] == "below_threshold"


def test_nontext_family_interleave_no_identity_collision():
    # 契约 3（img/tab 交错不碰撞）：同页同序时 img 与 tab 各自对齐
    # （matched=2，无族间误配）
    a = _ann("d", [("n", "img:1", "g01", False),
                   ("n", "tab:1", "g02", False)])
    b = _ann("d", [("n", "tab:x", "g02", False),
                   ("n", "img:y", "g01", False)])
    same = compute_agreement(a, a)
    assert same["matched"] == 2 and same["agree"] == 2
    assert same["kind_diff"] == [] and same["agreement"] == 1.0
    # 顺序颠倒（阅读序分歧）：SequenceMatcher 只配得一对，但**绝不
    # 产生 img↔tab 族间误配**（kind_diff 恒空）；未配上的一对如实
    # 进 only_a/only_b——交叉序分歧本身应计入一致率惩罚
    r = compute_agreement(a, b)
    assert r["matched"] == 1 and r["agree"] == 1
    assert r["kind_diff"] == [] and r["segment_diff"] == []
    assert len(r["only_a"]) == 1 and len(r["only_b"]) == 1
    assert r["union"] == 3 and r["agreement"] == pytest.approx(1 / 3)


def test_nontext_keys_deterministic_on_repeat():
    # 契约 4（同一输入重复运行键完全相同、报告逐字段相等）
    from stage9.agreement import annotation_unit_keys
    a = _ann("d", [("s", "T.", "g01", False),
                   ("n", "img:fig-1", "g01", False),
                   ("n", "tab:2", "g02", False)])
    b = _ann("d", [("s", "T.", "g01", False),
                   ("n", "img:2", "g01", False),
                   ("n", "tab:t", "g02", False)])
    assert annotation_unit_keys(a) == annotation_unit_keys(b)
    assert compute_agreement(a, b) == compute_agreement(a, b)


def test_report_records_nontext_alignment_version():
    # 契约 5（报告记录算法版本）
    a = _ann("d", [("n", "img:fig-1", "g01", False)])
    r = compute_agreement(a, a)
    assert r["nontext_alignment"] == "v3-page-family-bounded"
    assert r["ambiguous_group_count"] == 0  # 单对象组不属歧义组
    assert r["agreement_lower"] == r["agreement_upper"] == 1.0
    assert r["decision"] == "pass"


def test_nontext_key_is_per_page_family():
    # 页维度：同在页 2 的图互相匹配；页 2 vs 页 3 的图不匹配
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
        ("nontext", "img", 1), ("nontext", "img", 1),
        ("nontext", "tab", 1)]
    with pytest.raises(AgreementInputError):
        unit_key(ann, ann["units"][0])


def test_ambiguous_group_interval_hand_computed():
    # 裁决 B' 例：同页同族双方各 2 对象、seg 一致但身份不可辨识——
    # 合法配对 [正配 2 全等, 交叉配 0 全等] → 全篇 [0/2, 2/2] 不可判定
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g02", False)])
    b = _ann("d", [("n", "img:x", "g01", False),
                   ("n", "img:y", "g02", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 2 and r["union"] == 2
    assert r["ambiguous_group_count"] == 1
    g = r["ambiguous_groups"][0]
    assert (g["side_a"], g["side_b"], g["matched"]) == (2, 2, 2)
    assert (g["contribution_lower"], g["contribution_upper"]) == (0, 2)
    assert r["agree_lower"] == 0 and r["agree_upper"] == 2
    assert r["agreement_lower"] == pytest.approx(0.0)
    assert r["agreement_upper"] == pytest.approx(1.0)
    assert r["decision"] == "indeterminate"
    assert r["below_threshold"] is True  # 不可判定=需处置（CLI rc 1）
    # 结构配对是合法配对之一 → 诊断值必落在区间内
    assert r["agreement_lower"] <= r["agreement"] <= r["agreement_upper"]


def test_ambiguous_group_degenerate_interval():
    # 各配对贡献相同（全同 seg）→ lower=upper 自然退化单值（裁决 B'）
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g01", False)])
    b = _ann("d", [("n", "img:x", "g01", False),
                   ("n", "img:y", "g01", False)])
    r = compute_agreement(a, b)
    assert r["ambiguous_group_count"] == 1
    g = r["ambiguous_groups"][0]
    assert (g["contribution_lower"], g["contribution_upper"]) == (2, 2)
    assert r["agreement_lower"] == r["agreement_upper"] == pytest.approx(1.0)
    assert r["decision"] == "pass" and r["agreement"] == 1.0
    assert r["below_threshold"] is False


def test_single_side_multi_not_ambiguous():
    # 单侧多对象（另一侧 ≤1）不属歧义组（裁决"≤1 对象正常算"）：
    # 结构配对照算、出确定值（本例配上的对 seg 不同 → 0.0）
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g02", False)])
    b = _ann("d", [("n", "img:x", "g02", False)])
    r = compute_agreement(a, b)
    assert r["ambiguous_group_count"] == 0
    assert r["agreement_lower"] == r["agreement_upper"] == pytest.approx(0.0)
    assert r["decision"] == "below_threshold"
    assert len(r["segment_diff"]) == 1


def test_mixed_text_and_ambiguous_bounds():
    # 文本对固定贡献 + 歧义组区间独立合成：[1/3, 3/3]
    a = _ann("d", [("s", "T.", "g01", False),
                   ("n", "img:a", "g01", False),
                   ("n", "img:b", "g02", False)])
    b = _ann("d", [("s", "T.", "g01", False),
                   ("n", "img:x", "g01", False),
                   ("n", "img:y", "g02", False)])
    r = compute_agreement(a, b)
    assert r["matched"] == 3 and r["union"] == 3
    assert r["agree_lower"] == 1 and r["agree_upper"] == 3
    assert r["agreement_lower"] == pytest.approx(1 / 3)
    assert r["agreement_upper"] == pytest.approx(1.0)
    assert r["decision"] == "indeterminate"


def test_pair_map_resolves_indeterminate():
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g02", False)])
    b = _ann("d", [("n", "img:x", "g01", False),
                   ("n", "img:y", "g02", False)])
    pm = {"img|1": [["u0001", "u0001"], ["u0002", "u0002"]]}
    r = compute_agreement(a, b, pair_map=pm, pair_map_sha256="ab" * 32)
    assert r["decision"] == "pass" and r["agreement"] == 1.0
    assert r["agree_lower"] == r["agree_upper"] == 2
    assert r["ambiguous_groups"][0]["resolved"] is True
    assert r["ambiguous_groups"][0]["contribution_lower"] == 2
    assert r["identity_resolution"] == {
        "pair_map_sha256": "ab" * 32, "resolved_group_count": 1}
    # 交叉配对同样合法（resolution 只定身份不改判断）→ 0 全等
    crossed = {"img|1": [["u0001", "u0002"], ["u0002", "u0001"]]}
    r2 = compute_agreement(a, b, pair_map=crossed, pair_map_sha256="00")
    assert r2["agreement"] == 0.0 and r2["decision"] == "below_threshold"
    assert len(r2["segment_diff"]) == 2  # 解析配对上的差异逐条可见
    assert r2["ambiguous_groups"][0]["resolved"] is True


def test_pair_map_rejects_illegal():
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g02", False)])
    b = _ann("d", [("n", "img:x", "g01", False),
                   ("n", "img:y", "g02", False)])
    with pytest.raises(AgreementInputError):  # 配对数 ≠ matched
        compute_agreement(a, b, pair_map={"img|1": [["u0001", "u0001"]]})
    with pytest.raises(AgreementInputError):  # 非单射
        compute_agreement(a, b, pair_map={
            "img|1": [["u0001", "u0001"], ["u0001", "u0002"]]})
    with pytest.raises(AgreementInputError):  # 引用组外 unit_id
        compute_agreement(a, b, pair_map={
            "img|1": [["u0009", "u0001"], ["u0002", "u0002"]]})
    with pytest.raises(AgreementInputError):  # 组不存在
        compute_agreement(a, b, pair_map={
            "img|2": [["u0001", "u0001"], ["u0002", "u0002"]]})
    # 非歧义组（b 侧单对象）不许 identity resolution
    c = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g01", False)])
    d = _ann("d", [("n", "img:x", "g01", False)])
    with pytest.raises(AgreementInputError):
        compute_agreement(c, d, pair_map={"img|1": [["u0001", "u0001"]]})


def test_group_contribution_bounds_bruteforce_crosscheck():
    # 2×2 与 3×3 全矩阵 × 全部 k：匹配法精确 = 暴力枚举所有恰 k 对
    # 单射配对的 min/max（算法正确性锁死）
    import itertools
    from stage9.agreement import _group_contribution_bounds
    for m, n in ((2, 2), (3, 3)):
        for bits in range(1 << (m * n)):
            agree = [[(bits >> (i * n + j)) & 1 == 1
                      for j in range(n)] for i in range(m)]
            for k in range(min(m, n) + 1):
                lo, hi = _group_contribution_bounds(
                    range(m), range(n), k, lambda i, j: agree[i][j])
                worst = best = None
                for ai in itertools.combinations(range(m), k):
                    for bj in itertools.permutations(range(n), k):
                        s = sum(1 for i, j in zip(ai, bj) if agree[i][j])
                        worst = s if worst is None else min(worst, s)
                        best = s if best is None else max(best, s)
                assert (lo, hi) == (worst, best)


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
    assert payload["decision"] == "below_threshold"
    assert payload["nontext_alignment"] == "v3-page-family-bounded"
    assert payload["ambiguous_group_count"] == 0
    assert len(payload["segment_diff"]) == 1


def test_cli_pair_map_resolution(tmp_path):
    import hashlib
    script = ROOT / "scripts" / "stage9_agreement.py"
    a = _ann("d", [("n", "img:a", "g01", False),
                   ("n", "img:b", "g02", False)])
    b = _ann("d", [("n", "img:x", "g01", False),
                   ("n", "img:y", "g02", False)])
    pa = tmp_path / "a.json"
    pb = tmp_path / "b.json"
    pa.write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    pb.write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")

    def run(*args):
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True, text=True, cwd=str(ROOT))

    base = run("--a", str(pa), "--b", str(pb), "--json")
    payload = json.loads(base.stdout)
    assert base.returncode == 1  # indeterminate → 需处置（非 pass）
    assert payload["decision"] == "indeterminate"
    assert payload["ambiguous_group_count"] == 1
    assert payload["identity_resolution"] is None

    pm = tmp_path / "pairmap.json"
    pm.write_text(json.dumps({"img|1": [["u0001", "u0001"],
                                        ["u0002", "u0002"]]},
                             ensure_ascii=False), encoding="utf-8")
    sha = hashlib.sha256(pm.read_bytes()).hexdigest()
    ok = run("--a", str(pa), "--b", str(pb), "--pair-map", str(pm),
             "--json")
    payload2 = json.loads(ok.stdout)
    assert ok.returncode == 0
    assert payload2["decision"] == "pass" and payload2["agreement"] == 1.0
    assert payload2["identity_resolution"] == {
        "pair_map_sha256": sha, "resolved_group_count": 1}

    bad = tmp_path / "badmap.json"
    bad.write_text(json.dumps({"img|1": [["u0001", "u0001"]]},
                              ensure_ascii=False), encoding="utf-8")
    illegal = run("--a", str(pa), "--b", str(pb), "--pair-map",
                  str(bad), "--json")
    assert illegal.returncode == 2
    assert json.loads(illegal.stdout)["ok"] is False
