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


def test_explicit_starts_preamble_single_group():
    # preamble（首起点之前的行）合并为单一组，其后按起点分组
    assert group_line_indices(5, [2]) == [[0, 1], [2, 3, 4]]


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


def test_partition_regex_preamble_single_group_v1():
    # 多行 preamble 合并为单一组（组内 v1，换行不是边界——十二轮修复）
    parts = ["References", "updated 2026.",
             "[1] Only one entry."] + REF_FOLDED[:2]
    groups = partition_entries(parts, NUM)
    assert [g[0] for g in groups] == [[0, 1], [2], [3, 4]]
    # preamble 两行折行同一句 → v1 单一 unit，起始源行 0
    assert groups[0][1] == [("References updated 2026.", 0)]


def test_preamble_wrapped_sentence_stays_v1_single_unit():
    # 十二轮裁决回归：两行换行包裹的同一句 preamble + 后随 [1]，
    # preamble 仍由 v1 处理，换行不产生额外边界（锁一）
    parts = ["These entries are sorted",
             "by publication year.",
             "[1] Devlin J, et al — BERT 2019"]
    groups = partition_entries(parts, NUM)
    assert [g[0] for g in groups] == [[0, 1], [2]]
    assert groups[0][1] == [
        (fold_ws("These entries are sorted by publication year."), 0)]


def test_preamble_two_sentences_v1_still_splits():
    # preamble 单组 ≠ 整段一 unit：v1 句切仍在运行（仅换行不是边界）
    groups = partition_entries(
        ["See the notes below. Entries follow.", "[1] first entry"], NUM)
    assert [u[0] for u in groups[0][1]] == [
        s for s in split_sentences(
            "See the notes below. Entries follow.") if s]


def test_partition_regex_no_match_raises():
    with pytest.raises(ValueError, match="未命中"):
        partition_entries(["no markers here"], NUM)


def test_partition_matches_scan_formula():
    # 与窄扫预演公式逐位一致：fold_ws(" ".join(行)) + 逐条目 v1
    #（preamble 行并入首个未起始组，与十二轮修复后口径一致）
    for parts in (REF_FOLDED, REF_SENTENCED, REF_FOLDED + REF_SENTENCED,
                  ["Preamble line one.", "Preamble two.",
                   "[1] single entry."]):
        entries, cur, pre = [], [], []
        for ln in parts:
            if NUM.match(ln):
                if cur:
                    entries.append(cur)
                cur = [ln]
            elif cur:
                cur.append(ln)
            else:
                pre.append(ln)
        if pre:
            entries.insert(0, pre)
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


def test_lines_block_with_entry_markers_not_auto_partitioned():
    # 范围契约（十二轮裁决）：NUM/LABEL 三通道只在显式 "entries" 块内
    # 运行；普通 "lines" 块即使内容匹配条目标记，也不触发条目分组
    ua = _load_user_annotate()
    reg = {
        (1, "L", 0): "Related Work",
        (1, "L", 1): "[1] alpha first line of a folded",
        (1, "L", 2): "citation that continues here.",
        (2, "L", 0): "[2] beta standalone.",
    }
    env = {
        "DOC": "test-doc",
        "ANNOTATOR": "test",
        "NOTES": "",
        "SEGMENTS": [("g00", "题名", "frontmatter"),
                     ("g01", "正文", "body")],
        "BLOCKS": [
            (((1, "L", 0),), "heading", "g00", True),
            (((1, "L", 1), (1, "L", 2), (2, "L", 0)), "lines", "g01",
             False),
        ],
    }
    ann, _ = ua.build_annotation(env, reg)
    sents = [u for u in ann["units"] if u["kind"] == "sentence"]
    # lines 语义 = 逐行一 unit；[1]/[2] 标记不触发条目合并/重切
    #（preview 含平铺尾随空格，rstrip 后比对）
    assert [u["text_preview"].rstrip(" ") for u in sents] == [
        "[1] alpha first line of a folded",
        "citation that continues here.",
        "[2] beta standalone."]
