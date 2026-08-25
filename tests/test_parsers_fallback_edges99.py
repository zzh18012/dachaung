r"""app/parsers_fallback PDF 边角测试 - 第九十九轮（Round 1529）。

新角度（集成对照）"厨房水槽"PDF——全部异形特性共存于
一文件（此前 20+ 轮逐项隔离验证，本轮锁共存不互扰）：

第 1 页叠合：双内容流（明文+Flate）× Type1 字体 ×
Type0/CID+ToUnicode（中文）× OCG OFF 图层文本 × Form
XObject 文本 × 48pt 水印叠印：

- **整页并成单元素**：'ALPHA GHOST DRAFT FORMBODY
  中文'（水印大字号行盒吞并 640/680 行——与 R1528 单
  独结论一致）、bbox 跨 82.5..152、type='heading'
- **零警告**：多流 FontBBox 缺陷、OCG、CID 全部静默

第 2 页叠合：/Rotate 180 × TJ kern × /Artifact 标记：

- **旋转镜像逐字反转**：'HEADER' → 'REDAEH'、
  'kerned' → 'denrek'
- **页内自上而下**：REDAEH（647.5）先于 denrek
  （697.5）
"""

from __future__ import annotations

import zlib
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


_TU = (
    "/CIDInit /ProcSet"
    " findresource begin\n"
    "12 dict begin\nbegincmap\n"
    "/CIDSystemInfo << /Registry"
    " (Adobe) /Ordering (UCS)"
    " /Supplement 0 >> def\n"
    "/CMapName /Adobe-Identity-UCS"
    " def\n/CMapType 2 def\n"
    "1 begincodespacerange\n<0000>"
    " <FFFF>\nendcodespacerange\n"
    "2 beginbfchar\n<0001> <4E2D>\n"
    "<0002> <6587>\nendbfchar\n"
    "endcmap\nCMapName currentdict"
    " /CMap defineresource pop\n"
    "end\nend")


def _pdf(tmp_path, name):
    form = ("BT /F1 12 Tf 0 0 Td"
            " (FORMBODY) Tj ET")
    s_a = (
        "BT /F1 12 Tf 72 700 Td"
        " (ALPHA) Tj ET"
        " BT /F1 12 Tf 72 680 Td"
        " /OC /mc0 BDC (GHOST) Tj"
        " EMC ET"
        " q 1 0 0 1 400 650 cm"
        " /Fm1 Do Q")
    s_b = zlib.compress(
        "BT /F2 12 Tf 72 640 Td"
        " <00010002> Tj ET"
        " BT /F1 48 Tf 72 660 Td"
        " (DRAFT) Tj ET"
        .encode("latin-1"))
    s2 = (
        "BT /F1 12 Tf 72 700 Td"
        " [(kern) 200 (ed)] TJ ET"
        " BT /F1 12 Tf 72 650 Td"
        " /Artifact BMC (HEADER)"
        " Tj EMC ET")
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R"
           " /OCProperties"
           " << /OCGs [90 0 R]"
           " /D << /OFF [90 0 R]"
           " /AS [] >> >> >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R 20 0 R]"
           " /Count 2 >>",
        3: "<< /Type /Page"
           " /Parent 2 0 R"
           " /MediaBox [0 0 612 792]"
           " /Resources << /Font"
           " << /F1 5 0 R"
           " /F2 6 0 R >> /XObject"
           " << /Fm1 7 0 R >> >>"
           " /Contents [4 0 R"
           " 8 0 R] >>",
        5: "<< /Type /Font"
           " /Subtype /Type1"
           " /BaseFont /Helvetica"
           " /Encoding"
           " /WinAnsiEncoding >>",
        6: ("<< /Type /Font"
            " /Subtype /Type0"
            " /BaseFont /CID"
            " /Encoding /Identity-H"
            " /DescendantFonts"
            " [<< /Type /Font"
            " /Subtype /CIDFontType0"
            " /BaseFont /CID"
            " /CIDSystemInfo"
            " << /Registry (Adobe)"
            " /Ordering (Identity)"
            " /Supplement 0 >>"
            " /DW 1000 >>]"
            " /ToUnicode 9 0 R >>"),
        7: (f"<< /Type /XObject"
            f" /Subtype /Form /BBox"
            f" [0 0 200 100]"
            f" /Resources << /Font"
            f" << /F1 5 0 R >> >>"
            f" /Length {len(form)} >>"
            f"\nstream\n{form}"
            f"\nendstream"),
        20: "<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox [0 0 612 792]"
            " /Rotate 180"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 21 0 R >>",
        90: "<< /Type /OCG"
            " /Name (Ghost) >>",
    }
    streams = {
        4: (f"<< /Length {len(s_a)} >>"
            f"\nstream\n{s_a}\n"
            f"endstream"
            ).encode("latin-1"),
        8: (f"<< /Filter"
            f" /FlateDecode /Length"
            f" {len(s_b)} >>"
            f"\nstream\n"
            ).encode("latin-1")
            + s_b + b"\nendstream",
        9: (f"<< /Length"
            f" {len(_TU)} >>"
            f"\nstream\n{_TU}\n"
            f"endstream"),
        21: (f"<< /Length"
             f" {len(s2)} >>"
             f"\nstream\n{s2}\n"
             f"endstream"
             ).encode("latin-1"),
    }
    pdf = b"%PDF-1.4\n"
    for oid in sorted(set(objs)
                      | set(streams)):
        o = streams.get(
            oid, objs.get(oid))
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + o + b"\nendobj\n")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 22 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_kitchen_sink(tmp_path):
    p = _pdf(tmp_path, "sink.pdf")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    got = [
        (e.content, e.type,
         e.source_locator["page"],
         [round(v, 1) for v in
          e.source_locator["bbox"]])
        for e in doc.elements]
    assert got == [
        ("ALPHA GHOST DRAFT"
         " FORMBODY 中文",
         "heading", 1,
         [72.0, 82.5, 469.3, 152.0]),
        ("REDAEH", "heading", 2,
         [490.0, 647.5,
          540.0, 659.5]),
        ("denrek", "heading", 2,
         [505.7, 697.5,
          540.0, 709.5]),
    ]
    assert doc.warnings == []
