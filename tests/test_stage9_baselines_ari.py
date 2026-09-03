# -*- coding: utf-8 -*-
"""Stage 9 批次 26：基线切分与 ARI 的手算 fixture（设计 §5 要求锁死）。"""
import pytest

from stage9.baselines import B2_SEPARATORS, b1_fixed_length, b2_recursive
from stage9.ari import ari_from_contingency, ari_units_vs_chunks
from stage9.normalize import fold_ws


class TestB1:
    def test_exact_cut(self):
        chunks = b1_fixed_length("a" * 10, 4)
        assert chunks == ["aaaa", "aaaa", "aa"]

    def test_short_stream_single_chunk(self):
        assert b1_fixed_length("abc", 200) == ["abc"]

    def test_empty(self):
        assert b1_fixed_length("", 200) == []

    def test_no_overlap_full_coverage(self):
        stream = fold_ws("第一句。 第二句。 第三句，较长一些。")
        chunks = b1_fixed_length(stream, 5)
        assert "".join(chunks) == stream
        assert all(len(c) == 5 for c in chunks[:-1])

    def test_invalid_n(self):
        with pytest.raises(ValueError):
            b1_fixed_length("abc", 0)


class TestB2:
    def test_paragraph_first(self):
        text = "A" * 30 + "\n\n" + "B" * 30
        chunks = b2_recursive(text, 40)
        assert chunks == ["A" * 30 + "\n\n", "B" * 30]

    def test_sentence_separator_recursion(self):
        # 30 字段落超 n=10：按 "。" 递归细分
        text = "甲" * 5 + "。" + "乙" * 5 + "。" + "丙" * 5 + "。"
        chunks = b2_recursive(text, 10)
        assert all(len(c) <= 10 for c in chunks)
        assert "".join(chunks) == text
        # 6+6=12 > 10 → 不并；三句各成块（≤n 不变量优先）
        assert chunks == ["甲" * 5 + "。", "乙" * 5 + "。", "丙" * 5 + "。"]

    def test_english_sentence(self):
        text = "One two three. Four five. Six."
        chunks = b2_recursive(text, 15)
        assert "".join(chunks) == text
        assert all(len(c) <= 15 for c in chunks)

    def test_space_fallback(self):
        text = "ab ab ab ab ab ab ab"
        chunks = b2_recursive(text, 5)
        assert "".join(chunks) == text
        assert all(len(c) <= 5 for c in chunks)

    def test_hard_char_fallback(self):
        text = "abcdefghij" * 5
        chunks = b2_recursive(text, 7)
        assert "".join(chunks) == text
        assert all(len(c) <= 7 for c in chunks)
        assert chunks == [text[i:i + 7] for i in range(0, len(text), 7)]

    def test_short_text_single_chunk(self):
        assert b2_recursive("短文", 100) == ["短文"]

    def test_separator_hierarchy_frozen(self):
        assert B2_SEPARATORS == ("\n\n", "\n", "。", "！", "？", "；", ". ",
                                 "! ", "? ", " ", "")

    def test_invalid_n(self):
        with pytest.raises(ValueError):
            b2_recursive("abc", -1)


class TestARI:
    def test_hand_computed_negative(self):
        """手算：n=6，g={3,3} c={3,3}，nij=[[2,1],[1,2]]：
        ΣC(nij,2)=2，ΣC(ai,2)=ΣC(bj,2)=6，C(6,2)=15，
        E=36/15=2.4，M=6，ARI=(2−2.4)/(6−2.4)=−1/9。"""
        ari, stats = ari_from_contingency([[2, 1], [1, 2]])
        assert ari == pytest.approx(-1 / 9)
        assert stats["n"] == 6
        assert stats["expected"] == pytest.approx(2.4)

    def test_perfect_clustering(self):
        ari, _ = ari_from_contingency([[3, 0], [0, 3]])
        assert ari == pytest.approx(1.0)

    def test_degenerate_both_single_cluster(self):
        # 两划分同为单簇：E=M → 分母 0 → 约定 1.0
        ari, stats = ari_from_contingency([[6]])
        assert ari == 1.0
        assert stats.get("degenerate") is True

    def test_insufficient_units(self):
        ari, stats = ari_from_contingency([[1]])
        assert ari is None
        assert stats["reason"] == "insufficient_units"

    def test_units_vs_chunks_labels(self):
        segs = ["g1", "g1", "g1", "g2", "g2", "g2"]
        chks = [0, 0, 1, 0, 1, 1]
        ari, _ = ari_units_vs_chunks(segs, chks)
        assert ari == pytest.approx(-1 / 9)

    def test_none_labels_excluded(self):
        # None 归属的 unit 不进 contingency（uncovered 披露由调用方负责）
        segs = ["g1", "g1", None, "g2", "g2"]
        chks = [0, 0, 0, None, 1]
        ari, stats = ari_units_vs_chunks(segs, chks)
        assert stats["n"] == 3
        assert ari is not None
