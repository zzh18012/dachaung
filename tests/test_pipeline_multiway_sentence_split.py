r"""pipeline 多路句界切分：逐窗递进、每窗
≤max_chars 内最后句号（Round 1781）。

新角度：R1780 锁句末符集——**18 句
2799 字符四块 723/720/679/674：每块尾
'S5.'/'S10.'/'S14.'/'w17_24'（前三块皆
句号、末块余文）；max_chars=200 三句
435 → 147/143/139 每窗刷新**零覆盖：

- **18 句四块**：块长精确、前三块尾句号
- **块间无内容丢失**：归一化拼接 == 原文
- **max_chars=200**：147/143/139
"""

from __future__ import annotations

import re

from pathlib import Path

from app.pipeline import process_single


def _sentences(n):
    return " ".join(
        "S%d. %s" % (i, " ".join(f"w{i}_{j}" for j in range(25)))
        for i in range(n))


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def test_multi_way_sentence_split(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(_sentences(18) + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    lens = [len(c.text) for c in doc.chunks]
    assert lens == [723, 720, 679, 674]
    assert all(
        c.metadata["strategy"]
        == "long_paragraph_sentence_split"
        for c in doc.chunks)
    assert all(
        c.metadata.get("split_boundary_after") is None
        for c in doc.chunks)
    for c in doc.chunks[:-1]:
        assert c.text.endswith(".")
    assert doc.chunks[-1].text.endswith("w17_24")


def test_multi_way_no_content_loss(tmp_path):
    src = _sentences(18)
    p = tmp_path / "d.txt"
    p.write_text(src + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    joined = " ".join(c.text for c in doc.chunks)
    assert _norm(joined) == _norm(src)


def test_custom_maxchars_sentence_windows(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(_sentences(3) + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text", max_chars=200)
    assert errors == []
    assert [len(c.text) for c in doc.chunks] == [
        147, 143, 139]
    assert doc.chunks[0].text.endswith("S1.")
    assert doc.chunks[1].text.endswith("S2.")
