r"""html xml 声明/条件注释/NUL 字节/emoji 字符引用测试（Round 1844）。

新角度（probe 实证，grep 核实 html 测试对 '<?xml' 声明、条件注释
'<!--[if'、输入 NUL、超 BMP 数字字符引用全零覆盖）：
- **xml 声明整段丢弃**：'<?xml version="1.0"?>' 前缀不产生元素、
  无 warning，后续内容照常解析（XHTML 文件可吃）
- **条件注释当注释丢弃**：'<!--[if IE]><p>ie only</p><![endif]-->'
  整块消失——downlevel-revealed 内容不泄漏成元素，前后段落原样
- **NUL 字节字面保留**：'before' + NUL + 'after' 的 content 保留
  NUL 字符（不剥离不替换）；**超 BMP 数字字符引用正确解码**：
  '&#128512;' 十进制与 '&#x1F600;' 十六进制都出 U+1F600 emoji
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

NUL = "\x00"
EMOJI = chr(0x1F600)


def _html(tmp_path: Path, data):
    p = tmp_path / "r1844.html"
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_html_xml_declaration_dropped(tmp_path: Path):
    doc = _html(tmp_path, '<?xml version="1.0" encoding="UTF-8"?>\n<p>after decl</p>')
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "after decl"
    assert doc.warnings == []


def test_html_conditional_comment_dropped(tmp_path: Path):
    doc = _html(
        tmp_path,
        "<p>before</p>\n<!--[if IE]><p>ie only</p><![endif]-->\n<p>after</p>",
    )
    assert len(doc.elements) == 2
    assert [e.content for e in doc.elements] == ["before", "after"]
    assert doc.warnings == []


def test_html_nul_preserved_emoji_ref_decoded(tmp_path: Path):
    doc = _html(tmp_path, b"<p>before\x00after</p>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "before" + NUL + "after"
    assert doc.warnings == []

    dec = _html(tmp_path, "<p>face &#128512; done</p>").elements[0]
    assert dec.content == "face " + EMOJI + " done"

    hexref = _html(tmp_path, "<p>hex face &#x1F600; ok</p>").elements[0]
    assert hexref.content == "hex face " + EMOJI + " ok"
