r"""pipeline 无空白文本 forced_char：长单
词、混排粘接；全角/组合字符原样（Round 1810）。

新角度：R1809 锁切分块 metadata——**'a'
×900 无空格拉丁长词 → 800 forced_char+
100（无句界无空白 → 直落第三档 forced）；
字×450+q×450 混排粘接 → 800 forced+
100（切点不看文字边界）；'ＡＢＣ é'
全角+组合字符原样保留（无规范化、len
5）**零覆盖：

- **长词**：forced_char 而非
  whitespace
- **混排**：800/100 跨文字切
- **全角**：逐字符原样
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_long_word_forced_char(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("a" * 900 + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "forced_char"), (100, None)]


def test_mixed_script_glued_split(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("字" * 450 + "q" * 450 + "\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "forced_char"), (100, None)]


def test_fullwidth_combining_preserved(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("ＡＢＣ é\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "ＡＢＣ é"]
    assert len(doc.elements[0].content) == 5
