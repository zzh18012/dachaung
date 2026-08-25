r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第六十五轮（Round 1480）。

新角度（probe 实证）超链接 + 行内图 + 零散透传标签
（fallback edges1-64 未碰过；hyperlink 全库零覆盖，图片
已由 wp:anchor 浮动图路径覆盖但 wp:inline 行内图未锁）：
- **w:hyperlink 文本保留**：'before link text after' 单段
  （hyperlink 内 runs 照常进 paragraph.text，**目标 URL
    不捕获**、resource_path None）
- **bookmarkStart/End 透明**：'ab'
- **w:tab 成字面 \\t**：'col1\\tcol2'（tab 保留进 content）
- **commentRange/Reference**：range 内文本保留
  'textcommented'、commentReference 本体不产内容
- **proofErr 拼写标记透明**：'mispeld'
- **wp:inline 行内图提取**：段落 'pic:' + image element，
  resource_path '(unsaved)'（image_output_dir 未设），
  metadata byte_size/ext='png'/extracted_to_disk=False
"""

from __future__ import annotations

import io
import struct
import zipfile
import zlib
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _png_1x1() -> bytes:
    def chunk(typ, data):
        c = typ + data
        return (struct.pack(">I", len(data))
                + c
                + struct.pack(
                    ">I",
                    zlib.crc32(c)
                    & 0xffffffff))
    ihdr = struct.pack(
        ">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat)
            + chunk(b"IEND", b""))


def _build_docx(paragraph_xml, image=False):
    ct = (
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
        + ('<Default Extension="png" '
           'ContentType="image/png"/>'
           '<Override PartName="/word/'
           'media/p.png" ContentType='
           '"image/png"/>'
           if image else "")
        + '</Types>')
    rels = (
        '<?xml version="1.0"?>'
        '<Relationships xmlns='
        '"http://schemas.openxmlformats.'
        'org/package/2006/relationships">'
        '<Relationship Id="rId1" Type='
        '"http://schemas.openxmlformats.'
        'org/officeDocument/2006/'
        'relationships/styles" Target='
        '"styles.xml"/>'
        + ('<Relationship Id="rId10" '
           'Type="http://schemas.'
           'openxmlformats.org/'
           'officeDocument/2006/'
           'relationships/hyperlink" '
           'Target="https://example.com/" '
           'TargetMode="External"/>'
           if "hyperlink" in paragraph_xml
           else "")
        + ('<Relationship Id="rId20" '
           'Type="http://schemas.'
           'openxmlformats.org/'
           'officeDocument/2006/'
           'relationships/image" '
           'Target="media/p.png"/>'
           if image else "")
        + '</Relationships>')
    doc_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://'
        'schemas.openxmlformats.org/'
        'wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.'
        'openxmlformats.org/'
        'officeDocument/2006/'
        'relationships" '
        'xmlns:wp="http://schemas.'
        'openxmlformats.org/drawingml/'
        '2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.'
        'openxmlformats.org/drawingml/'
        '2006/main" '
        'xmlns:pic="http://schemas.'
        'openxmlformats.org/drawingml/'
        '2006/picture">'
        '<w:body>' + paragraph_xml
        + '<w:sectPr/></w:body>'
        '</w:document>')
    styles = (
        '<?xml version="1.0"?>'
        '<w:styles xmlns:w="http://'
        'schemas.openxmlformats.org/'
        'wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" '
        'w:styleId="Normal"/></w:styles>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml", ct)
        z.writestr("_rels/.rels", (
            '<?xml version="1.0"?>'
            '<Relationships xmlns='
            '"http://schemas.'
            'openxmlformats.org/package/'
            '2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.'
            'openxmlformats.org/'
            'officeDocument/2006/'
            'relationships/officeDocument"'
            ' Target="word/document.xml"/>'
            '</Relationships>'))
        z.writestr(
            "word/document.xml", doc_xml)
        z.writestr(
            "word/_rels/document.xml.rels",
            rels)
        z.writestr(
            "word/styles.xml", styles)
        if image:
            z.writestr(
                "word/media/p.png",
                _png_1x1())
    return buf.getvalue()


def _parse(tmp_path, name, px,
           image=False):
    p = tmp_path / name
    p.write_bytes(_build_docx(
        px, image=image))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- hyperlink ----------

def test_hyperlink_text_preserved(
        tmp_path):
    doc = _parse(
        tmp_path, "hl.docx",
        "<w:p><w:r><w:t>before "
        "</w:t></w:r>"
        '<w:hyperlink r:id="rId10">'
        "<w:r><w:t>link text</w:t>"
        "</w:r></w:hyperlink>"
        "<w:r><w:t> after</w:t>"
        "</w:r></w:p>")
    assert [(e.type, e.content,
             e.resource_path)
            for e in doc.elements] == [
        ("paragraph",
         "before link text after",
         None),
    ]
    assert doc.warnings == []


# ---------- bookmark ----------

def test_bookmark_transparent(tmp_path):
    doc = _parse(
        tmp_path, "bm.docx",
        "<w:p><w:r><w:t>a</w:t></w:r>"
        '<w:bookmarkStart w:id="1" '
        'w:name="bm"/>'
        "<w:r><w:t>b</w:t></w:r>"
        '<w:bookmarkEnd w:id="1"/>'
        "</w:p>")
    assert [e.content
            for e in doc.elements] == [
        "ab",
    ]


# ---------- tab ----------

def test_tab_run_literal_tab(tmp_path):
    doc = _parse(
        tmp_path, "tab.docx",
        "<w:p><w:r><w:t>col1</w:t>"
        "<w:tab/><w:t>col2</w:t>"
        "</w:r></w:p>")
    assert [e.content
            for e in doc.elements] == [
        "col1\tcol2",
    ]


# ---------- comment ----------

def test_comment_range_text_kept(
        tmp_path):
    doc = _parse(
        tmp_path, "cm.docx",
        "<w:p><w:r><w:t>text</w:t>"
        "</w:r>"
        '<w:commentRangeStart w:id="0"/>'
        "<w:r><w:t>commented</w:t>"
        "</w:r>"
        '<w:commentRangeEnd w:id="0"/>'
        '<w:r><w:commentReference '
        'w:id="0"/></w:r></w:p>')
    assert [e.content
            for e in doc.elements] == [
        "textcommented",
    ]
    assert doc.warnings == []


# ---------- proofErr ----------

def test_proof_err_transparent(tmp_path):
    doc = _parse(
        tmp_path, "pe.docx",
        '<w:p><w:proofErr w:type='
        '"spellStart"/>'
        "<w:r><w:t>mispeld</w:t></w:r>"
        '<w:proofErr w:type='
        '"spellEnd"/></w:p>')
    assert [e.content
            for e in doc.elements] == [
        "mispeld",
    ]


# ---------- wp:inline 行内图 ----------

def test_inline_picture_extracted(
        tmp_path):
    px = (
        "<w:p><w:r><w:t>pic: </w:t>"
        "</w:r>"
        "<w:r><w:drawing><wp:inline>"
        '<wp:extent cx="9525" cy="9525"/>'
        "<a:graphic><a:graphicData "
        'uri="http://schemas.'
        'openxmlformats.org/drawingml/'
        '2006/picture">'
        "<pic:pic><pic:nvPicPr>"
        '<pic:cNvPr id="0" name="p.png"/>'
        "<pic:cNvPicPr/></pic:nvPicPr>"
        '<pic:blipFill><a:blip '
        'r:embed="rId20"/></pic:blipFill>'
        "<pic:spPr><a:xfrm>"
        '<a:off x="0" y="0"/>'
        '<a:ext cx="9525" cy="9525"/>'
        "</a:xfrm><a:prstGeom "
        'prst="rect"><a:avLst/>'
        "</a:prstGeom></pic:spPr>"
        "</pic:pic></a:graphicData>"
        "</a:graphic></wp:inline>"
        "</w:drawing></w:r></w:p>")
    doc = _parse(
        tmp_path, "pic.docx", px,
        image=True)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "pic:"),
        ("image", None),
    ]
    img = doc.elements[1]
    assert img.resource_path == \
        "(unsaved)"
    assert img.metadata["ext"] == \
        "png"
    assert img.metadata[
        "extracted_to_disk"] is False
    assert img.metadata[
        "byte_size"] == len(
        _png_1x1())
