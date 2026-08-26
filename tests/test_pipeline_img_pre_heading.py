r"""pipeline img 破坏 pre 与标题内联全 raw
（Round 1678）。

新角度：R1677 锁同级替换——**img 把 pre 拆
三段（尾段丢失 pre 标记）、md 标题内链
接/图片语法全 raw**零覆盖：

- **img 进 pre**：paragraph 'a'（仍
  preformatted）+ image + paragraph 'b'
  （普通段）——img 提取优先于 pre 容器
- **标题内链接 raw**：'# H [x](u) tail'
  → heading 原样
- **标题内图片 raw**：'![i](x.png)' 同样
  原样，无 image 元素
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_img_breaks_pre(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<pre>a<img src='x.png' alt='IA'>b</pre>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a", {"kind": "preformatted"}),
        ("image", None, {"alt": "IA"}),
        ("paragraph", "b", {})]


def test_link_in_heading_raw(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# H [x](u) tail\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "H [x](u) tail", {"level": 1})]


def test_img_syntax_in_heading_raw(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# H ![i](x.png) tail\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "H ![i](x.png) tail",
         {"level": 1})]
    assert [e.type for e in doc.elements] == [
        "heading"]
