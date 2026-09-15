r"""PDF ToUnicode bfchar 目标（dst）形态变体（Round 1994，a 优先级）。

edges87/93/99 锁的映射全是"一 CID → 一 BMP 码点"（bfchar/
bfrange/未映射 (cid:N)/无 ToUnicode 全占位）；dst 侧形态零
覆盖。探针 R1994 实证（pdfminer dst 解码走 UTF-16BE 变长）：

- **T1 多码点 dst**：<0001>→<00410042>（一 CID → 'AB' 两
  字符）+ <0002>→<0043> → <00010002> Tj 得 'ABC'；bbox
  仍按 **2 字形**前进（DW 1000×12pt=24pt → x1=124，文本
  字符数与字形数解耦）
- **T2 星体代理对 dst**：<0003>→<D83DDE00>（U+1F600）+
  <0004>→<005A> → '\U0001F600Z'——UTF-16BE 代理对正确
  合成单星体字符（不拆孤立代理）
- **T3 空 dst**：<0005>→<> + <0006>→<0051> → 'Q'——空
  串**入表生效**（非未映射回退）：字形静默吞字但宽度照走
  （x1=124=2 字形宽，非 112），零告警

判别式：若 dst 按定长 2 字节切则 T1 得 'ABC' 但 T2 拆成两
孤立代理（内容乱码/输出层翻红）；若空 dst 视作未映射则 T3
得 '(cid:5)Q' 翻红；若宽度按字符数（3 字符）而非字节数算
则 T1 x1=136 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _cmap(pairs: list[tuple[str, str]]) -> bytes:
    body = "".join(f"<{s}> <{dst}>\n" for s, dst in pairs)
    return (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
            "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
            " /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
            "1 begincodespacerange\n<0000> <ffff>\n"
            "endcodespacerange\n"
            f"{len(pairs)} beginbfchar\n{body}endbfchar\n"
            "endcmap\nCMapName currentdict /CMap defineresource"
            " pop\nend\nend").encode()


def _build(hex_text: str, pairs: list[tuple[str, str]]):
    tu = _cmap(pairs)
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
        p = Path(td) / "t.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_multichar_dst_two_glyphs_three_chars():
    """T1：一 CID→'AB' 多码点 dst → 'ABC'，bbox 仍 2 字形宽。"""
    d = _build("00010002",
               [("0001", "00410042"), ("0002", "0043")])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ABC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_astral_surrogate_pair_combined():
    """T2：dst 代理对 <D83DDE00> → '\U0001F600' 单星体字符。"""
    d = _build("00030004",
               [("0003", "D83DDE00"), ("0004", "005A")])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "\U0001F600Z"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_empty_dst_silent_char_width_advances():
    """T3：空 dst 静默吞字但宽度照走（x1=124 非 112）。"""
    d = _build("00050006",
               [("0005", ""), ("0006", "0051")])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "Q"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []
