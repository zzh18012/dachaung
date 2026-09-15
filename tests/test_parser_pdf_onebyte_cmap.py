r"""PDF OneByteIdentityH/V 与 Encoding 字典态（Round 2001，a 优先级）。

cmapdb.py:293-296 内置 IdentityCMapByte（单字节 code=CID）
与 PDFCIDFont._get_cmap_name 字典态分支（pdffont.py:1205-1210
Encoding 无 name 属性 → 读 [CMapName]）零覆盖。探针 R2001
实证（含机制溯源）：

- **T1 OneByteIdentityH**：'(AB)' 字面串 → 单字节 code
  65/66 → CIDs 65/66 → 'AB'、DW1000 → x1=124；与
  Identity-H 对照（双字节 0x4142=16706 单字 '(cid:16706)'
  x1=112）**同串不同拆**
- **T2 Encoding 字典态**：/Encoding << /Type /Encoding
  /CMapName /OneByteIdentityH >> → 字典分支读出同名 →
  与 T1 完全同值
- **T3 DLIdent-H 别名**：IDENTITY_ENCODER（pdffont.py:
  168-171）把 DLIdent-H→Identity-H → 行为=Identity-H
  （'(cid:16706)' x1=112），**不**落空 CMap 回退
- **T4 未知名空 CMap 回退**：/CMapName /ZZZUnknown →
  CMapNotFound → CMap()（码点表空，cmapdb.py:90-102
  decode 零产出）→ 0 元素 + pdf_no_text_extracted 告警
- **T5 OneByteIdentityV**：1 字节竖排 → 'A B' 每字 12pt
  向下堆叠（几何同 R2000 T1）

判别式：T1 若双字节拆则同对照翻；T3 若走空回退则 0 元素
翻；T4 若抛异常/静默空告警翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(encoding: bytes):
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
    content = b"BT /F1 12 Tf 100 700 Td (AB) Tj ET"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
            b" /Encoding " + encoding
            + b" /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity"
            b" >> ] /ToUnicode 7 0 R >>"),
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
        p = Path(td) / "o.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_onebyte_identity_h_splits_per_byte():
    """T1：OneByteIdentityH → '(AB)' 拆两 CID → 'AB' x1=124。"""
    d = _build(b"/OneByteIdentityH")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_encoding_dict_cmapname_branch():
    """T2：字典态 /CMapName → 与直接名同值 'AB' x1=124。"""
    d = _build(b"<< /Type /Encoding /CMapName /OneByteIdentityH >>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_dlident_alias_resolves_identity():
    """T3：DLIdent-H 经 IDENTITY_ENCODER 别名 → 同 Identity-H '(cid:16706)'。"""
    d = _build(b"/DLIdent-H")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(cid:16706)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 112.0, 92.0], abs=0.01)
    d2 = _build(b"/Identity-H")
    assert d2.elements[0].content == "(cid:16706)"
    assert d2.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 112.0, 92.0], abs=0.01)
    assert d.warnings == [] and d2.warnings == []


def test_unknown_cmap_empty_fallback():
    """T4：未知名 → 空 CMap 零字符 → 0 元素 + pdf_no_text_extracted。"""
    d = _build(b"<< /Type /Encoding /CMapName /ZZZUnknown >>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_onebyte_identity_v_stacks():
    """T5：OneByteIdentityV → 1 字节竖排 'A B' 每字 12pt 堆叠。"""
    d = _build(b"/OneByteIdentityV")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [94.0, 90.56, 106.0, 114.56], abs=0.01)
    assert d.warnings == []
