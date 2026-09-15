r"""PDF Type0 嵌入 CMap 流 Encoding（Round 2002，a 优先级）。

/Encoding 指向 CMap 流对象（PDFStream）零覆盖。_get_cmap_name
（pdffont.py:1205-1222）：流无 name 属性 → 读流字典
[CMapName]；**流内容从不被解析**（仍走 CMapDB.get_cmap 按名
查表）；CMapName 缺 → "unknown" → CMapNotFound → 空 CMap()。
探针 R2002 实证（流体内嵌自定义 cidrange <41>-<42>→CID
100/101，若被解析应得 'ZZ'）：

- **T1 流字典名生效、内容忽略**：/CMapName /OneByteIdentityH
  → '(AB)' → 'AB' x1=124（非内容映射的 'ZZ'）
- **T2 缺 CMapName 空回退**：流无 /CMapName → "unknown"
  → 空 CMap → 0 元素 + pdf_no_text_extracted
- **T3 流字典名走 2 字节路径**：/CMapName /Identity-H +
  hex <00410042> → 'AB' x1=124

判别式：T1 若 'ZZ' 则流内容参与翻；T2 若有元素或无告警翻；
T3 若 1 字节拆（x1 超预期/内容不同）翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(cmap_name: bytes | None, text_op: bytes):
    tu = (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
          "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
          " /Ordering (UCS) /Supplement 0 >> def\n"
          "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
          "1 begincodespacerange\n<00> <ff>\n"
          "endcodespacerange\n"
          "2 beginbfchar\n<41> <0041>\n<42> <0042>\n"
          "endbfchar\n"
          "endcmap\nCMapName currentdict /CMap defineresource"
          " pop\nend\nend").encode()
    emb = (b"/CIDInit /ProcSet findresource begin\n"
           b"begincmap\n"
           b"1 begincidrange\n<41> <42> 100\n"
           b"endcidrange\n"
           b"endcmap\nCMapName currentdict /CMap defineresource pop\n"
           b"end\nend")
    name_part = b"" if cmap_name is None else (b"/CMapName " + cmap_name + b" ")
    content = b"BT /F1 12 Tf 100 700 Td " + text_op + b" Tj ET"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
            b" /Encoding 8 0 R"
            b" /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity"
            b" >> ] /ToUnicode 7 0 R >>"),
        7: (b"<< /Length " + str(len(tu)).encode()
            + b" >>\nstream\n" + tu + b"\nendstream"),
        8: (b"<< " + name_part + b"/Length " + str(len(emb)).encode()
            + b" >>\nstream\n" + emb + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "e.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_stream_dict_name_wins_content_ignored():
    """T1：流字典 CMapName 生效，流内容（cidrange→100/101）被忽略 → 'AB'。"""
    d = _build(b"/OneByteIdentityH", b"(AB)")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_stream_without_cmapname_empty_fallback():
    """T2：流缺 /CMapName → unknown → 空 CMap → 0 元素 + 告警。"""
    d = _build(None, b"(AB)")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_stream_dict_name_two_byte_path():
    """T3：流字典 /CMapName /Identity-H → hex <00410042> → 'AB' x1=124。"""
    d = _build(b"/Identity-H", b"<00410042>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []
