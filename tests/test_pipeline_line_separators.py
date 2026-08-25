r"""pipeline 行分隔符归一：孤立 CR、\\f、
\\u2028、\\x85（Round 1623）。

新角度：R1622 锁空白家族——**非 \\n 行分隔符**
零覆盖：

- **孤立 \\r 归一为 \\n**（与 \\r\\n → \\n 同路；
  'alpha\\rbeta' → 'alpha\\nbeta' 单段）
- **\\f / \\u2028 / \\x85 惰性**：留在内容里
  原样（不构成换行、不分段）
- **只含 \\f 的行当空行**：分段且计行号
  （line 1 / line 3）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    return doc


def test_lone_cr_becomes_newline(tmp_path):
    doc = _run(
        tmp_path, "r.txt", "alpha\rbeta\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "alpha\nbeta")]


def test_exotic_separators_inert(tmp_path):
    for name, sep in [
            ("f.txt", "\x0c"),
            ("u.txt", chr(0x2028)),
            ("n.txt", chr(0x85))]:
        doc = _run(
            tmp_path, name,
            "alpha" + sep + "beta\n")
        assert [(e.type, e.content,
                 e.source_locator)
                for e in doc.elements] == [
            ("paragraph", "alpha" + sep + "beta",
             {"line": 1})], name


def test_formfeed_line_blank(tmp_path):
    doc = _run(
        tmp_path, "p.txt",
        "para a\n\x0c\npara b\n")
    assert [(e.content, e.source_locator)
            for e in doc.elements] == [
        ("para a", {"line": 1}),
        ("para b", {"line": 3})]
