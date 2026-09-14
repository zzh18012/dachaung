r"""DOCX 脚注/尾注家族静默不可见性锁定（Round 1923，a 优先级）。

edges50 已锁批注（comments.xml + commentReference 注入）；脚注
（footnotes.xml）/尾注（endnotes.xml）grep 零覆盖。探针 R1923
实证（raw zip 构造完整 OOXML 包，python-docx 可开；_parse_docx
只读 document.xml body + para.text 只取 w:t）：

- **脚注文本不可见**：footnotes.xml 里的脚注文本不出现在任何
  元素；w:footnoteReference 标记本身也无字符贡献（正文文本完好）
- **仅含脚注引用的段落**（无 w:t）→ "(空段落)" 占位、
  metadata empty=True——脚注引用不构成内容
- **尾注同样不可见**（endnotes.xml + w:endnoteReference）
- **零告警**：三类不可见都不产生 WarningRecord（纯静默）

判别式：若未来把 footnoteReference 渲染成标记文本或把脚注文
本并入正文，content 全等断言翻红。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_CT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
    '<Override PartName="/word/endnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>'
    "</Types>"
)
_TOP_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type="{_R}/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)
_DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rIdF" Type="{_R}/footnotes" Target="footnotes.xml"/>'
    f'<Relationship Id="rIdE" Type="{_R}/endnotes" Target="endnotes.xml"/>'
    "</Relationships>"
)
_FOOTNOTES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f'<w:footnotes xmlns:w="{_W}">'
    '<w:footnote w:id="1"><w:p><w:r><w:t>SECRETFOOT one</w:t></w:r></w:p></w:footnote>'
    '<w:footnote w:id="2"><w:p><w:r><w:t>SECRETFOOT two</w:t></w:r></w:p></w:footnote>'
    "</w:footnotes>"
)
_ENDNOTES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f'<w:endnotes xmlns:w="{_W}">'
    '<w:endnote w:id="3"><w:p><w:r><w:t>SECRETEND three</w:t></w:r></w:p></w:endnote>'
    "</w:endnotes>"
)


def _build(path: Path) -> Path:
    body = (
        '<w:p><w:r><w:t>Body with footnote</w:t></w:r>'
        '<w:r><w:footnoteReference w:id="1"/></w:r></w:p>'
        '<w:p><w:r><w:footnoteReference w:id="2"/></w:r></w:p>'
        '<w:p><w:r><w:t>Tail with endnote</w:t></w:r>'
        '<w:r><w:endnoteReference w:id="3"/></w:r></w:p>'
    )
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _TOP_RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/document.xml", doc)
        z.writestr("word/footnotes.xml", _FOOTNOTES)
        z.writestr("word/endnotes.xml", _ENDNOTES)
    return path


def _parse(tmp_path: Path):
    p = _build(tmp_path / "fn.docx")
    return FallbackParser().parse(p, compute_file_hash(p))


def test_footnote_text_and_reference_mark_invisible(tmp_path):
    """脚注文本（footnotes.xml）不出现在任何元素；引用标记无字符
    贡献——正文段落 content 全等 'Body with footnote'。"""
    d = _parse(tmp_path)
    assert [e.type for e in d.elements] == ["paragraph", "paragraph", "paragraph"]
    body = d.elements[0]
    assert body.content == "Body with footnote"
    blob = " ".join(e.content or "" for e in d.elements)
    assert "SECRETFOOT" not in blob
    assert "SECRETEND" not in blob
    assert d.warnings == []


def test_footnote_only_paragraph_becomes_empty_placeholder(tmp_path):
    """仅含 w:footnoteReference 的段落（无 w:t）→ "(空段落)" 占位、
    metadata empty=True——脚注引用不构成内容。"""
    d = _parse(tmp_path)
    only_ref = d.elements[1]
    assert only_ref.content == "(空段落)"
    assert only_ref.metadata["empty"] is True
    assert only_ref.source_locator["paragraph_index"] == 1


def test_endnote_reference_invisible(tmp_path):
    """尾注（endnotes.xml + w:endnoteReference）与脚注同型：正文文本
    完好、SECRETEND 不可见、零告警。"""
    d = _parse(tmp_path)
    tail = d.elements[2]
    assert tail.content == "Tail with endnote"
    assert "SECRETEND" not in tail.content
    assert d.warnings == []
