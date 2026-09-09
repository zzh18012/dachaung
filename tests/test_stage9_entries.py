# -*- coding: utf-8 -*-
"""stage9.entries（结构化条目划分层，指南 §3.1 / R3' 2026-09-09）测试。"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

from stage9.entries import (entry_units, group_line_indices,
                            partition_entries)
from stage9.normalize import fold_ws
from stage9.splitter import split_sentences

NUM = re.compile(r"^\[\d+\]\s*")


def _load_user_annotate():
    spec = importlib.util.spec_from_file_location(
        "stage9_user_annotate_for_test",
        ROOT / "scripts" / "stage9_user_annotate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- group_line_indices（显式起点形态） ----------

def test_explicit_starts_grouping():
    # 行 0、2 开条目：[[0,1],[2,3,4]]
    assert group_line_indices(5, [0, 2]) == [[0, 1], [2, 3, 4]]


def test_explicit_starts_first_not_zero_preamble_own_groups():
    # preamble 行各自成组，其后按起点分组
    assert group_line_indices(5, [2]) == [[0], [1], [2, 3, 4]]


@pytest.mark.parametrize("idx", [[], [1, 1], [2, 1], [3], [-1], ["0"],
                                 [True]])
def test_explicit_starts_invalid(idx):
    with pytest.raises(ValueError):
        group_line_indices(3, idx)


def test_explicit_starts_rejects_regex():
    with pytest.raises(ValueError):
        group_line_indices(3, re.compile(r"^\["))


# ---------- partition_entries（regex 形态） ----------

REF_FOLDED = [
    "[1] Devlin J, Chang M W, Lee K, Toutanova K — BERT: Pre-training",
    "of Deep Bidirectional Transformers for Language Understanding 2019",
    "[2] Vaswani A, et al — Attention Is All You Need 2017",
]
REF_SENTENCED = [
    "[3] Brown T. Language models are few-shot learners. 2020. This",
    "entry has real sentence ends. Second sentence here.",
]


def test_partition_regex_grouping_folded_entry_one_unit():
    groups = partition_entries(REF_FOLDED, NUM)
    assert [g[0] for g in groups] == [[0, 1], [2]]
    # 条目 1 无句末切分点（"." 后随小写/逗号）→ 整条目一 unit（锁一+锁二）
    assert len(groups[0][1]) == 1
    assert groups[0][1][0][0] == fold_ws(" ".join(REF_FOLDED[:2]))
    assert groups[1][1][0][0] == REF_FOLDED[2]


def test_partition_regex_multi_unit_entry_has_line_attribution():
    groups = partition_entries(REF_SENTENCED, NUM)
    assert len(groups) == 1 and groups[0][0] == [0, 1]
    texts = [u[0] for u in groups[0][1]]
    assert texts == [s for s in split_sentences(
        fold_ws(" ".join(REF_SENTENCED))) if s]
    # "Second sentence here." 起始字符落在源行 1
    assert groups[0][1][0][1] == 0
    assert groups[0][1][-1][1] == 1


def test_partition_regex_preamble_lines_own_groups():
    parts = ["References", "[1] Only one entry."] + REF_FOLDED
    groups = partition_entries(parts, NUM)
    assert [g[0] for g in groups] == [[0], [1], [2, 3], [4]]


def test_partition_regex_no_match_raises():
    with pytest.raises(ValueError, match="未命中"):
        partition_entries(["no markers here"], NUM)


def test_partition_matches_scan_formula():
    # 与窄扫预演公式逐位一致：fold_ws(" ".join(行)) + 逐条目 v1
    for parts in (REF_FOLDED, REF_SENTENCED, REF_FOLDED + REF_SENTENCED):
        entries, cur = [], []
        for ln in parts:
            if NUM.match(ln):
                if cur:
                    entries.append(cur)
                cur = [ln]
            elif cur:
                cur.append(ln)
            else:
                entries.append([ln])
        if cur:
            entries.append(cur)
        scan_units = []
        for ent in entries:
            text = fold_ws(" ".join(x for x in ent if x))
            sents = [s for s in split_sentences(text) if s]
            scan_units.extend(sents if sents else [text])
        tool_units = [u[0] for _, us in partition_entries(parts, NUM)
                      for u in us]
        assert tool_units == scan_units


def test_partition_empty_and_blank_lines():
    with pytest.raises(ValueError, match="未命中"):
        partition_entries([""], NUM)
    groups = partition_entries(["[1] a", "", "[2] b"], NUM)
    assert [g[0] for g in groups] == [[0, 1], [2]]
    assert groups[0][1] == [("[1] a", 0)]


def test_entry_units_multispace_folded():
    assert entry_units(["[1]  a   b", "c  d"]) == [("[1] a b c d", 0)]


# ---------- assembler 集成（entries 块 → v1.1 标注） ----------

REG = {
    (1, "L", 0): "Related Work",
    (1, "L", 1): "[1] Devlin J, Chang M W — BERT: Pre-training of Deep",
    (1, "L", 2): "Bidirectional Transformers 2019",
    (2, "L", 0): "[2] Vaswani A, et al — Attention Is All You Need",
    (2, "L", 1): "2017",
}


def _build(blocks):
    ua = _load_user_annotate()
    env = {
        "DOC": "test-doc",
        "ANNOTATOR": "test",
        "NOTES": "",
        "SEGMENTS": [("g00", "题名", "frontmatter"),
                     ("g01", "参考文献", "backmatter")],
        "BLOCKS": blocks,
    }
    return ua.build_annotation(env, dict(REG))


ENTRY_KEYS = (((1, "L", 1), (1, "L", 2), (2, "L", 0), (2, "L", 1)))


def test_build_annotation_entries_block():
    from stage9.validation import validate_annotation
    ann, seg_ids = _build([
        (((1, "L", 0),), "heading", "g00", True),
        (ENTRY_KEYS, "entries", "g01", False, NUM),
    ])
    assert seg_ids == ["g00", "g01"]
    sents = [u for u in ann["units"] if u["kind"] == "sentence"]
    # 条目 1 无切分点整条一 unit；条目 2 跨页折行整条一 unit
    assert len(sents) == 2
    assert sents[0]["page"] == 1
    assert sents[1]["page"] == 2  # 起始源行在页 2
    # hard：首组首 unit 取块 hard=False，第二组首 unit True
    assert sents[0]["hard_boundary_before"] is False
    assert sents[1]["hard_boundary_before"] is True
    # 条目文本完整入流（锁一：折行合并；平铺规则 span 末含分隔空格）
    assert fold_ws(" ".join([
        "[1] Devlin J, Chang M W — BERT: Pre-training of Deep",
        "Bidirectional Transformers 2019"])) == \
        ann["stream"][sents[0]["char_span"][0]:
                      sents[0]["char_span"][1]].rstrip(" ")
    doc_id, fails = validate_annotation(ann, None)
    assert doc_id == "test-doc" and fails == []


def test_build_annotation_entries_explicit_starts():
    ann, _ = _build([
        (((1, "L", 0),), "heading", "g00", True),
        (ENTRY_KEYS, "entries", "g01", False, (0, 2)),
    ])
    sents = [u for u in ann["units"] if u["kind"] == "sentence"]
    assert len(sents) == 2  # 显式起点同分组


def test_build_annotation_entries_missing_spec_raises():
    with pytest.raises(SystemExit, match="第 5 元素"):
        _build([
            (((1, "L", 0),), "heading", "g00", True),
            (((1, "L", 1), (1, "L", 2)), "entries", "g01", False),
        ])


def test_build_annotation_entries_bad_start_raises():
    with pytest.raises(SystemExit, match="边界判断错误"):
        _build([
            (((1, "L", 0),), "heading", "g00", True),
            (((1, "L", 1), (1, "L", 2)), "entries", "g01", False, (7,)),
        ])
