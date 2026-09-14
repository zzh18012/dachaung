r"""html 控制字符保留 + 块嵌套违规 + 游离标题闭合（Round 1846）。

新角度（probe 实证，grep 核实全库零覆盖）：
- **unicode/控制分隔符逐字保留**：U+2028/U+0085(NEL)/VT 在 html 内容中
  原样保留（'a\\u2028b'），行号只被真实 \\n 推进——与 md 的
  splitlines() 语义（R1842：全部归一为 \\n 且当块级换行）成家族对照
- **块嵌套违规恢复**：`<p>a<h2>t</h2>b</p>` → 段落 'a' 被标题打断 flush、
  heading 't'（level 2、section_path='t'）、随后 loose 'b' 成新段落且
  **承袭 section_path='t'**（顺序式 heading→paragraph 承袭已有覆盖，
  打断-承袭无覆盖）
- **游离 </h1> 无操作**：当前 kind=paragraph 时 `</h1>` 不 flush、后续
  loose 数据继续并入（'posttail' 合并）——edges3 只覆盖了
  反方向（heading 时 `</p>` 无操作）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

U2028 = chr(0x2028)
NEL = chr(0x85)
VT = chr(0x0B)


def _parse(tmp_path: Path, text: str):
    p = tmp_path / "a.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_html_separators_preserved_verbatim(tmp_path: Path):
    doc = _parse(tmp_path, "<p>a" + U2028 + "b</p>\n<p>c</p>")
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "a" + U2028 + "b"
    assert doc.elements[0].source_locator == {"line": 1}
    assert doc.elements[1].content == "c"
    assert doc.elements[1].source_locator == {"line": 2}

    n = _parse(tmp_path, "<p>a" + NEL + "b</p>")
    assert n.elements[0].content == "a" + NEL + "b"
    v = _parse(tmp_path, "<p>a" + VT + "b</p>")
    assert v.elements[0].content == "a" + VT + "b"


def test_html_heading_inside_paragraph_nesting(tmp_path: Path):
    doc = _parse(tmp_path, "<p>a<h2>t</h2>b</p>")
    assert len(doc.elements) == 3
    first, heading, trailing = doc.elements
    assert first.type == "paragraph"
    assert first.content == "a"
    assert first.source_locator == {"line": 1}
    assert heading.type == "heading"
    assert heading.content == "t"
    assert heading.metadata == {"level": 2}
    assert heading.source_locator == {"line": 1, "section_path": "t"}
    assert trailing.type == "paragraph"
    assert trailing.content == "b"
    assert trailing.source_locator == {"line": 1, "section_path": "t"}


def test_html_stray_heading_close_no_flush(tmp_path: Path):
    doc = _parse(tmp_path, "pre</p>post</h1>tail")
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "pre"
    assert doc.elements[1].type == "paragraph"
    assert doc.elements[1].content == "posttail"
    assert doc.elements[1].source_locator == {"line": 1}
