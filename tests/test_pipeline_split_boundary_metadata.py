r"""pipeline 切分边界元数据三态：句界省略、
whitespace、forced_char（Round 1722）。

新角度：R1721 锁 forced_char——**'word. '
句点结尾文本在句界切分（split_boundary_
after 键省略）、CJK 恰 800 不切、CJK 802
强制切、句号后短词混排不切**零覆盖：

- **'word. '*200（1200 字符）**：797+401
  两块，块尾 'rd.'（句界切分，metadata 无
  split_boundary_after 键）
- **CJK 恰 800**：单 chunk 800（边界不切）
- **CJK 802**：800 forced_char + 2
- **3 句长句 + 'a '*300（666 字符）**：单
  chunk 665
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _chunks(tmp_path, text):
    p = tmp_path / "d.txt"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    return doc.chunks


def test_sentence_boundary_split_omits_key(tmp_path):
    chunks = _chunks(tmp_path, "word. " * 200)
    assert [len(c.text) for c in chunks] == [797, 401]
    assert chunks[0].text.endswith("rd.")
    for c in chunks:
        assert "split_boundary_after" not in c.metadata
        assert c.metadata["strategy"] == \
            "long_paragraph_sentence_split"


def test_cjk_exact_800_one_chunk(tmp_path):
    chunks = _chunks(tmp_path, "字" * 800)
    assert len(chunks) == 1
    assert len(chunks[0].text) == 800


def test_cjk_802_forced(tmp_path):
    chunks = _chunks(tmp_path, "字" * 802)
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in chunks] == [
        (800, "forced_char"), (2, None)]


def test_mixed_sentence_short_under_limit(tmp_path):
    chunks = _chunks(
        tmp_path, "sentence one is here. " * 3 + "a " * 300)
    assert len(chunks) == 1
    assert len(chunks[0].text) == 665
