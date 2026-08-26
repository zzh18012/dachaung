r"""pipeline 属性值实体解码与深层容器
（Round 1669）。

新角度：R1668 锁单元格内联 raw——**alt 属
性值内实体照常解码、5 层嵌套容器全透明**
零覆盖：

- **alt 内实体**：'a&nbsp;b &amp; c' →
  'a\\xa0b & c'（\\xa0 与 & 都解码）
- **5 层 div 嵌套**：链条全透明，只留
  paragraph 'deep'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_entity_in_alt_decoded(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<img src='x.png' alt='a&nbsp;b &amp; c'>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None,
         {"alt": "a\xa0b & c"})]


def test_five_deep_divs_transparent(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<div><div><div><div><div><p>deep</p>"
        "</div></div></div></div></div>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "deep", {})]
