r"""PDF ToUnicode CMap 块容错与 cidchar（Round 1996，a 优先级）。

R1995 锁四块入口共享 add_cid2unichr；本轮锁容错分支
（cmapdb.py ENDCIDCHAR/ENDBFRANGE isinstance 校验与 zip
strict=False 截断）。探针 R1996 实证：

- **T1 规范序 cidchar 被静默丢弃**：begincidchar `<0030>
  48`（规范 = code bytes + CID int）——ENDCIDCHAR 处理
  `for cid, code in choplist(2, objs)` 且 isinstance(cid,
  int) 校验，token 序实际 (bytes, int) → 校验失败**无任何
  告警跳过** → '(cid:48)(cid:49)'（字形宽度照走）
- **T2 数组 dst 短条目 zip 截断**：bfrange <0010><0012>
  （3 宽）配 [<0041> <0042>]（2 条目）→ stderr warn_once
  （**不入结构化告警**）+ zip strict=False → 范围内 CID18
  也未映射 → 文本 <001000120013>（CID 16/18/19）得
  'A(cid:18)(cid:19)'
- **T3 奇数 nibble dst 词法层补零**：bfchar <0010> <048>
  → PDF 十六进制串**词法层**右补零成 0x04,0x48 → UTF-16BE
  解码 U+0448 'Ј'——奇长根本到不了解码器

判别式：T1 若交换序读则 '01'；T2 若定宽对齐则 '(cid:16)
(cid:17)(cid:18)' 或 d.warnings 非空翻红；T3 若解码器收到
奇字节则 UnicodeDecodeError/(cid:16) 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(hex_text: str, blocks: str):
    tu = (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
          "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
          " /Ordering (UCS) /Supplement 0 >> def\n"
          "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
          "1 begincodespacerange\n<0000> <ffff>\n"
          "endcodespacerange\n"
          f"{blocks}"
          "endcmap\nCMapName currentdict /CMap defineresource"
          " pop\nend\nend").encode()
    content = f"BT /F1 12 Tf 100 700 Td <{hex_text}> Tj ET".encode()
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
            b" /Encoding /Identity-H /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity >> ]"
            b" /ToUnicode 7 0 R >>"),
        7: (b"<< /Length " + str(len(tu)).encode()
            + b" >>\nstream\n" + tu + b"\nendstream"),
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
        p = Path(td) / "f.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_cidchar_spec_order_silently_dropped():
    """T1：规范序 cidchar（code+CID）被 isinstance 校验静默丢弃。"""
    d = _build("00300031",
               "1 begincidchar\n<0030> 48\n<0031> 49\nendcidchar\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(cid:48)(cid:49)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_bfrange_short_array_zip_truncation():
    """T2：数组 dst 短条目 → zip 截断，范围内 CID 也未映射。"""
    d = _build("001000120013",
               "1 beginbfrange\n<0010> <0012> [<0041> <0042>]\n"
               "endbfrange\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A(cid:18)(cid:19)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 136.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_odd_nibble_dst_padded_at_lexer():
    """T3：<048> 词法层补零 → 0x0448 → 'Ј'，奇长到不了解码器。"""
    d = _build("0010",
               "1 beginbfchar\n<0010> <048>\nendbfchar\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "Ј"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 112.0, 92.0], abs=0.01)
    assert d.warnings == []
