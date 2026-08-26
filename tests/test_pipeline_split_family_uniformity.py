r"""pipeline 切分家族同谱：CJK 多路 forced、
句界跨 md/html/代码块（Round 1782）。

新角度：R1781 锁多路句界——**'字'*1800
三块 800/800/200：中间块 boundary
'forced_char'、末块 None；句界切分跨家族
统一：md 段落、html <p>、md 围栏代码块
的 7 句 1007 全部 723+283（尾 'S5.'）——
代码块并非 forced_char 专属，R1775 的
CJK 代码 forced 只因无空白**零覆盖：

- **'字'*1800**：800 forced+800 forced+
  200
- **md/html 段落句界**：723+283 两家族
  全同
- **围栏代码句界**：723+283，尾 'S5.'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _sentences():
    return " ".join(
        "S%d. %s" % (i, " ".join(f"w{i}_{j}" for j in range(25)))
        for i in range(7))


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_cjk_multiway_forced(tmp_path):
    p = _write(tmp_path, "d.txt", "字" * 1800 + "\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "forced_char"), (800, "forced_char"),
        (200, None)]


def test_sentence_split_family_uniform(tmp_path):
    for name, parser, text in [
        ("a.md", "markdown", _sentences() + "\n"),
        ("b.html", "html", "<p>" + _sentences() + "</p>"),
    ]:
        p = _write(tmp_path, name, text)
        doc, errors = process_single(
            p, write_json=False, parser_name=parser)
        assert errors == []
        assert [(len(c.text),
                 c.metadata.get("split_boundary_after"))
                for c in doc.chunks] == [
            (723, None), (283, None)]
        assert doc.chunks[0].text.endswith("S5.")


def test_code_fence_sentence_split(tmp_path):
    p = _write(
        tmp_path, "d.md",
        "```\n" + _sentences() + "\n```\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(len(c.text), c.text[-4:],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (723, " S5.", None), (283, "6_24", None)]
