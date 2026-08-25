r"""app/parsers_fallback PDF 边角测试 - 第九十六轮（Round 1526）。

新角度（probe 实证）文档级元数据与书签全部忽略（
/Info、XMP、/Outlines 从未测过；Document.metadata 仅
含 fallback 自身标记）：

- **/Info 字典完全忽略**：Title/Author/CreationDate
  挂 trailer /Info → doc.metadata 仍为 {'fallback':
  True, 'image_output_dir': None}，只提取正文
- **XMP 元数据流完全忽略**：catalog /Metadata XMP 包
  dc:title → 同上，流内容不解析不告警
- **/Outlines 书签完全忽略**：两级书签结构 + /Dest →
  书签标题不产生任何元素
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _doc(tmp_path, name, mutate):
    p = _pdf(
        tmp_path, name,
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET")
    raw = p.read_bytes().decode("latin-1")
    raw = mutate(raw)
    p.write_bytes(raw.encode("latin-1"))
    return FallbackParser().parse(
        p, compute_file_hash(p))


def _assert_ignored(doc):
    assert [e.content
            for e in doc.elements] == [
        "BODY"]
    assert doc.metadata == {
        "fallback": True,
        "image_output_dir": None}
    assert doc.warnings == []


def test_info_dict_ignored(tmp_path):
    def add(raw):
        extra = ("7 0 obj"
                 " << /Title (Doc Title)"
                 " /Author (Someone)"
                 " /CreationDate"
                 " (D:20260101) >>"
                 " endobj\n")
        raw = raw.replace(
            "trailer",
            extra + "trailer")
        return raw.replace(
            "/Root 1 0 R",
            "/Root 1 0 R"
            " /Info 7 0 R")
    _assert_ignored(
        _doc(tmp_path, "info.pdf", add))


def test_xmp_metadata_ignored(
        tmp_path):
    xmp = (
        '<?xpacket begin=""?>'
        '<x:xmpmeta'
        ' xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF><rdf:Description'
        ' dc:title="XMP TITLE"/>'
        '</rdf:RDF></x:xmpmeta>'
        '<?xpacket end="w"?>')

    def add(raw):
        extra = (
            "7 0 obj"
            " << /Type /Metadata"
            " /Subtype /XML"
            f" /Length {len(xmp)} >>"
            f"\nstream\n{xmp}\n"
            "endstream\nendobj\n")
        raw = raw.replace(
            "trailer",
            extra + "trailer")
        return raw.replace(
            "/Type /Catalog",
            "/Type /Catalog"
            " /Metadata 7 0 R")
    _assert_ignored(
        _doc(tmp_path, "xmp.pdf", add))


def test_outlines_ignored(tmp_path):
    def add(raw):
        extra = (
            "7 0 obj << /Type"
            " /Outlines /First 8 0 R"
            " /Last 8 0 R /Count 1"
            " >> endobj\n"
            "8 0 obj << /Title"
            " (Bookmark 1) /Parent"
            " 7 0 R /Dest [3 0 R"
            " /XYZ null 700 null]"
            " >> endobj\n")
        raw = raw.replace(
            "trailer",
            extra + "trailer")
        return raw.replace(
            "/Type /Catalog",
            "/Type /Catalog"
            " /Outlines 7 0 R")
    _assert_ignored(
        _doc(tmp_path, "outl.pdf", add))
