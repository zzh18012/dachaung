r"""parser 标签大小写不敏感、属性实体解
码、md 反斜杠转义字面（Round 1797）。

新角度：R1796 锁游离文本——**'<P
CLASS=x>a</P>' 大写标签+无引号属性照
识别（heading level 2 如常）；img 属性
内实体解码 alt='a&b'；md '\\## not
heading' 反斜杠保留原样、不识别标题；
正文 '\\*b\\*' 转义星号字面保留**零
覆盖：

- **大写 <P>/<H2>**：paragraph + heading
  level 2
- **alt="a&amp;b"**：'a&b'
- **'\\## x' / 'a \\*b\\* c'**：字面段落
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_html_case_insensitive_tags(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<P CLASS=x>a</P><H2>T</H2>',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a", {}),
        ("heading", "T", {"level": 2})]


def test_html_attr_entity_decoded(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<img alt="a&amp;b" src="x.png">',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.metadata)
            for e in doc.elements] == [
        ("image", {"alt": "a&b"})]


def test_md_backslash_escapes_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("\\## not heading", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "\\## not heading")]
    p = tmp_path / "e.md"
    p.write_text("a \\*b\\* c", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a \\*b\\* c"]
