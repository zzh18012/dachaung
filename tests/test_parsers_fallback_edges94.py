r"""app/parsers/fallback_parser.py PDF 边角测试 - 第九十四轮（Round 1524）。

新角度（probe 实证）PDF 1.5 xref 流与对象流（现代
PDF 生成器默认结构；此前轮次全部经典 xref 表或无 xref
靠扫描兜底）：

- **xref 流（/Type /XRef + FlateDecode）正常解析**：
  W [1 4 2] 二进制条目、startxref 指向流对象 → 文本照
  常提取（bbox 完全正常 [72,82.5,154,94.5]）
- **对象流（/ObjStm）内压缩字体照常加载**：字体对象
  以 type-2 条目（ObjStm 内索引）定位 → 'INOBJECT
  STREAM' 正常提取
- 构造细节：/W 字段序为 [type(1) offset(4) gen(2)] →
  struct '>BIH'（'>BHI' 会产生空提取——字段错位）
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _xref_entries(entries):
    return zlib.compress(
        b"".join(
            struct.pack(">BIH", t, a, b)
            for (t, a, b) in entries))


def _pdf_xref_stream(tmp_path, name,
                     content):
    out = bytearray(
        b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    objs = {
        1: b"<< /Type /Catalog"
           b" /Pages 2 0 R >>",
        2: b"<< /Type /Pages"
           b" /Kids [3 0 R]"
           b" /Count 1 >>",
        3: b"<< /Type /Page"
           b" /Parent 2 0 R"
           b" /MediaBox [0 0 612 792]"
           b" /Resources << /Font"
           b" << /F1 5 0 R >> >>"
           b" /Contents 4 0 R >>",
        4: (f"<< /Length"
            f" {len(content)} >>"
            f"\nstream\n{content}"
            f"\nendstream"
            ).encode("latin-1"),
        5: b"<< /Type /Font"
           b" /Subtype /Type1"
           b" /BaseFont /Helvetica"
           b" /Encoding"
           b" /WinAnsiEncoding >>",
    }
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + objs[oid]
                + b"\nendobj\n")
    xref_off = len(out)
    entries = [(0, 0, 65535)]
    for oid in range(1, 7):
        entries.append(
            (1, xref_off if oid == 6
             else offsets[oid], 0))
    comp = _xref_entries(entries)
    out += (b"6 0 obj"
            b" << /Type /XRef /Size 7"
            b" /W [1 4 2] /Root 1 0 R"
            b" /Filter /FlateDecode"
            + f" /Length {len(comp)} >>"
            .encode("latin-1")
            + b"\nstream\n" + comp
            + b"\nendstream\nendobj\n"
            + f"startxref\n{xref_off}"
              f"\n%%EOF"
            .encode("latin-1"))
    p = tmp_path / name
    p.write_bytes(bytes(out))
    return p


def _pdf_objstm(tmp_path, name,
                content):
    out = bytearray(
        b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    objs = {
        1: b"<< /Type /Catalog"
           b" /Pages 2 0 R >>",
        2: b"<< /Type /Pages"
           b" /Kids [3 0 R]"
           b" /Count 1 >>",
        3: b"<< /Type /Page"
           b" /Parent 2 0 R"
           b" /MediaBox [0 0 612 792]"
           b" /Resources << /Font"
           b" << /F1 5 0 R >> >>"
           b" /Contents 4 0 R >>",
        4: (f"<< /Length"
            f" {len(content)} >>"
            f"\nstream\n{content}"
            f"\nendstream"
            ).encode("latin-1"),
    }
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + objs[oid]
                + b"\nendobj\n")
    font5 = (b"<< /Type /Font"
             b" /Subtype /Type1"
             b" /BaseFont /Helvetica"
             b" /Encoding"
             b" /WinAnsiEncoding >>")
    stmdata = b"5 0 " + font5
    comp7 = zlib.compress(stmdata)
    offsets[7] = len(out)
    out += (b"7 0 obj"
            b" << /Type /ObjStm /N 1"
            b" /First 4"
            b" /Filter /FlateDecode"
            + f" /Length {len(comp7)} >>"
            .encode("latin-1")
            + b"\nstream\n" + comp7
            + b"\nendstream\nendobj\n")
    xref_off = len(out)
    entries = [(0, 0, 65535)]
    for oid in range(1, 9):
        if oid == 5:
            entries.append((2, 7, 0))
        elif oid == 6:
            entries.append((0, 0, 0))
        elif oid == 8:
            entries.append(
                (1, xref_off, 0))
        else:
            entries.append(
                (1, offsets[oid], 0))
    comp = _xref_entries(entries)
    out += (b"8 0 obj"
            b" << /Type /XRef /Size 9"
            b" /W [1 4 2] /Root 1 0 R"
            b" /Filter /FlateDecode"
            + f" /Length {len(comp)} >>"
            .encode("latin-1")
            + b"\nstream\n" + comp
            + b"\nendstream\nendobj\n"
            + f"startxref\n{xref_off}"
              f"\n%%EOF"
            .encode("latin-1"))
    p = tmp_path / name
    p.write_bytes(bytes(out))
    return p


def test_xref_stream(tmp_path):
    p = _pdf_xref_stream(
        tmp_path, "xrs.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (XREFSTREAM) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements] == [
        ("XREFSTREAM",
         [72.0, 82.5, 154.0, 94.5])]
    assert doc.warnings == []


def test_object_stream(tmp_path):
    p = _pdf_objstm(
        tmp_path, "objstm.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (INOBJECTSTREAM) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements] == [
        ("INOBJECTSTREAM",
         [72.0, 82.5, 181.3, 94.5])]
    assert doc.warnings == []
