r"""pipeline 超限切分落点：句界优先、
无标点回退空白（Round 1779）。

新角度：R1778 锁 html 同谱——**带句号文本
切在 ≤800 的最后一个句号处（首块尾
'S5.'，split_boundary_after 键不出现），
不按字符 800 硬切；无标点文本回退
whitespace（boundary='whitespace'）**
零覆盖：

- **7 句 ×144=1007**：723+283，首块尾
  'S5.'、boundary None
- **次块 'w5_0' 起头**：S5 标记留前块、
  词群入次块
- **纯词 979**：797 whitespace+181 回退
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _sentences():
    return " ".join(
        "S%d. %s" % (i, " ".join(f"w{i}_{j}" for j in range(25)))
        for i in range(7))


def test_sentence_boundary_preferred(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(_sentences() + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (723, "long_paragraph_sentence_split", None),
        (283, "long_paragraph_sentence_split", None)]
    assert doc.chunks[0].text.endswith("S5.")


def test_sentence_split_remainder_starts_mid_sentence(
        tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(_sentences() + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert doc.chunks[1].text.startswith("w5_0 ")


def test_whitespace_fallback_no_punctuation(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(" ".join(
        f"w{i}_{j}" for i in range(7)
        for j in range(25)) + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (797, "whitespace"), (181, None)]
