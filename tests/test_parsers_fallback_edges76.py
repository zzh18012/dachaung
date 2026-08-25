r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第七十六轮（Round 1505）。

新角度（probe 实证）**多 part 静默丢内容面**（footnotes
/ header 独立 part，edges1-75 均只构造 document.xml 单
part）：

- **⚠ footnotes.xml 文本被丢弃**：body 含 footnoteReference
  + footnotes.xml 有 'the footnote text' → 只有 body
  text 入元素，脚注内容静默丢失、无任何告警（真实 Word
  文档脚注是正文一部分）
- **⚠ header1.xml 文本被丢弃**：sectPr 引用 header +
  header part 有 'the header text' → 同样只留 body
  text、无告警
- **header-only 文档 → '(空段落)' 占位**：body 无文本
  时输出空段占位元素（非 docx_no_content——空 w:p 本身
  触发占位逻辑）
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_W = ("http://schemas.openxmlformats."
      "org/wordprocessingml/2006/main")
_R = ("http://schemas.openxmlformats."
      "org/officeDocument/2006/"
      "relationships")

_CT = (
    '<?xml version="1.0"?>'
    '<Types xmlns="http://schemas.'
    'openxmlformats.org/package/2006/'
    'content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.'
    'openxmlformats-package.'
    'relationships+xml"/>'
    '<Default Extension="xml" '
    'ContentType="application/xml"/>'
    '<Override PartName="/word/'
    'document.xml" ContentType='
    '"application/vnd.'
    'openxmlformats-officedocument.'
    'wordprocessingml.document.'
    'main+xml"/>'
    '<Override PartName="/word/'
    'styles.xml" ContentType='
    '"application/vnd.'
    'openxmlformats-officedocument.'
    'wordprocessingml.styles+xml"/>'
    '<Override PartName="/word/'
    'footnotes.xml" ContentType='
    '"application/vnd.'
    'openxmlformats-officedocument.'
    'wordprocessingml.footnotes+xml"/>'
    '<Override PartName="/word/'
    'header1.xml" ContentType='
    '"application/vnd.'
    'openxmlformats-officedocument.'
    'wordprocessingml.header+xml"/>'
    '</Types>')

_RELS = (
    '<?xml version="1.0"?>'
    '<Relationships xmlns='
    '"http://schemas.openxmlformats.'
    'org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type='
    f'"{_R}/styles" '
    'Target="styles.xml"/>'
    f'<Relationship Id="rId2" Type='
    f'"{_R}/footnotes" '
    'Target="footnotes.xml"/>'
    f'<Relationship Id="rId3" Type='
    f'"{_R}/header" '
    'Target="header1.xml"/>'
    '</Relationships>')

_FOOTNOTES = (
    '<?xml version="1.0"?>'
    f'<w:footnotes xmlns:w="{_W}">'
    '<w:footnote w:id="1"><w:p>'
    '<w:r><w:t>the footnote text'
    '</w:t></w:r></w:p></w:footnote>'
    '</w:footnotes>')

_HEADER = (
    '<?xml version="1.0"?>'
    f'<w:hdr xmlns:w="{_W}">'
    '<w:p><w:r><w:t>the header text'
    '</w:t></w:r></w:p></w:hdr>')

_STYLES = (
    '<?xml version="1.0"?>'
    f'<w:styles xmlns:w="{_W}">'
    '<w:style w:type="paragraph" '
    'w:styleId="Normal"/></w:styles>')


def _doc(body_inner):
    return (
        '<?xml version="1.0"?>'
        f'<w:document xmlns:w="{_W}"'
        f' xmlns:r="{_R}">'
        '<w:body>' + body_inner
        + '<w:sectPr><w:headerReference'
        ' w:type="default" r:id="rId3"/>'
        '</w:sectPr>'
        '</w:body></w:document>')


def _build(body_inner):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", (
            '<?xml version="1.0"?>'
            '<Relationships xmlns='
            '"http://schemas.'
            'openxmlformats.org/package/'
            '2006/relationships">'
            '<Relationship Id="rId1" '
            f'Type="{_R}/officeDocument" '
            'Target="word/document.xml"/>'
            '</Relationships>'))
        z.writestr(
            "word/document.xml",
            _doc(body_inner))
        z.writestr(
            "word/_rels/document.xml.rels",
            _RELS)
        z.writestr(
            "word/styles.xml", _STYLES)
        z.writestr(
            "word/footnotes.xml",
            _FOOTNOTES)
        z.writestr(
            "word/header1.xml", _HEADER)
    return buf.getvalue()


def _parse(tmp_path, name, body_inner):
    p = tmp_path / name
    p.write_bytes(_build(body_inner))
    return FallbackParser().parse(
        p, compute_file_hash(p))


_BODY_WITH_REF = (
    "<w:p><w:r><w:t>body text</w:t>"
    "</w:r>"
    '<w:r><w:footnoteReference '
    'w:id="1"/></w:r></w:p>')


def test_footnote_text_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "fn.docx",
        _BODY_WITH_REF)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "body text"),
    ]
    assert doc.warnings == []


def test_header_text_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "hd.docx",
        _BODY_WITH_REF)
    contents = [e.content
                for e in doc.elements]
    assert "the header text" \
        not in contents
    assert contents == ["body text"]


def test_header_only_empty_para(
        tmp_path):
    doc = _parse(
        tmp_path, "ho.docx",
        "<w:p><w:r><w:t></w:t></w:r>"
        "</w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "(空段落)"),
    ]
    assert doc.elements[0].metadata[
        "empty"] is True
    assert doc.warnings == []
